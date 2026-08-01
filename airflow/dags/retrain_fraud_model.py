from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="credit_card_fraud_retraining",
    description="Validate data, retrain the fraud model, and log metrics.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["mlops", "fraud"],
)
def fraud_retraining_dag():
    @task
    def validate_dataset() -> str:
        import pandas as pd

        from fraud_mlops.config import DATA_PATH
        from fraud_mlops.validation import validate_dataframe

        df = pd.read_csv(DATA_PATH)
        validate_dataframe(df, require_target=True)
        return f"Validated {len(df)} rows."

    @task
    def train_model() -> dict:
        from fraud_mlops.training.train import train

        return train()

    validation_result = validate_dataset()
    metrics = train_model()
    validation_result >> metrics


fraud_retraining_dag()

