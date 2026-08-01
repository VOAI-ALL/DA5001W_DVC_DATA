from sklearn.linear_model import LogisticRegression

from fraud_mlops.preprocessing import build_model_pipeline


def test_build_model_pipeline_has_expected_steps():
    pipeline = build_model_pipeline(LogisticRegression())
    assert list(pipeline.named_steps) == ["preprocessor", "model"]

