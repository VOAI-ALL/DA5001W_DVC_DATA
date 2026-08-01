from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from fraud_mlops.inference import FraudModelService
from fraud_mlops.validation.schema import ValidationError


model_service = FraudModelService()

REQUEST_COUNT = Counter("fraud_api_requests_total", "Total prediction API requests", ["endpoint", "status"])
PREDICTION_COUNT = Counter("fraud_predictions_total", "Prediction counts by class", ["predicted_class"])
PREDICTION_LATENCY = Histogram("fraud_prediction_latency_seconds", "Prediction latency in seconds")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        model_service.load()
    except FileNotFoundError:
        # Health endpoint will report model_loaded=false until training is run.
        pass
    yield


app = FastAPI(title="Credit Card Fraud Detection API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "model_loaded": model_service.is_loaded}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    try:
        return model_service.model_info()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/predict")
def predict(payload: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = model_service.predict(payload)
    except FileNotFoundError as exc:
        REQUEST_COUNT.labels(endpoint="/predict", status="model_missing").inc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValidationError as exc:
        REQUEST_COUNT.labels(endpoint="/predict", status="validation_error").inc()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        REQUEST_COUNT.labels(endpoint="/predict", status="error").inc()
        raise HTTPException(status_code=500, detail="Prediction failed.") from exc

    PREDICTION_LATENCY.observe(time.perf_counter() - start)
    REQUEST_COUNT.labels(endpoint="/predict", status="success").inc()
    PREDICTION_COUNT.labels(predicted_class=str(result["predicted_class"])).inc()
    return result


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
