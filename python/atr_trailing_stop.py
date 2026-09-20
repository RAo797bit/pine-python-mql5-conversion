"""
Python port of pine/ATR_Trailing_Stop.pine.

Two implementations of the same rules:

  atr_trailing_stop()            the production version (numpy arrays, fast)
  atr_trailing_stop_reference()  a deliberately literal, bar-by-bar transcription of the Pine
                                 semantics (na / nz / series history), used to cross-check the first

tests/test_parity.py asserts the two agree on random data and parameters.

Pine -> Python translation notes
  ta.tr(true)          first bar has no previous close, so TR = high - low there
  ta.sma(x, n)         na until n bars exist (first valid value at index n-1)
  nz(stop[1], src)     previous stop, or the current source while the previous stop is na
  var float stop = na  state carried from bar to bar
  ta.crossover(a, b)   a > b and a[1] <= b[1]        (false while either is na)
  ta.crossunder(a, b)  a < b and a[1] >= b[1]
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    tr = high - low
    prev_close = close[:-1]
    tr[1:] = np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - prev_close), np.abs(low[1:] - prev_close)])
    return tr


def atr_trailing_stop(df: pd.DataFrame, atr_len: int = 14, mult: float = 3.0) -> pd.DataFrame:
    """Return df with columns: tr, n_loss, stop, buy, sell (buy/sell are booleans)."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)

    tr = _true_range(high, low, close)
    sma = pd.Series(tr).rolling(atr_len).mean().to_numpy()
    n_loss = mult * sma

    stop = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(n_loss[i]):
            continue                                   # Pine: stop stays na until the SMA is valid
        src = close[i]
        prev_stop = stop[i - 1] if i > 0 and not np.isnan(stop[i - 1]) else src
        prev_src = close[i - 1] if i > 0 else np.nan
        if src > prev_stop and prev_src > prev_stop:
            stop[i] = max(prev_stop, src - n_loss[i])
        elif src < prev_stop and prev_src < prev_stop:
            stop[i] = min(prev_stop, src + n_loss[i])
        elif src > prev_stop:
            stop[i] = src - n_loss[i]
        else:
            stop[i] = src + n_loss[i]

    prev_close = np.concatenate([[np.nan], close[:-1]])
    prev_stop_arr = np.concatenate([[np.nan], stop[:-1]])
    with np.errstate(invalid="ignore"):
        buy = (close > stop) & (prev_close <= prev_stop_arr)
        sell = (close < stop) & (prev_close >= prev_stop_arr)

    out = df.copy()
    out["tr"] = tr
    out["n_loss"] = n_loss
    out["stop"] = stop
    out["buy"] = buy
    out["sell"] = sell
    return out


def atr_trailing_stop_reference(df: pd.DataFrame, atr_len: int = 14, mult: float = 3.0) -> pd.DataFrame:
    """Literal bar-by-bar transcription of the Pine script (slow, for cross-checking only)."""
    na = math.nan

    def isna(x: float) -> bool:
        return x != x

    def nz(x: float, replacement: float) -> float:
        return replacement if isna(x) else x

    highs, lows, closes = df["high"].tolist(), df["low"].tolist(), df["close"].tolist()
    tr_hist: list[float] = []
    stop_hist: list[float] = []
    buys: list[bool] = []
    sells: list[bool] = []

    for i in range(len(closes)):
        # ta.tr(true)
        if i == 0:
            tr = highs[0] - lows[0]
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_hist.append(tr)

        # ta.sma(tr, atrLen)
        sma = sum(tr_hist[-atr_len:]) / atr_len if len(tr_hist) >= atr_len else na
        n_loss = mult * sma if not isna(sma) else na

        src = closes[i]
        src1 = closes[i - 1] if i > 0 else na
        stop1 = stop_hist[i - 1] if i > 0 else na
        prev_stop = nz(stop1, src)

        if isna(n_loss):
            stop = na
        elif src > prev_stop and (not isna(src1)) and src1 > prev_stop:
            stop = max(prev_stop, src - n_loss)
        elif src < prev_stop and (not isna(src1)) and src1 < prev_stop:
            stop = min(prev_stop, src + n_loss)
        elif src > prev_stop:
            stop = src - n_loss
        else:
            stop = src + n_loss
        stop_hist.append(stop)

        crossover = (not isna(stop)) and (not isna(stop1)) and src > stop and src1 <= stop1
        crossunder = (not isna(stop)) and (not isna(stop1)) and src < stop and src1 >= stop1
        buys.append(crossover)
        sells.append(crossunder)

    out = df.copy()
    out["tr"] = tr_hist
    out["stop"] = stop_hist
    out["buy"] = buys
    out["sell"] = sells
    return out
