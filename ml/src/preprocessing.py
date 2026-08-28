"""
Preprocessing pipeline.

Builds a single sklearn Pipeline step (median imputation + robust scaling)
that is combined with the Isolation Forest into ONE saved artifact per
category model. This guarantees inference always applies the exact same
transformation used at training time -- there is no separate/duplicated
preprocessing logic anywhere else in the codebase.
"""
from __future__ import annotations

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from . import config


def build_preprocessor() -> Pipeline:
    """
    Median imputation (robust to skewed financial data) followed by
    RobustScaler (robust to outliers, which anomaly detection data is
    expected to contain by definition).
    """
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )


def get_feature_names() -> list[str]:
    return list(config.ENGINEERED_FEATURES)
