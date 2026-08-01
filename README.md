# Real-Time Credit Card Fraud Detection MLOps Pipeline

This project implements the proposal in `Project_Proposal.md` as a local, reproducible MLOps demo using the credit card fraud dataset in `creditcard.csv`.

## Dataset

- Rows: 284,807
- Features: `Time`, `V1` to `V28`, `Amount`
- Target: `Class`
- Fraud rows: 492
- Fraud rate: approximately 0.173%

The model uses `LogisticRegression(class_weight="balanced")` to compensate for the severe class imbalance during training. Evaluation focuses on precision, recall, F1-score, ROC-AUC, and PR-AUC rather than accuracy.

`creditcard.csv` is intentionally not committed because it is a large local dataset. After cloning the repository, download the Kaggle dataset and place the CSV at the project root:

```text
creditcard.csv
```

## Project Structure

```text
api/                         FastAPI prediction service
airflow/dags/                Airflow retraining DAG
data/processed/              Generated train/test splits
models/                      Generated model artifacts
monitoring/prometheus/       Prometheus scrape config
monitoring/grafana/          Grafana dashboard JSON
reports/                     Generated metrics and reference stats
src/fraud_mlops/             Python package
tests/                       Unit and API tests
```

## Environment

For full environment recreation instructions, see:

```text
ENVIRONMENT_SETUP.md
```

Use the existing `MLDL` conda environment:

```powershell
conda activate MLDL
```

On this Windows setup, PowerShell is recommended. If you use Command Prompt, environment variable syntax is different.

For commands run from a non-activated shell, use:

```powershell
conda run -n MLDL <command>
```

## Train the Model

```powershell
$env:PYTHONPATH="src"
python -m fraud_mlops.training.train
```

This creates:

- `models/fraud_model.joblib`
- `reports/metrics.json`
- `reports/reference_stats.json`
- processed train/test split files under `data/processed/`

For a fast smoke run:

```powershell
$env:PYTHONPATH="src"
python -m fraud_mlops.training.train --sample-rows 5000
```

The verified full training run produced:

| Metric | Value |
|---|---:|
| Threshold | 0.95 |
| Precision | 0.3919 |
| Recall | 0.8878 |
| F1-score | 0.5438 |
| ROC-AUC | 0.9722 |
| PR-AUC | 0.7159 |

## Run the API

Train the model first, then start FastAPI:

```powershell
$env:PYTHONPATH="src;."
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `GET /health`
- `GET /model-info`
- `POST /predict`
- `GET /metrics`

Swagger UI is available at:

```text
http://127.0.0.1:8000/docs
```

## Example Prediction

Send a JSON body with all feature columns:

```json
{
  "Time": 0.0,
  "V1": -1.3598071337,
  "V2": -0.0727811733,
  "V3": 2.536346738,
  "V4": 1.3781552243,
  "V5": -0.3383207699,
  "V6": 0.4623877778,
  "V7": 0.2395985541,
  "V8": 0.0986979013,
  "V9": 0.3637869696,
  "V10": 0.090794172,
  "V11": -0.5515995333,
  "V12": -0.6178008558,
  "V13": -0.9913898472,
  "V14": -0.3111693537,
  "V15": 1.4681769721,
  "V16": -0.4704005253,
  "V17": 0.2079712419,
  "V18": 0.0257905802,
  "V19": 0.4039929603,
  "V20": 0.2514120982,
  "V21": -0.0183067779,
  "V22": 0.2778375756,
  "V23": -0.1104739102,
  "V24": 0.0669280749,
  "V25": 0.1285393583,
  "V26": -0.1891148439,
  "V27": 0.1335583767,
  "V28": -0.0210530535,
  "Amount": 149.62
}
```

## Run Tests

```powershell
$env:PYTHONPATH="src;."
pytest
```

## Kafka Streaming Simulation

Start Kafka through Docker Compose:

```powershell
docker compose up -d zookeeper kafka
```

Then run:

```powershell
$env:PYTHONPATH="src"
python -m fraud_mlops.streaming.kafka_producer --limit 100 --delay-seconds 0.05
```

The default topic is `credit-card-transactions`.

Verify messages:

```powershell
docker compose exec kafka kafka-console-consumer `
  --bootstrap-server kafka:29092 `
  --topic credit-card-transactions `
  --from-beginning `
  --max-messages 5
```

## Spark Structured Streaming

Start Spark:

```powershell
docker compose up -d spark-master spark-worker
```

Run the streaming consumer from the Spark container:

```powershell
docker compose exec -e PYTHONPATH=/app/src spark-master /opt/spark/bin/spark-submit `
  --conf spark.jars.ivy=/tmp/.ivy2 `
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.2 `
  /app/src/fraud_mlops/streaming/spark_streaming.py `
  --bootstrap-servers kafka:29092 `
  --topic credit-card-transactions `
  --checkpoint /tmp/fraud-stream-checkpoint-v2
```

The Spark image used by Docker Compose is `spark:python3-java17`, which currently reports Spark `4.1.2` and Scala `2.13.17`. The Kafka connector must match that Spark/Scala version.

If Spark starts but shows empty batches, publish more Kafka messages in another terminal:

```powershell
$env:PYTHONPATH="src"
python -m fraud_mlops.streaming.kafka_producer --limit 20 --delay-seconds 0.05
```

The current Spark job parses the Kafka transaction JSON and writes parsed records to the console. The next production extension would be calling the FastAPI inference endpoint or loading the model directly inside Spark workers.

## Docker Compose

```powershell
docker compose up --build
```

Services included:

- FastAPI
- Kafka
- Zookeeper
- MLflow
- Prometheus
- Grafana
- Spark master and worker
- Airflow webserver and scheduler

Airflow is available at `http://localhost:8082` with username `admin` and password `admin` after the init service completes.

Useful local service URLs:

| Service | URL |
|---|---|
| FastAPI Swagger | `http://127.0.0.1:8000/docs` |
| MLflow UI | `http://127.0.0.1:5000` |
| Prometheus | `http://localhost:9090` |
| Prometheus targets | `http://localhost:9090/targets` |
| Grafana | `http://localhost:3000` |
| Spark master UI | `http://localhost:8080` |
| Airflow | `http://localhost:8082` |

## MLflow

Start MLflow locally from the `MLDL` environment:

```powershell
mlflow ui --host 127.0.0.1 --port 5000
```

Open:

```text
http://127.0.0.1:5000
```

The verified training run logs to the experiment:

```text
credit-card-fraud-detection
```

The registered model is:

```text
credit-card-fraud-detector
```

## Prometheus and Grafana

Prometheus is configured to scrape the FastAPI app running on the Windows host:

```text
host.docker.internal:8000
```

Start monitoring services:

```powershell
docker compose up -d prometheus grafana
```

Check Prometheus targets:

```text
http://localhost:9090/targets
```

The `fraud-api` target should be `UP`.

In Grafana:

1. Add a Prometheus data source with URL `http://prometheus:9090`.
2. Import `monitoring/grafana/fraud_dashboard.json`.
3. Generate API predictions through Swagger to populate dashboard panels.

## Airflow

Start Airflow:

```powershell
docker compose up -d airflow-postgres airflow-init airflow-webserver airflow-scheduler
```

Open:

```text
http://localhost:8082
```

Login:

```text
Username: admin
Password: admin
```

Trigger the DAG:

```text
credit_card_fraud_retraining
```

The verified run completed both tasks successfully:

- `validate_dataset`
- `train_model`

## DVC

DVC pipeline metadata is included in `dvc.yaml`. The current `MLDL` environment did not have DVC installed during implementation, so DVC was scaffolded but not initialized locally.

After installing DVC, run:

```powershell
dvc init
dvc add creditcard.csv
$env:PYTHONPATH="src"
dvc repro
```

## MLOps Flow

1. Validate the dataset schema.
2. Train Logistic Regression with balanced class weights.
3. Tune the classification threshold on F1-score.
4. Save the model artifact and metrics.
5. Log the run to MLflow when available.
6. Serve predictions through FastAPI.
7. Expose Prometheus metrics.
8. Simulate real-time transactions with Kafka.
9. Parse streaming transactions with Spark.
10. Use Airflow DAG for retraining orchestration.

## Verified End-to-End Run

The pipeline was verified end to end with the following checks:

- `pytest`: 5 passed, with warnings only.
- Full training completed and registered MLflow model version 3.
- Swagger `/health`, `/model-info`, `/predict`, and `/metrics` worked.
- Prometheus scraped the host API successfully after using `host.docker.internal:8000`.
- Grafana imported the dashboard and showed updated prediction metrics.
- Kafka producer published transaction JSON records.
- Kafka console consumer read records from `credit-card-transactions`.
- Spark consumed and displayed transaction rows from Kafka.
- Airflow DAG `credit_card_fraud_retraining` completed successfully.

## Troubleshooting Notes From The Verified Run

| Issue | Fix |
|---|---|
| PowerShell command used in Command Prompt failed | Use PowerShell syntax `$env:PYTHONPATH="src;."`, or use `set PYTHONPATH=src;.` in Command Prompt |
| `kafka.vendor.six.moves` import error | Use `confluent-kafka`; the producer now imports `confluent_kafka.Producer` |
| Spark image `bitnami/spark:3.5` unavailable | Use official `spark:python3-java17` image |
| Spark Ivy cache failed under `/nonexistent` | Set `HOME=/tmp`, `IVY_HOME=/tmp/.ivy2`, and pass `--conf spark.jars.ivy=/tmp/.ivy2` |
| Spark Kafka connector mismatch | Use `org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.2` for Spark 4.1.2 / Scala 2.13 |
| Spark could not import `fraud_mlops` | Run `docker compose exec -e PYTHONPATH=/app/src ...` |
| Prometheus target was `DOWN` | Scrape `host.docker.internal:8000` because FastAPI was running on Windows host |
| Airflow task logs returned 403 | Use scheduler logs or direct task test; this is log-serving secret-key related, not the task failure |
| Airflow `train_model` failed with missing `joblib` | Webserver and scheduler now install ML dependencies before startup |
