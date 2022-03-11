import os
import time
import pyupbit
import datetime
import requests
import numpy as np
from dotenv import load_dotenv

load_dotenv()
access = os.getenv("ACCESS_KEY")
secret = os.getenv("SECRET_KEY")
myToken = os.getenv("SLACK_TOKEN")

channel = "cryptocurrency"


def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + token},
        data={"channel": channel, "text": text},
    )


def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]["close"] + (df.iloc[0]["high"] - df.iloc[0]["low"]) * k
    return target_price


def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time


def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    ma15 = df["close"].rolling(15).mean().iloc[-1]
    return ma15


def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b["currency"] == ticker:
            if b["balance"] is not None:
                return float(b["balance"])
            else:
                return 0
    return 0


def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


def get_ror(k):
    """k에 따른 수익률 조회"""
    df = pyupbit.get_ohlcv("KRW-BTC")
    df["range"] = (df["high"] - df["low"]) * k
    df["target"] = df["open"] + df["range"].shift(1)

    df["ror"] = np.where(df["high"] > df["target"], df["close"] / df["target"], 1)

    ror = df["ror"].cumprod()[-2]
    return ror


def get_bestk():
    """0.1 ~ 0.9 사이의 최적k 조회"""
    bestk = 0.5
    max_value = 0
    for k in np.arange(0.1, 1.0, 0.1):
        ror = get_ror(k)
        if ror > max_value:
            max_value = ror
            bestk = k
    return bestk


# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken, channel, "autotrade start")
minute = 0
k = 0.5

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")  # 9:00
        end_time = start_time + datetime.timedelta(days=1)  # 9:00 + 1일

        # 9시 ~ 다음날 8시 59분
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", k)
            ma15 = get_ma15("KRW-BTC")
            current_price = get_current_price("KRW-BTC")
            if target_price < current_price and ma15 < current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw * 0.9995)
                    buy_msg = f'**********\n매수체결 (BUY)\n매수액: {buy_result["price"]}\n수수료: {buy_result["reserved_fee"]}\nBTC 가격: {current_price}\n**********\n'
                    post_message(myToken, channel, buy_msg)

            now_minute = now.minute // 30
            if minute != now_minute:
                # k값 업데이트
                k = get_bestk()
                krw = get_balance("KRW")
                minute = now_minute
                msg = f"현재 시간: {now}\n목표 매수가: {target_price}\n현재 가격: {current_price}\nKR 잔고: {krw}\n"
                post_message(myToken, channel, msg)

        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc * 0.9995)
                current_price = get_current_price("KRW-BTC")
                sell_msg = f"**********\n매도체결 (SELL)\n매도액: {float(sell_result['volume']) * current_price}\nBTC 가격: {current_price}\n**********\n"
                post_message(myToken, channel, sell_msg)
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken, channel, e)
        time.sleep(1)
