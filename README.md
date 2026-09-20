# Pine Script → Python → MQL5 Conversion (with parity checks)

A worked example of how I convert a TradingView indicator into a Python implementation and an MT5 indicator, and how I check that the three versions agree. The indicator is a standard ATR trailing stop, written from scratch for this demo.

> Conversion examples, not trading advice. The indicator has no claimed edge.

## What's in the repo

| Path | What it is |
|---|---|
| `pine/ATR_Trailing_Stop.pine` | The TradingView (Pine v5) source. |
| `python/atr_trailing_stop.py` | Python port: a fast version and a literal bar-by-bar reference transcription of the Pine semantics. |
| `mql5/ATR_Trailing_Stop.mq5` | MT5 indicator (stop line plus buy/sell arrows). Compiles with 0 errors, 0 warnings. |
| `mql5/Export_ATRStop_Values.mq5` | MT5 script that exports OHLC and indicator values to CSV for a real parity check. |
| `tools/compare_with_mt5.py` | Compares the Python port with an MT5 export and reports the largest difference. |
| `tests/test_parity.py` | 5 tests: Python vs reference across parameters, NA handling, ratchet behaviour, signal rules, comparison tool. |
| `reports/compile.log` | MetaEditor compile results. |

## The indicator

```
nLoss = mult * SMA(trueRange, atrLen)
stop  = ratchets up under price in an uptrend, down over price in a downtrend,
        and flips when the close goes through it
buy   = close crosses above the stop     sell = close crosses below the stop
```

## Why conversions go wrong, and what this repo handles

| Pine behaviour | How it is handled |
|---|---|
| `na` values until an indicator warms up | Stop stays NaN / `EMPTY_VALUE` until the SMA has `atrLen` bars |
| `nz(stop[1], src)` (previous stop, or the current source while it is `na`) | Same substitution in Python and MQL5 |
| `ta.tr(true)` on the first bar | True range is `high - low` there because there is no previous close |
| `ta.sma` vs `ta.atr` (RMA) | Uses SMA of true range on purpose, so it matches MT5's `iATR` |
| `var` state carried between bars | A plain loop in Python; the stop buffer in MQL5 (recalculation restarts from `prev_calculated - 1`) |
| `ta.crossover` / `ta.crossunder` | Explicit `a > b and a[1] <= b[1]` checks |

## What has and hasn't been verified

Verified here:
- Python port equals the literal Pine transcription to 1e-12 on random data, for several parameter sets (`python -m unittest discover -s tests -v`).
- Both MQL5 files compile with 0 errors and 0 warnings (see `reports/compile.log`).
- The comparison tool correctly reports a match and detects a drifting port (tested).

**Not verified here:** the MQL5 indicator has not been run against the Python output on a live MT5 chart in this repo, and the Pine script has not been run on TradingView here. The Python "reference" transcribes the Pine rules by hand; it is not the TradingView runtime. To close the loop on your own data, run the export script and `tools/compare_with_mt5.py` (below). On a real delivery I run this comparison and include the result.

## Run it

```bash
python -m unittest discover -s tests -v
```
Requires Python 3.10+ with `pandas` and `numpy`.

### Check the MQL5 port against Python on your own MT5 data
1. Compile `mql5/ATR_Trailing_Stop.mq5` (F7 in MetaEditor); the `.ex5` must be in `MQL5\Indicators`.
2. Drag `Export_ATRStop_Values` onto a chart. It writes `MQL5\Files\atr_stop_export.csv`.
3. `python tools/compare_with_mt5.py path/to/atr_stop_export.csv --atr-len 14 --mult 3.0`
   Exit code 0 and `RESULT: MATCH` means every comparable bar agrees.

## Need a conversion?

Send me the Pine source (or the indicator rules) and I'll deliver the Python and/or MQL5 version with a parity check like this one.
