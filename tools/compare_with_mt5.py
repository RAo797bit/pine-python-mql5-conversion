"""
Compare the Python port with real MT5 output on the same bars.

1. Compile mql5/ATR_Trailing_Stop.mq5, then run mql5/Export_ATRStop_Values.mq5 on a chart.
   It writes MQL5\\Files\\atr_stop_export.csv  (time,open,high,low,close,stop).
2. Run:
       python tools/compare_with_mt5.py path/to/atr_stop_export.csv --atr-len 14 --mult 3.0

The Python indicator is computed from the exported OHLC and compared with the `stop` column MT5
produced. Exit code 0 means every comparable bar matched within the tolerance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from atr_trailing_stop import atr_trailing_stop  # noqa: E402


def compare(df: pd.DataFrame, atr_len: int, mult: float, tol: float) -> dict:
    py = atr_trailing_stop(df[["open", "high", "low", "close"]], atr_len, mult)
    mt5 = pd.to_numeric(df["stop"], errors="coerce").to_numpy()
    ours = py["stop"].to_numpy()

    both = ~np.isnan(mt5) & ~np.isnan(ours)
    diff = np.abs(mt5[both] - ours[both])
    return {
        "bars": int(len(df)),
        "compared": int(both.sum()),
        "max_abs_diff": float(diff.max()) if diff.size else float("nan"),
        "mismatches": int((diff > tol).sum()),
        "na_disagreements": int((np.isnan(mt5) != np.isnan(ours)).sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--atr-len", type=int, default=14)
    ap.add_argument("--mult", type=float, default=3.0)
    ap.add_argument("--tol", type=float, default=1e-6, help="absolute tolerance in price units")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    result = compare(df, args.atr_len, args.mult, args.tol)
    for k, v in result.items():
        print(f"{k:>18}: {v}")
    ok = result["compared"] > 0 and result["mismatches"] == 0 and result["na_disagreements"] == 0
    print("RESULT:", "MATCH" if ok else "DIFFERENCES FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
