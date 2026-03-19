import requests
import yfinance as yf
import telebot

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

# ===== DATA =====
def get_change(ticker):
    try:
        data = yf.Ticker(ticker).history(period="3d")

        if len(data) < 2:
            return None

        last = data["Close"].iloc[-1]
        prev = data["Close"].iloc[-2]

        return round((last / prev - 1) * 100, 2)

    except:
        return None


def get_fear_greed():
    try:
        url = "https://api.alternative.me/fng/"
        data = requests.get(url, timeout=5).json()
        return int(data["data"][0]["value"])
    except:
        return None


def get_vix():
    try:
        data = yf.Ticker("^VIX").history(period="1d")
        return round(data["Close"].iloc[-1], 2)
    except:
        return None


# ===== INTERPRET =====
def interpret_spx(val):
    if val is None:
        return "no data"

    if val <= -2:
        return f"{val}% → сильний risk-off → тиск на BTC (обережно з UP)"
    elif val <= -1:
        return f"{val}% → risk-off → слабкість BTC"
    elif val < 0:
        return f"{val}% → легка слабкість"
    elif val < 1:
        return f"{val}% → стабільність"
    else:
        return f"{val}% → risk-on → підтримка BTC (обережно з DOWN)"


def interpret_dxy(val):
    if val is None:
        return "no data"

    if val >= 1:
        return f"{val}% → сильний долар → тиск на BTC (обережно з UP)"
    elif val > 0:
        return f"{val}% → долар посилюється → легкий тиск на BTC"
    elif val > -1:
        return f"{val}% → слабкий долар → підтримка BTC"
    else:
        return f"{val}% → сильна слабкість долара → підтримка BTC (обережно з DOWN)"


def interpret_fg(val):
    if val is None:
        return "no data"

    if val < 20:
        return f"{val} → паніка → обережно з DOWN (можливий відскок)"
    elif val < 40:
        return f"{val} → страх → слабкість ринку"
    elif val < 60:
        return f"{val} → нейтрально → без перекосу"
    elif val < 80:
        return f"{val} → жадібність → обережно з UP"
    else:
        return f"{val} → перегрів → ризик падіння (обережно з UP)"


def interpret_vix(val):
    if val is None:
        return "no data"

    if val < 15:
        return f"{val} → спокій → стабільний ринок"
    elif val < 20:
        return f"{val} → норм → без сильного страху"
    elif val < 30:
        return f"{val} → страх → тиск на BTC"
    else:
        return f"{val} → паніка → можливі різкі рухи (обережно з DOWN)"


def interpret_btc(val):
    if val is None:
        return "no data"

    if val >= 2:
        return f"{val}% → сильний рух UP → можливий перегрів (обережно з UP)"
    elif val > 0:
        return f"{val}% → зростання"
    elif val > -2:
        return f"{val}% → слабкість"
    else:
        return f"{val}% → сильне падіння → можливий відскок (обережно з DOWN)"


# ===== MARKET BIAS =====
def get_market_bias(spx, dxy, vix, fg):
    score = 0

    if spx is not None:
        if spx <= -1:
            score -= 1
        elif spx >= 1:
            score += 1

    if dxy is not None:
        if dxy >= 0.5:
            score -= 1
        elif dxy <= -0.5:
            score += 1

    if vix is not None:
        if vix >= 25:
            score -= 1
        elif vix <= 15:
            score += 1

    if fg is not None:
        if fg < 30:
            score -= 1
        elif fg > 60:
            score += 1

    if score <= -2:
        return "🔻 Risk-off → ринок під тиском"
    elif score >= 2:
        return "🟢 Risk-on → ринок підтримує BTC"
    else:
        return "➖ Mixed → немає явного перекосу"


# ===== KEY FACTOR =====
def get_key_factor(spx, dxy, vix, fg):
    factors = []

    if spx is not None and abs(spx) >= 1:
        factors.append(("SPX", abs(spx), spx))

    if dxy is not None and abs(dxy) >= 0.5:
        factors.append(("DXY", abs(dxy), dxy))

    if vix is not None and vix >= 20:
        factors.append(("VIX", vix, vix))

    if fg is not None and (fg < 30 or fg > 70):
        factors.append(("FG", abs(fg - 50), fg))

    if not factors:
        return "немає домінуючого фактору"

    main = max(factors, key=lambda x: x[1])
    name, _, value = main

    if name == "SPX":
        return "SPX падає → тиск на ринок" if value < 0 else "SPX росте → підтримка ринку"

    elif name == "DXY":
        return "DXY росте → тиск на BTC" if value > 0 else "DXY падає → підтримка BTC"

    elif name == "VIX":
        return "VIX високий → підвищений страх"

    elif name == "FG":
        return "паніка → можливі відскоки" if value < 30 else "жадібність → ризик перегріву"


# ===== REPORT =====
def generate_report():
    spx = get_change("^GSPC")
    dxy = get_change("DX-Y.NYB")
    btc = get_change("BTC-USD")
    fg = get_fear_greed()
    vix = get_vix()

    text = "📊 Macro Report\n\n"

    text += f"SPX: {interpret_spx(spx)}\n"
    text += f"DXY: {interpret_dxy(dxy)}\n"
    text += f"VIX: {interpret_vix(vix)}\n"
    text += f"BTC: {interpret_btc(btc)}\n"
    text += f"Fear & Greed: {interpret_fg(fg)}\n"

    text += f"\n🌍 Загальний фон:\n{get_market_bias(spx, dxy, vix, fg)}\n"
    text += f"\n🎯 Ключовий фактор:\n{get_key_factor(spx, dxy, vix, fg)}"

    return text


# ===== SEND =====
def send_report():
    try:
        bot.send_message(CHAT_ID, generate_report())
        print("Report sent")
    except Exception as e:
        print("Error:", e)


# ===== RUN =====
if __name__ == "__main__":
    send_report()
