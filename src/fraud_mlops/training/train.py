from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from fraud_mlops.config import (
    DATA_PATH,
    FEATURE_COLUMNS,
    METRICS_PATH,
    MODEL_DIR,
    MODEL_PATH,
    PROCESSED_DIR,
    RANDOM_STATE,
    REFERENCE_STATS_PATH,
    REPORT_DIR,
    TARGET_COLUMN,
)
from fraud_mlops.preprocessing import build_model_pipeline
from fraud_mlops.validation import validate_dataframe


def choose_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, dict[str, float]]:
    candidates = np.linspace(0.05, 0.95, 181)
    best_threshold = 0.5
    best_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    for threshold in candidates:
        predictions = (probabilities >= threshold).astype(int)
        metrics = {
            "precision": precision_score(y_true, predictions, zero_division=0),
            "recall": recall_score(y_true, predictions, zero_division=0),
            "f1": f1_score(y_true, predictions, zero_division=0),
        }
        if metrics["f1"] > best_metrics["f1"]:
            best_threshold = float(threshold)
            best_metrics = metrics

    return best_threshold, best_metrics


def evaluate(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "threshold": threshold,
        "precision": precision_score(y_true, predictions, zero_division=0),
        "recall": recall_score(y_true, predictions, zero_division=0),
        "f1": f1_score(y_true, predictions, zero_division=0),
        "roc_auc": roc_auc_score(y_true, probabilities),
        "pr_auc": average_precision_score(y_true, probabilities),
        "confusion_matrix": {
            "tn": int(matrix[0, 0]),
            "fp": int(matrix[0, 1]),
            "fn": int(matrix[1, 0]),
            "tp": int(matrix[1, 1]),
        },
    }


def log_with_mlflow(metrics: dict, model, model_path: Path) -> None:
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        return

    mlflow.set_experiment("credit-card-fraud-detection")
    with mlflow.start_run(run_name="logistic-regression-balanced"):
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_param("max_iter", 1000)
        mlflow.log_param("threshold", metrics["threshold"])
        for name in ["precision", "recall", "f1", "roc_auc", "pr_auc"]:
            mlflow.log_metric(name, metrics[name])
        mlflow.log_artifact(str(model_path))
        mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name="credit-card-fraud-detector")


def train(data_path: Path = DATA_PATH, sample_rows: int | None = None) -> dict:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path, nrows=sample_rows)
    validate_dataframe(df, require_target=True)

    x = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN].astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    estimator = LogisticRegression(class_weight="balanced", max_iter=1000, solver="lbfgs")
    pipeline = build_model_pipeline(estimator)
    pipeline.fit(x_train, y_train)

    probabilities = pipeline.predict_proba(x_test)[:, 1]
    threshold, _ = choose_threshold(y_test.to_numpy(), probabilities)
    metrics = evaluate(y_test.to_numpy(), probabilities, threshold)

    artifact = {
        "pipeline": pipeline,
        "threshold": threshold,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": "credit-card-fraud-detector",
        "model_version": "local-0.1.0",
    }
    joblib.dump(artifact, MODEL_PATH)

    x_train.to_csv(PROCESSED_DIR / "x_train.csv", index=False)
    x_test.to_csv(PROCESSED_DIR / "x_test.csv", index=False)
    y_train.to_csv(PROCESSED_DIR / "y_train.csv", index=False)
    y_test.to_csv(PROCESSED_DIR / "y_test.csv", index=False)

    reference_stats = x_train[["Amount", "Time", "V1", "V2", "V3", "V4"]].agg(["mean", "std"]).to_dict()
    REFERENCE_STATS_PATH.write_text(json.dumps(reference_stats, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    log_with_mlflow(metrics, pipeline, MODEL_PATH)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the fraud detection model.")
    parser.add_argument("--data-path", type=Path, default=DATA_PATH)
    parser.add_argument("--sample-rows", type=int, default=None)
    args = parser.parse_args()
    metrics = train(args.data_path, args.sample_rows)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

