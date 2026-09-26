import os
import requests
import pandas as pd
import yfinance as yf

SYMBOL = os.getenv("YAHOO_SYMBOL", "GC=F")
INTERVAL = "15m"
PERIOD = "5d"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "Missing required environment variables: "
        "TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID. "
        "Set them before running the bot."
    )

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

    # yfinance can return MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    needed = ["Open", "High", "Low", "Close"]
    df = df[needed].dropna().copy()
    return df

def indicators(df):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    # Ichimoku defaults: 9 / 26 / 52
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    # Stochastic 14 / 3 / 3
    lowest = low.rolling(14).min()
    highest = high.rolling(14).max()
    stoch_k_raw = 100 * (close - lowest) / (highest - lowest)
    stoch_k = stoch_k_raw.rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()

    # MACD 12 / 26 / 9
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - macd_signal

    out = pd.DataFrame({
        "close": close,
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": hist,
    }).dropna()
    return out

def detect_signal(x):
    if len(x) < 2:
        return None

    p = x.iloc[-2]  # previous closed candle
    c = x.iloc[-1]  # latest closed candle

    bullish_cross = p.tenkan <= p.kijun and c.tenkan > c.kijun
    bearish_cross = p.tenkan >= p.kijun and c.tenkan < c.kijun

    cloud_top = max(c.senkou_a, c.senkou_b)
    cloud_bottom = min(c.senkou_a, c.senkou_b)

    above_cloud = c.close > cloud_top
    below_cloud = c.close < cloud_bottom

    bullish_cloud = c.senkou_a > c.senkou_b
    bearish_cloud = c.senkou_a < c.senkou_b

    stochastic_buy = c.stoch_k > c.stoch_d and c.stoch_k < 80
    stochastic_sell = c.stoch_k < c.stoch_d and c.stoch_k > 20

    macd_buy = c.macd > c.macd_signal and c.macd_hist > 0
    macd_sell = c.macd < c.macd_signal and c.macd_hist < 0

    if bullish_cross and above_cloud and bullish_cloud and stochastic_buy and macd_buy:
        return "BUY", c

    if bearish_cross and below_cloud and bearish_cloud and stochastic_sell and macd_sell:
        return "SELL", c

    return None

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()

def main():
    df = get_data()
    x = indicators(df)
    result = detect_signal(x)
    result = ("BUY", x.iloc[-1])  # TEMPORARY TEST LINE

    if not result:
        print("No new signal.")
        return

    side, c = result
    ts = x.index[-1]
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_convert("Asia/Tehran")

    emoji = "🟢" if side == "BUY" else "🔴"
    msg = (
        f"{emoji} XAUUSD — {side}\n"
        f"⏱ Timeframe: M15\n"
        f"💰 Price: {c.close:.2f}\n"
        f"🕒 Candle: {ts.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"☁️ Ichimoku: price {'above' if side == 'BUY' else 'below'} cloud\n"
        f"〰️ Tenkan/Kijun: {'bullish' if side == 'BUY' else 'bearish'} cross\n"
        f"📊 Stochastic: {'bullish' if side == 'BUY' else 'bearish'}\n"
        f"📈 MACD: {'bullish' if side == 'BUY' else 'bearish'}\n\n"
        f"⚠️ Alert only — no trade is executed."
    )
    send_telegram(msg)
    print("Signal sent:", side)

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
