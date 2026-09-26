import os
import json
import requests
import pandas as pd
import yfinance as yf

SYMBOL = os.getenv("YAHOO_SYMBOL", "GC=F")
INTERVAL = "5m"
PERIOD = "5d"

STATE_FILE = "state.json"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "Missing required environment variables: "
        "TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID. "
        "Set them before running the bot."
    )


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_data():
    df = yf.download(
        SYMBOL,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise RuntimeError("No market data returned.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    needed = ["Open", "High", "Low", "Close"]
    df = df[needed].dropna().copy()
    return df


def indicators(df):
    close = df["Close"]
    low = df["Low"]
    high = df["High"]

    # Fast EMA pair for scalping
    ema_fast = close.ewm(span=8, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()

    # Fast MACD (6/13/5 instead of standard 12/26/9)
    ema6 = close.ewm(span=6, adjust=False).mean()
    ema13 = close.ewm(span=13, adjust=False).mean()
    macd = ema6 - ema13
    macd_signal = macd.ewm(span=5, adjust=False).mean()

    # Fast Stochastic (5/3/3)
    lowest = low.rolling(5).min()
    highest = high.rolling(5).max()
    stoch_k_raw = 100 * (close - lowest) / (highest - lowest)
    stoch_k = stoch_k_raw.rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()

    out = pd.DataFrame({
        "close": close,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "macd": macd,
        "macd_signal": macd_signal,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
    }).dropna()
    return out


def detect_signal(x):
    if len(x) < 2:
        return None

    p = x.iloc[-2]
    c = x.iloc[-1]

    bullish_cross = p.ema_fast <= p.ema_slow and c.ema_fast > c.ema_slow
    bearish_cross = p.ema_fast >= p.ema_slow and c.ema_fast < c.ema_slow

    macd_bull = c.macd > c.macd_signal
    macd_bear = c.macd < c.macd_signal

    stoch_bull = c.stoch_k > c.stoch_d and c.stoch_k < 80
    stoch_bear = c.stoch_k < c.stoch_d and c.stoch_k > 20

    # Relaxed for scalping: EMA cross + at least ONE confirmation
    if bullish_cross and (macd_bull or stoch_bull):
        return "BUY", c

    if bearish_cross and (macd_bear or stoch_bear):
        return "SELL", c

    return None


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()


def main():
    state = load_state()

    df = get_data()
    x = indicators(df)
    result = detect_signal(x)

    if not result:
        print("No new signal.")
        return

    side, c = result
    ts = x.index[-1]
    ts_str = str(ts)

    if state.get("last_signal_ts") == ts_str:
        print("Signal already sent for this candle, skipping.")
        return

    if getattr(ts, "tzinfo", None) is not None:
        ts_local = ts.tz_convert("Asia/Tehran")
    else:
        ts_local = ts

    emoji = "🟢" if side == "BUY" else "🔴"
    msg = (
        f"{emoji} XAUUSD (Scalp) — {side}\n"
        f"⏱ Timeframe: M5\n"
        f"💰 Price: {c.close:.2f}\n"
        f"🕒 Candle: {ts_local.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"〰️ EMA 8/21: {'bullish' if side == 'BUY' else 'bearish'} cross\n"
        f"📈 MACD: {'bullish' if side == 'BUY' else 'bearish'}\n"
        f"📊 Stochastic: {'bullish' if side == 'BUY' else 'bearish'}\n\n"
        f"⚠️ Alert only — no trade is executed."
    )
    send_telegram(msg)
    print("Signal sent:", side)

    state["last_signal_ts"] = ts_str
    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Gold signal bot error:\n{type(e).__name__}: {e}"
        print(error_msg)
        try:
            send_telegram(error_msg)
        except Exception as telegram_error:
            print(f"Also failed to send error alert to Telegram: {telegram_error}")
        raise
