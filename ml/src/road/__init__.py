"""
Road-domain ML plugin for MPLADGuard-AI.

This package is intentionally self-contained: it defines its own raw
schema, validation rules, feature engineering, and config, separate
from the generic multi-category pipeline in ml/src/{config,
validation, feature_engineering}.py.

Why a separate module instead of extending the generic pipeline:
the generic pipeline's REQUIRED_COLUMNS and engineered features
(fund_utilization_ratio, contract_estimate_ratio, tender_estimate_ratio,
inspection_gap_days, etc.) depend on financial-flow, contractor, tender,
and inspection columns that the current road dataset does not contain.
Forcing road data through that pipeline would require fabricating
those values, which MPLADGuard-AI's responsible-AI policy forbids.

The road module reuses genuinely domain-agnostic infrastructure from
the generic pipeline (scoring.normalize_to_risk_score,
scoring.compute_score_reference, preprocessing.build_preprocessor,
and explain.py's z-score explanation logic, now parameterized) rather
than duplicating it.

This is the template for adding future domains (bridge, school,
water, ...): each gets its own ml/src/<domain>/ package with the same
five files (config, schema, validation, feature_engineering, train),
and predict.py dispatches to the right one based on the "domain" key
stored in each trained model's metadata.
"""
