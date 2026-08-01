from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fraud_mlops.config import REFERENCE_STATS_PATH


def load_reference_stats(path: Path = REFERENCE_STATS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_basic_drift(current: pd.DataFrame, reference_path: Path = REFERENCE_STATS_PATH) -> dict:
    reference = load_reference_stats(reference_path)
    results = {}
    for column, stats in reference.items():
        if column not in current.columns:
            continue
        ref_mean = float(stats["mean"])
        ref_std = max(float(stats["std"]), 1e-9)
        current_mean = float(current[column].mean())
        z_score = abs(current_mean - ref_mean) / ref_std
        results[column] = {
            "reference_mean": ref_mean,
            "current_mean": current_mean,
            "mean_shift_std_units": z_score,
            "drift_flag": z_score >= 3.0,
        }
    return results

