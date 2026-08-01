from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud_mlops.config import FEATURE_COLUMNS


def build_preprocessor() -> ColumnTransformer:
    scaled_columns = ["Time", "Amount"]
    passthrough_columns = [column for column in FEATURE_COLUMNS if column not in scaled_columns]
    return ColumnTransformer(
        transformers=[
            ("scale_time_amount", StandardScaler(), scaled_columns),
            ("pca_features", "passthrough", passthrough_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def build_model_pipeline(estimator) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", estimator),
        ]
    )

