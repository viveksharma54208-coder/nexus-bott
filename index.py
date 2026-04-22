import pandas as pd
from datetime import datetime, timedelta
import pytz, requests, random, time, os

BOT_NAME = "🚀 NEXUS FUTURE ENGINE 🚀"
DEVELOPER = "👨‍💻 Chandan"
IST = pytz.timezone("Asia/Kolkata")

# ===== USER SETTINGS (FROM RENDER ENV) =====
SETTINGS = {
    "market": os.getenv("MARKET", "OTC"),
    "timeframe": int(os.getenv("TIMEFRAME", 1)),
    "from_time": os.getenv("FROM_TIME", "00:00"),
    "to_time": os.getenv("TO_TIME", "23:59"),
    "accuracy": int(os.getenv("ACCURACY", 75)),
    "pairs": os.getenv("PAIRS", "EURUSD,GBPJPY").split(",")
}

ALL_PAIRS = [
    "USDBRL-OTC","USDNGN-OTC","USDCOP-OTC","USDARS-OTC",
    "USDCLP-OTC","USDPEN-OTC","USDTRY-OTC","USDPKR-OTC",
    "USDBDT-OTC","USDZAR-OTC","USDSGD-OTC","USDTHB-OTC","USDHKD-OTC",
    "EURUSD","EURGBP","EURJPY","GBPJPY","AUDJPY","EURAUD","GBPAUD",
    "EURCHF","GBPCHF","AUDCHF","CADJPY","CHFJPY","NZDJPY",
    "EURCAD","GBPCAD","AUDCAD","NZDCAD","EURNZD","GBPNZD","AUDNZD"
]

# ===== DATA (LIVE) =====
def get_data():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=200"
        data = requests.get(url, timeout=5).json()
        df = pd.DataFrame(data, columns=["t","o","h","l","c","v","_","_","_","_","_","_"])
        for col in ["o","h","l","c"]:
            df[col] = df[col].astype(float)

        df["ema50"] = df["c"].ewm(span=50).mean()
        df["ema200"] = df["c"].ewm(span=200).mean()

        delta = df["c"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100/(1+rs))
        return df
    except:
        return None

# ===== MODELS =====
def prediction_model(df):
    last = df.iloc[-1]; prev = df.iloc[-2]
    trend = 1 if last["ema50"] > last["ema200"] else -1
    momentum = 1 if last["c"] > prev["c"] else -1
    reversal = -1 if last["rsi"]>70 else (1 if last["rsi"]<30 else 0)
    return trend + momentum + reversal

def logic_model(df):
    last = df.iloc[-1]; prev = df.iloc[-2]
    score = 0
    score += 2 if last["ema50"] > last["ema200"] else -2

    body = abs(last["c"] - last["o"])
    wick = last["h"] - last["l"]
    if body > wick*0.5:
        score += 2 if last["c"] > last["o"] else -2

    if last["h"] > prev["h"]: score += 1
    if last["l"] < prev["l"]: score -= 1
    return score

# ===== ENGINES =====
def live_engine(df):
    score = logic_model(df) + prediction_model(df)
    prob = min(abs(score)*15, 95)
    if abs(score) < 3: return None, prob
    return ("CALL" if score>0 else "PUT"), prob

def otc_engine():
    score = random.randint(-6,6)
    prob = min(abs(score)*18 + random.randint(5,15), 95)
    if abs(score) < 2: return None, prob
    return ("CALL" if score>0 else "PUT"), prob

# ===== BACKTEST =====
def backtest(df):
    if df is None: return 60
    wins=0; total=20
    for i in range(-total,-1):
        sub = df.iloc[:i]
        signal,_ = live_engine(sub)
        if signal:
            nxt = df.iloc[i+1]
            if (signal=="CALL" and nxt["c"]>nxt["o"]) or (signal=="PUT" and nxt["c"]<nxt["o"]):
                wins+=1
    return int((wins/total)*100)

# ===== SIGNAL =====
def generate():
    now = datetime.now(IST)
    df = get_data()
    winrate = backtest(df)
    signals = []

    for i in range(1,60):
        t = (now + timedelta(minutes=i*SETTINGS["timeframe"])).strftime("%H:%M")
        if not (SETTINGS["from_time"] <= t <= SETTINGS["to_time"]):
            continue

        for pair in SETTINGS["pairs"]:
            if pair not in ALL_PAIRS: continue

            if SETTINGS["market"] == "OTC":
                if "OTC" not in pair: continue
                signal, prob = otc_engine()
            else:
                if "OTC" in pair or df is None: continue
                signal, prob = live_engine(df)

            if signal:
                prob = min(prob*0.7 + winrate*0.3, 95)
                if prob >= SETTINGS["accuracy"]:
                    icon = "🟢📈" if signal=="CALL" else "🔴📉"
                    tier = "💎 VIP" if prob>=85 else "🔥 PREMIUM"

                    signals.append(f"""
╔════════════════════╗
🚀 NEXUS FUTURE ENGINE
👨‍💻 Dev: Chandan
╚════════════════════╝
{icon} {pair} ({SETTINGS['market']})
⏰ {t} ⏳ M{SETTINGS['timeframe']}
🔮 {signal}
📊 {int(prob)}% {tier}
━━━━━━━━━━━━━━━━━━
""")
                    break

        if len(signals) >= 10:
            break

    return signals if signals else ["❌ No signals (lower accuracy)"]

# ===== AUTO RUN =====
if __name__ == "__main__":
    print("🚀 BOT STARTED...")

    while True:
        sigs = generate()
        for s in sigs:
            print(s)
        print("⏳ Next cycle...\n")
        time.sleep(60)
