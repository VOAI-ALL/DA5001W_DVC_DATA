# Implementation Mapping Against Project Plan

This document maps the original `Implementation_Plan.md` phases to the files and artifacts created in the project workspace.

## Current Implementation Status

| Plan Area | Status | Evidence |
|---|---|---|
| Local project skeleton | Implemented | `src/`, `api/`, `airflow/dags/`, `monitoring/`, `tests/`, `models/`, `reports/`, `data/processed/` |
| MLDL environment compatibility | Verified | Tests and training were run with the `MLDL` conda environment |
| Baseline model | Implemented | `src/fraud_mlops/training/train.py`, `models/fraud_model.joblib` |
| API serving | Implemented | `api/main.py`, `Dockerfile.api` |
| MLflow tracking | Implemented locally | Training script logs runs and registers `credit-card-fraud-detector` when MLflow is available |
| Kafka streaming | Implemented and verified | `src/fraud_mlops/streaming/kafka_producer.py`, Kafka service in `docker-compose.yml`; messages were published and consumed |
| Spark streaming | Implemented and verified for stream parsing | `src/fraud_mlops/streaming/spark_streaming.py`, Spark services in `docker-compose.yml`; rows were displayed from Kafka |
| Airflow orchestration | Implemented and verified | `airflow/dags/retrain_fraud_model.py`, Airflow services in `docker-compose.yml`; DAG completed successfully |
| Monitoring | Implemented and verified | Prometheus metrics in API, `monitoring/prometheus/prometheus.yml`, `monitoring/grafana/fraud_dashboard.json`; Prometheus target was UP and Grafana showed data |
| DVC | Scaffolded | `dvc.yaml`, `params.yaml`, `.dvcignore`; DVC was not initialized because it was not installed in `MLDL` |
| CI/CD | Scaffolded | `.gitlab-ci.yml` |
| Tests | Implemented and passed | `tests/`, 5 passing pytest tests |

## Phase 1: Repository and Environment Setup

### Planned

- Create project layout.
- Add dependency management.
- Add `.gitignore`.
- Initialize DVC and dataset/model versioning.
- Add README.

### Created

- `.gitignore`
- `requirements.txt`
- `pyproject.toml`
- `README.md`
- `dvc.yaml`
- `params.yaml`
- `.dvcignore`
- `src/fraud_mlops/`
- `api/`
- `airflow/dags/`
- `monitoring/prometheus/`
- `monitoring/grafana/`
- `tests/`
- `models/`
- `reports/`
- `data/processed/`

### Notes

DVC was scaffolded but not initialized because `dvc` was not installed in the `MLDL` environment at implementation time.

## Phase 2: Data Validation and Preprocessing

### Planned

- Define stable schema.
- Validate required columns, missing values, numeric types, class labels, and non-negative amount.
- Scale `Amount` and optionally `Time`.
- Preserve PCA features.
- Save train/test splits.

### Created

- `src/fraud_mlops/config.py`
- `src/fraud_mlops/validation/schema.py`
- `src/fraud_mlops/preprocessing.py`
- `data/processed/x_train.csv`
- `data/processed/x_test.csv`
- `data/processed/y_train.csv`
- `data/processed/y_test.csv`

### Implemented Behavior

- Validates `Time`, `V1` to `V28`, `Amount`, and `Class`.
- Rejects missing columns, missing values, non-numeric values, invalid class labels, and negative transaction amounts.
- Uses `StandardScaler` for `Time` and `Amount`.
- Passes `V1` to `V28` through unchanged.
- Uses stratified train/test splitting.

## Phase 3: Baseline Model Training

### Planned

- Train Logistic Regression with `class_weight="balanced"`.
- Evaluate precision, recall, F1-score, ROC-AUC, PR-AUC, and confusion matrix.
- Tune classification threshold.
- Save model artifact.
- Add unit tests.

### Created

- `src/fraud_mlops/training/train.py`
- `models/fraud_model.joblib`
- `reports/metrics.json`
- `tests/test_preprocessing.py`
- `tests/test_validation.py`

### Full Training Metrics

| Metric | Value |
|---|---:|
| Threshold | 0.95 |
| Precision | 0.3919 |
| Recall | 0.8878 |
| F1-score | 0.5438 |
| ROC-AUC | 0.9722 |
| PR-AUC | 0.7159 |
| True negatives | 56,729 |
| False positives | 135 |
| False negatives | 11 |
| True positives | 87 |

## Phase 4: MLflow Experiment Tracking and Model Registry

### Planned

- Track parameters, metrics, and artifacts.
- Register best model.

### Created

- MLflow logging inside `src/fraud_mlops/training/train.py`
- Local `mlruns/` output when training is executed
- MLflow service in `docker-compose.yml`

### Implemented Behavior

The training script logs:

- Model type
- Class weight
- Maximum iterations
- Tuned threshold
- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC
- Model artifact

It also registers the model as `credit-card-fraud-detector` when MLflow is available.

## Phase 5: FastAPI Prediction Service

### Planned

- Add `/health`, `/model-info`, `/predict`, and `/metrics`.
- Validate JSON payloads.
- Return probability, predicted class, model version, and threshold.
- Expose Prometheus metrics.

### Created

- `api/main.py`
- `api/__init__.py`
- `src/fraud_mlops/inference/model.py`
- `tests/test_api.py`
- `Dockerfile.api`

### Implemented Endpoints

- `GET /health`
- `GET /model-info`
- `POST /predict`
- `GET /metrics`

### Prometheus Metrics

- `fraud_api_requests_total`
- `fraud_predictions_total`
- `fraud_prediction_latency_seconds`

## Phase 6: Kafka-Based Streaming Simulation

### Planned

- Replay historical transactions into Kafka.
- Exclude `Class` from inference messages.
- Add configurable stream speed and limit.
- Use JSON messages.

### Created

- `src/fraud_mlops/streaming/kafka_producer.py`
- Kafka and Zookeeper services in `docker-compose.yml`

### Implemented Behavior

The Kafka producer:

- Reads `creditcard.csv`.
- Publishes only feature columns, excluding `Class`.
- Sends JSON messages.
- Supports configurable topic, bootstrap server, delay, and message limit.
- Uses `confluent_kafka.Producer` because the available `kafka-python` package failed under Python 3.12.

### Verification

- Published 100 transactions to `credit-card-transactions`.
- Verified records using `kafka-console-consumer`.

## Phase 7: Spark Structured Streaming Processing

### Planned

- Consume Kafka topic.
- Parse incoming records.
- Validate transaction schema.
- Write predictions or stream output.

### Created

- `src/fraud_mlops/streaming/spark_streaming.py`
- Spark master and worker services in `docker-compose.yml`

### Implemented Behavior

The Spark job:

- Consumes Kafka messages.
- Parses JSON using the expected transaction schema.
- Writes parsed records to the console sink.
- Runs in the official `spark:python3-java17` Docker image.
- Uses Spark `4.1.2`, Scala `2.13`, and connector `org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.2`.

### Remaining Extension

The current Spark job validates the streaming shape and parsing path. Calling the FastAPI prediction endpoint or loading the model inside Spark workers is the next extension.

### Verification

Spark consumed Kafka records and displayed parsed transaction rows after setting `PYTHONPATH=/app/src` and using a writable Ivy cache.

## Phase 8: Airflow Training and Retraining Workflow

### Planned

- Validate dataset.
- Preprocess dataset.
- Train model.
- Evaluate model.
- Register/promote model if criteria pass.

### Created

- `airflow/dags/retrain_fraud_model.py`
- Airflow Postgres, init, webserver, and scheduler services in `docker-compose.yml`

### Implemented Behavior

The DAG:

- Validates the full dataset.
- Runs the training pipeline.
- Produces updated model and metrics artifacts.
- Logs to MLflow when available.

### Verification

The Airflow DAG `credit_card_fraud_retraining` completed successfully after recreating the webserver and scheduler containers with project ML dependencies installed.

### Remaining Extension

Explicit production-vs-candidate model comparison and stage promotion rules are scaffolded conceptually but not yet coded as separate DAG tasks.

## Phase 9: Monitoring with Prometheus and Grafana

### Planned

- Monitor API latency, request rate, prediction counts, error rate, and model behavior.
- Provide Grafana dashboard.

### Created

- Prometheus metrics in `api/main.py`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/grafana/fraud_dashboard.json`
- Prometheus and Grafana services in `docker-compose.yml`

### Implemented Dashboard Panels

- API request rate
- Prediction latency
- Predictions by class

### Verification

- Prometheus target `fraud-api` was verified as `UP`.
- Prometheus returned `fraud_predictions_total`.
- Grafana dashboard imported successfully and updated after API predictions.

## Phase 10: Drift Detection

### Planned

- Compare live input windows against reference statistics.
- Track drift for `Amount` and selected PCA features.

### Created

- `src/fraud_mlops/drift.py`
- `reports/reference_stats.json`

### Implemented Behavior

The drift module:

- Loads reference training statistics.
- Computes mean shift in standard-deviation units.
- Flags drift when the shift is at least 3 standard deviations.

### Remaining Extension

The drift function is implemented as a reusable module but is not yet wired into a live scheduled job or Prometheus metric exporter.

## Phase 11: Docker Compose Integration

### Planned

- Run the stack locally with Compose.
- Include Kafka, Spark, MLflow, FastAPI, Airflow, Prometheus, and Grafana.

### Created

- `docker-compose.yml`
- `Dockerfile.api`

### Services Included

- FastAPI
- Kafka
- Zookeeper
- MLflow
- Prometheus
- Grafana
- Spark master
- Spark worker
- Airflow Postgres
- Airflow init
- Airflow webserver
- Airflow scheduler

### Verification

`docker compose config` parsed successfully. Docker emitted a local warning about access to `C:\Users\creak\.docker\config.json`, but the Compose configuration itself was valid.

During the end-to-end run, the Spark image was changed to `spark:python3-java17` because `bitnami/spark:3.5` was not available. Spark services now use a writable Ivy cache via `HOME=/tmp` and `IVY_HOME=/tmp/.ivy2`.

## Phase 12: CI/CD Pipeline

### Planned

- Run tests.
- Build Docker image.
- Support GitLab CI/CD.

### Created

- `.gitlab-ci.yml`
- `tests/test_api.py`
- `tests/test_preprocessing.py`
- `tests/test_validation.py`

### Implemented CI Stages

- `test`
- `build`

The pipeline installs dependencies, runs `pytest`, and builds the API Docker image.

## Verification Summary

| Check | Result |
|---|---|
| `pytest` in `MLDL` | Passed, 5 tests |
| Full model training in `MLDL` | Passed |
| API prediction smoke test | Passed |
| `python -m compileall src api airflow tests` | Passed |
| `docker compose config` | Passed with local Docker config warning |
| Kafka producer and consumer | Passed |
| Spark Kafka streaming parse | Passed |
| Prometheus target scrape | Passed |
| Grafana dashboard import and update | Passed |
| Airflow retraining DAG | Passed |

## Files Created or Updated

### Core Package

- `src/fraud_mlops/__init__.py`
- `src/fraud_mlops/config.py`
- `src/fraud_mlops/preprocessing.py`
- `src/fraud_mlops/drift.py`
- `src/fraud_mlops/validation/__init__.py`
- `src/fraud_mlops/validation/schema.py`
- `src/fraud_mlops/training/__init__.py`
- `src/fraud_mlops/training/train.py`
- `src/fraud_mlops/inference/__init__.py`
- `src/fraud_mlops/inference/model.py`
- `src/fraud_mlops/streaming/__init__.py`
- `src/fraud_mlops/streaming/kafka_producer.py`
- `src/fraud_mlops/streaming/spark_streaming.py`

### API

- `api/__init__.py`
- `api/main.py`
- `Dockerfile.api`

### Orchestration and Monitoring

- `airflow/dags/retrain_fraud_model.py`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/grafana/fraud_dashboard.json`
- `docker-compose.yml`

### Project Configuration

- `.gitignore`
- `.gitlab-ci.yml`
- `.dvcignore`
- `dvc.yaml`
- `params.yaml`
- `pyproject.toml`
- `requirements.txt`
- `README.md`

### Tests

- `tests/test_api.py`
- `tests/test_preprocessing.py`
- `tests/test_validation.py`

### Generated Artifacts

- `models/fraud_model.joblib`
- `reports/metrics.json`
- `reports/reference_stats.json`
- `data/processed/x_train.csv`
- `data/processed/x_test.csv`
- `data/processed/y_train.csv`
- `data/processed/y_test.csv`

## Gaps and Next Steps

| Gap | Recommended Next Step |
|---|---|
| DVC not initialized | Install DVC in `MLDL`, then run `dvc init`, `dvc add creditcard.csv`, and `dvc repro` |
| Spark parses records but does not yet call model inference | Add FastAPI calls or distributed model loading in the Spark streaming job |
| Airflow retraining works but promotion rules are not separate tasks | Add candidate-vs-production comparison and explicit model promotion task |
| Drift detection is not scheduled | Wire `src/fraud_mlops/drift.py` into Airflow or expose drift metrics through the API |
| Grafana dashboard is minimal | Add panels for fraud probability distribution, error rate, and drift once live metrics are emitted |
