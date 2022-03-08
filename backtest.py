# 변동성 돌파 기법 backtest
import pyupbit
import numpy as np

# 7일간, 당일 시가, 고가, 저가, 종가, 거래량
df = pyupbit.get_ohlcv("KRW-BTC", count=7)

# 변동성 돌파 기준 범위 계산 (고가 - 저가) * 0.5
df["range"] = (df["high"] - df["low"]) * 0.5

# target, range 컬럼을 한칸씩 밑으로 내림 (전날이므로)
df["target"] = df["open"] + df["range"].shift(1)

# ror(수익률)
# 매수가 일어났을 때는 계산, 아닐경우 유지이므로 1
df["ror"] = np.where(df["high"] > df["target"], df["close"] / df["target"], 1)

# 누적 수익률, Draw Down 계산
df["hpr"] = df["ror"].cumprod()
df["dd"] = (df["hpr"].cummax() - df["hpr"]) / df["hpr"].cummax() * 100

# MDD 계산, 엑셀에 저장
print("MDD(%): ", df["dd"].max())
df.to_excel("dd.xlsx")
