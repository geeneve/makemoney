from math import ceil
import os
import time
import traceback
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
    time.sleep(1)
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


def convert_krw(amount):
    """읽기 쉬운 단위로 변환"""
    return format(ceil(float(amount)), ",d") + "원"


# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken, channel, "autotrade start")

hour = -1
k = 0.5
buy_price = 0

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
            krw = get_balance("KRW")
            if target_price < current_price and ma15 < current_price:
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw * 0.9995)
                    buy_msg = f'**********\n매수체결 (BUY)\n매수액: {convert_krw(buy_result["price"])}\nBTC 가격: {convert_krw(current_price)}\n**********\n'
                    post_message(myToken, channel, buy_msg)
                    buy_price = current_price

            now_hour = now.hour
            if hour != now_hour:
                # 시간당 한 번 k값 업데이트
                k = get_bestk()
                time.sleep(1)
                hour = now_hour

                # 2시간에 한 번 슬랙 알림
                if hour % 2 == 0:
                    if buy_price > 0:
                        # 오늘 구매한 경우 메시지
                        msg = f"매수O\n매수가: {convert_krw(buy_price)}\n현재가: {convert_krw(current_price)}\n손익: {convert_krw(current_price-buy_price)}\n"
                    else:
                        # 오늘 구매하지 않은 경우 메시지
                        msg = f"매수X\n목표 매수가: {convert_krw(max(target_price, ma15))}\n현재가: {convert_krw(current_price)}\n차액: {convert_krw(max(target_price, ma15) - current_price)}\n"
                    post_message(myToken, channel, msg)

        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc * 0.9995)
                current_price = get_current_price("KRW-BTC")
                sell_msg = f"**********\n매도체결 (SELL)\n매도액: {float(sell_result['volume']) * current_price}\nBTC 가격: {current_price}\n**********\n"
                post_message(myToken, channel, sell_msg)
                buy_price = 0
        time.sleep(1)
    except Exception as e:
        traceback.print_exc()
        print(e)
        post_message(myToken, channel, e)
        time.sleep(1)
