import os.path

from CONFIG import USERNAME, PASSWORD, BOT_TOKEN
import requests
import json
import telebot
import asyncio


URLS = {
    0: "https://iss.moex.com/iss/statistics/engines/currency/markets/fixing.json",
    1: "https://iss.moex.com/iss/statistics/engines/currency/markets/selt/rates.json",
    2: "https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities.json"
}

buttons = {
    0: 'Фиксинги Московской биржи',
    1: 'Курсы ЦБРФ',
    2: 'Индикативные курсы валют срочного рынка',
    3: 'Подписаться на уведомление, когда изменится курс доллара'
}

notifiers = None

last_usd_rate = 0.0
last_euro_rate = 0.0


def get_fixing_data():
    s = requests.Session()
    s.get('https://passport.moex.com/authenticate', auth=(USERNAME, PASSWORD))
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox / 66.0"}
    cookies = {'MicexPassportCert': s.cookies['MicexPassportCert']}
    req = requests.get(URLS[0], headers=headers, cookies=cookies)
    data = json.loads(req.text)
    usd_data = data['history']['data'][-1]
    euro_data = data['history']['data'][1]
    return usd_data[-1], euro_data[-1]


def get_futures_data():
    s = requests.Session()
    s.get('https://passport.moex.com/authenticate', auth=(USERNAME, PASSWORD))
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox / 66.0"}
    cookies = {'MicexPassportCert': s.cookies['MicexPassportCert']}
    req = requests.get(URLS[2], headers=headers, cookies=cookies)
    data = json.loads(req.text)
    usd_data = data['securities']['data'][-1]
    return usd_data[-1]


def add_notifier(id):
    global notifiers
    if notifiers is None:
        if os.path.isfile("notifiers.txt"):
            with open("notifiers.txt", "r") as file:
                data = file.read()
                notifiers = [str(x) for x in data.split(";") if str(x) != ""]
        else:
            with open("notifiers.txt", "w") as file:
                file.write(str(id) + ";")
            notifiers = [str(id)]
    notifiers.append(id)
    with open("notifiers.txt", "a") as file:
        file.write(str(id) + ";")


def notify_everybody(msg):
    if notifiers is not None:
        for id in notifiers:
            bot.send_message(id, msg)


async def check_usd_rate():
    global last_usd_rate
    s = requests.Session()
    s.get('https://passport.moex.com/authenticate', auth=(USERNAME, PASSWORD))
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox / 66.0"}
    cookies = {'MicexPassportCert': s.cookies['MicexPassportCert']}
    req = requests.get(URLS[1], headers=headers, cookies=cookies)
    data = json.loads(req.text)
    usd_data = data['cbrf']['data'][0][0]
    if usd_data != last_usd_rate:
        notify_everybody(f"Чел тут вообще капец, доллар поменялся:\n{last_usd_rate} -> {usd_data}")
    last_usd_rate = usd_data


async def check_euro_rate():
    global last_euro_rate
    s = requests.Session()
    s.get('https://passport.moex.com/authenticate', auth=(USERNAME, PASSWORD))
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox / 66.0"}
    cookies = {'MicexPassportCert': s.cookies['MicexPassportCert']}
    req = requests.get(URLS[1], headers=headers, cookies=cookies)
    data = json.loads(req.text)
    euro_rate = data['cbrf']['data'][0][6]
    if euro_rate != last_euro_rate:
        notify_everybody(f"Чел тут вообще капец, евро поменялся:\n{last_euro_rate} -> {euro_rate}")
    last_euro_rate = euro_rate


bot = telebot.TeleBot(BOT_TOKEN)

if os.path.isfile("notifiers.txt"):
    with open("notifiers.txt", "r") as file:
        data = file.read()
        notifiers = [str(x) for x in data.split(";") if str(x) != ""]
else:
    with open("notifiers.txt", "w") as file:
        file.write("")


@bot.message_handler(commands=["start"])
def start(m, res=False):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton(buttons[0]))
    markup.add(telebot.types.KeyboardButton(buttons[1]))
    markup.add(telebot.types.KeyboardButton(buttons[2]))
    markup.add(telebot.types.KeyboardButton(buttons[3]))
    bot.send_message(m.chat.id, 'Выбирай, что тебе нужно',  reply_markup=markup)


@bot.message_handler(content_types=["text"])
def handle_text(message):
    msg_text = message.text.strip()
    if msg_text == buttons[0]:
        usd_rate, euro_rate = get_fixing_data()
        answer = f"Курс доллара: {usd_rate}\nКурс Евро: {euro_rate}"
    elif msg_text == buttons[1]:
        answer = f"Курс доллара: {last_usd_rate}\nКурс Евро: {last_euro_rate}"
    elif msg_text == buttons[2]:
        usd_rate = get_futures_data()
        answer = f"Курс доллара: {usd_rate}"
    elif msg_text == buttons[3]:
        if notifiers is not None and str(message.chat.id) in notifiers:
            answer = "Ты и так подписан..."
        else:
            add_notifier(message.chat.id)
            answer = "Подписал тебя!"
    elif msg_text == "secret":
        answer = ")"
        asyncio.run(check_usd_rate())
        asyncio.run(check_euro_rate())
    else:
        answer = "Не понял, что тебе нужно?"
    bot.send_message(message.chat.id, answer)


bot.polling(none_stop=True, interval=0)
