"""
Parity tests. Run: python -m unittest discover -s tests -v

Checks that the fast Python port matches a literal bar-by-bar transcription of the Pine script,
and that the MT5 comparison tool detects both a match and a divergence.
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tools"))

from atr_trailing_stop import atr_trailing_stop, atr_trailing_stop_reference  # noqa: E402
from compare_with_mt5 import compare  # noqa: E402


def make_bars(n=1500, seed=1, start=100.0, vol=0.6):
    rng = np.random.default_rng(seed)
    close = start + np.cumsum(rng.normal(0, vol, n))
    open_ = np.concatenate([[start], close[:-1]])
    high = np.maximum(open_, close) + np.abs(rng.normal(0, vol / 2, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, vol / 2, n))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


class ParityTests(unittest.TestCase):
    def assert_same(self, a, b):
        np.testing.assert_allclose(a["tr"].to_numpy(), b["tr"].to_numpy(), rtol=0, atol=1e-12)
        np.testing.assert_allclose(a["stop"].to_numpy(), b["stop"].to_numpy(), rtol=0, atol=1e-12, equal_nan=True)
        np.testing.assert_array_equal(a["buy"].to_numpy(), b["buy"].to_numpy())
        np.testing.assert_array_equal(a["sell"].to_numpy(), b["sell"].to_numpy())

    def test_matches_reference_across_parameters(self):
        for seed in (1, 2, 3):
            df = make_bars(seed=seed)
            for atr_len, mult in [(1, 1.0), (5, 2.0), (14, 3.0), (30, 1.5)]:
                with self.subTest(seed=seed, atr_len=atr_len, mult=mult):
                    self.assert_same(
                        atr_trailing_stop(df, atr_len, mult),
                        atr_trailing_stop_reference(df, atr_len, mult),
                    )

    def test_stop_is_na_until_sma_is_valid(self):
        out = atr_trailing_stop(make_bars(n=50), atr_len=14, mult=3.0)
        self.assertTrue(out["stop"].iloc[:13].isna().all())
        self.assertFalse(np.isnan(out["stop"].iloc[13]))

    def test_stop_ratchets_with_the_trend(self):
        # steady uptrend: once long, the stop must never move down
        n = 300
        close = 100 + np.arange(n) * 0.5 + np.random.default_rng(5).normal(0, 0.05, n)
        df = pd.DataFrame({"open": close, "high": close + 0.2, "low": close - 0.2, "close": close})
        out = atr_trailing_stop(df, 14, 2.0)
        stop = out["stop"].to_numpy()[40:]
        self.assertTrue((np.diff(stop) >= -1e-12).all())
        self.assertTrue((out["close"].to_numpy()[40:] > stop).all())

    def test_signals_are_exclusive_and_only_on_cross(self):
        out = atr_trailing_stop(make_bars(seed=9), 14, 3.0)
        self.assertFalse((out["buy"] & out["sell"]).any())
        # a buy means price is above the stop now and was not above it on the previous bar
        idx = np.flatnonzero(out["buy"].to_numpy())
        self.assertGreater(len(idx), 0)
        for i in idx:
            self.assertGreater(out["close"].iloc[i], out["stop"].iloc[i])
            self.assertLessEqual(out["close"].iloc[i - 1], out["stop"].iloc[i - 1])


class CompareToolTests(unittest.TestCase):
    def test_detects_match_and_divergence(self):
        df = make_bars(n=400, seed=4)
        py = atr_trailing_stop(df, 14, 3.0)

        exported = df.copy()
        exported["stop"] = py["stop"]           # what a perfect MT5 port would export
        ok = compare(exported, 14, 3.0, 1e-6)
        self.assertGreater(ok["compared"], 300)
        self.assertEqual(ok["mismatches"], 0)
        self.assertEqual(ok["na_disagreements"], 0)

        broken = exported.copy()
        broken.loc[200:, "stop"] += 0.01        # simulate a port that drifts
        bad = compare(broken, 14, 3.0, 1e-6)
        self.assertGreater(bad["mismatches"], 0)


if __name__ == "__main__":
    unittest.main()
