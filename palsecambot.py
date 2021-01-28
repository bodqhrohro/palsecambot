import telebot
from threading import Thread, Event, RLock
import logging
from random import randrange, getrandbits, random

logging.basicConfig()

bot = telebot.TeleBot('your_token')

# (message_id, is_advanced)
chats_lock = RLock()
chats = {}
WIDTH = 36
HEIGHT=12

def randomBackground(color=False):
    lines = []
    for _ in range(HEIGHT):
        rnd = getrandbits(WIDTH)
        lines.append(['░' if (rnd >> i) & 1 else '▒' for i in range(WIDTH)])

    # still ugly :C
    """
    if color:
        for _ in range(randrange(10)):
            x = randrange(WIDTH-6)
            y = randrange(HEIGHT)
            lines[y][x] = '🟥'
            lines[y][x+1] = '​'
            lines[y][x+2] = '​'
    """

    return lines

def linesToStr(lines):
    return "\n".join(["".join(line) for line in lines])

def randomScreen():
    mesecam = randrange(2)
    bg = randomBackground(mesecam)

    # print OSD
    bg[1][3] = '►'
    color_string = "MESECAM" if mesecam else "PAL"
    bg[1][5:5+len(color_string)] = color_string
    bg[2][5:9] = "AUTO"

    # add HBI
    hbi_offset = 0
    for y in range(len(bg)):
        dice = random() ** 3
        if (dice > 0.6):
            hbi_offset -= 1 if hbi_offset > 0 else 0
        elif (dice > 0.5):
            hbi_offset += 1

        if (hbi_offset > 0):
            bg[y][hbi_offset:WIDTH] = bg[y][:WIDTH-hbi_offset]
            for x in range(hbi_offset - 1):
                bg[y][x] = '█'
            bg[y][hbi_offset - 1] = '║'

    # add VBI
    bg.append(['═' for _ in range(WIDTH)])
    bg.append(['█' for _ in range(WIDTH)])
    bg.append(['═' for _ in range(WIDTH)])

    vbi_offset = int((HEIGHT+3)*(random() ** 6))

    return "```\n" + \
            linesToStr(bg[vbi_offset:vbi_offset+HEIGHT]) + \
            ("\n" + linesToStr(bg[:vbi_offset-3]) if vbi_offset > 3 else "") + \
            "\n```"

def toggleText(toggle):
    if toggle:
        return "```\n► PAL\n  AUTO\n```"
    else:
        return "```\n► MESECAM\n  AUTO\n```"

@bot.message_handler(commands=['start'])
def start(message):
    new_message = bot.send_message(message.chat.id, toggleText(True), parse_mode='Markdown')
    with chats_lock:
        chats[message.chat.id] = (new_message.message_id, False)

@bot.message_handler(commands=['start_advanced'])
def start_advanced(message):
    new_message = bot.send_message(message.chat.id, randomScreen(), parse_mode='Markdown')
    with chats_lock:
        chats[message.chat.id] = (new_message.message_id, True)

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    with chats_lock:
        if chat_id in chats.keys():
            message_id, is_advanced = chats[chat_id]
            del chats[chat_id]

            message_text = '`■`'
            if is_advanced:
                bg = randomBackground()
                bg[1][3] = '■'
                message_text = "```\n" + "\n".join(["".join(line) for line in bg]) + "\n```"
            bot.edit_message_text(message_text, chat_id, message_id, parse_mode='Markdown')

class EditThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.timer = Event()
        self.toggle = True

    def run(self):
        while not self.timer.wait(1):
            self.toggle = not self.toggle
            new_text = toggleText(self.toggle)
            with chats_lock:
                for chat_id, tup in chats.items():
                    message_id, is_advanced = tup
                    message_text = new_text
                    if is_advanced:
                        message_text = randomScreen()
                    try:
                        bot.edit_message_text(message_text, chat_id, message_id, parse_mode='Markdown')
                    except telebot.apihelper.ApiException as ex:
                        # 400 should be a same-content warning, ignore it
                        if ex.result.status_code != 400:
                            logging.error(ex)
                            self.timer.wait(60)

thread = EditThread()
thread.start()

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as ex:
        logging.error(ex)
