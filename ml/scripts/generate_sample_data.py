"""
Generates ml/data/sample/sample_projects.csv -- a CLEARLY SYNTHETIC/DEMO
dataset used only to exercise the training + prediction pipeline end to end.

This is NOT real MPLADS data. Every row has dataset_type=synthetic.

Run:
    python -m ml.scripts.generate_sample_data
"""
from __future__ import annotations

import datetime as dt
import random

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

STATES = ["Maharashtra", "Uttar Pradesh", "Tamil Nadu", "Karnataka", "Bihar"]
DISTRICTS = ["District A", "District B", "District C", "District D"]
AGENCIES = ["PWD", "Zilla Parishad", "Municipal Corporation", "Rural Development Dept"]
PROCUREMENT_METHODS = ["Open Tender", "Limited Tender", "Direct Contract"]

CATEGORY_PROFILES = {
    # category: (n_rows, base_cost_lakh, base_beneficiaries, base_duration_days)
    "bridge": (40, 45, 3000, 300),
    "road": (40, 30, 5000, 240),
    "school": (20, 20, 800, 180),  # below MIN_CATEGORY_SAMPLES=30 -> falls back to default model
}

ANOMALY_FRACTION = 0.10


def _random_date(start: dt.date, end: dt.date) -> dt.date:
    delta = (end - start).days
    return start + dt.timedelta(days=random.randint(0, max(delta, 0)))


def generate_project(idx: int, category: str, base_cost_lakh: float, base_beneficiaries: int,
                      base_duration: int, is_anomalous: bool) -> dict:
    estimated_cost = round(np.random.normal(base_cost_lakh, base_cost_lakh * 0.15), 2) * 100000
    estimated_cost = max(estimated_cost, 100000)

    cost_multiplier = np.random.uniform(1.6, 2.4) if is_anomalous and random.random() < 0.5 else np.random.uniform(0.9, 1.15)
    actual_cost = round(estimated_cost * cost_multiplier, 2)

    sanctioned_amount = round(estimated_cost * np.random.uniform(0.95, 1.05), 2)
    released_amount = round(sanctioned_amount * np.random.uniform(0.7, 1.0), 2)

    util_multiplier = np.random.uniform(1.2, 1.5) if is_anomalous and random.random() < 0.3 else np.random.uniform(0.6, 0.98)
    utilized_amount = round(released_amount * util_multiplier, 2)

    sanction_date = _random_date(dt.date(2023, 1, 1), dt.date(2023, 6, 30))
    work_order_date = sanction_date + dt.timedelta(days=random.randint(10, 45))
    planned_completion_date = work_order_date + dt.timedelta(days=base_duration)

    delay_days = int(np.random.normal(20, 15))
    if is_anomalous and random.random() < 0.5:
        delay_days += random.randint(120, 300)
    delay_days = max(delay_days, -10)

    completed = random.random() < 0.75
    actual_completion_date = (
        planned_completion_date + dt.timedelta(days=delay_days) if completed else None
    )

    physical_progress = round(np.random.uniform(60, 100), 1) if completed else round(np.random.uniform(10, 90), 1)
    financial_progress = round(physical_progress + np.random.uniform(-5, 5), 1)
    if is_anomalous and random.random() < 0.4:
        financial_progress = min(100.0, physical_progress + np.random.uniform(25, 45))
    financial_progress = float(np.clip(financial_progress, 0, 100))
    physical_progress = float(np.clip(physical_progress, 0, 100))

    inspection_count = np.random.poisson(3)
    if is_anomalous and random.random() < 0.4:
        inspection_count = 0
    last_inspection_date = (
        None if inspection_count == 0
        else _random_date(work_order_date, dt.date(2024, 6, 1))
    )

    issues_reported = np.random.poisson(2)
    issues_resolved = min(issues_reported, np.random.poisson(1.5))
    if is_anomalous and random.random() < 0.3:
        issues_resolved = 0

    contract_value = round(estimated_cost * np.random.uniform(0.9, 1.05), 2)
    estimated_tender_value = round(estimated_cost * np.random.uniform(0.95, 1.05), 2)
    bid_count = np.random.randint(2, 8)
    if is_anomalous and random.random() < 0.3:
        bid_count = 1
    winning_bid = round(estimated_tender_value * np.random.uniform(0.85, 1.0), 2)
    second_lowest_bid = round(winning_bid * np.random.uniform(1.0, 1.1), 2) if bid_count > 1 else winning_bid

    estimated_beneficiaries = max(int(np.random.normal(base_beneficiaries, base_beneficiaries * 0.2)), 50)
    population_served = int(estimated_beneficiaries * np.random.uniform(0.8, 1.1))

    return {
        "project_id": f"MPLAD-{category.upper()[:3]}-{idx:04d}",
        "project_name": f"{category.title()} Project {idx}",
        "project_type": category,
        "work_category": category,
        "state": random.choice(STATES),
        "district": random.choice(DISTRICTS),
        "constituency": f"Constituency {random.randint(1, 20)}",
        "location": f"Location {idx}",
        "latitude": round(np.random.uniform(8.0, 32.0), 5),
        "longitude": round(np.random.uniform(70.0, 88.0), 5),
        "estimated_cost": round(estimated_cost, 2),
        "sanctioned_amount": sanctioned_amount,
        "released_amount": released_amount,
        "utilized_amount": utilized_amount,
        "actual_cost": actual_cost,
        "number_of_payments": np.random.randint(1, 10),
        "sanction_date": sanction_date.isoformat(),
        "work_order_date": work_order_date.isoformat(),
        "planned_completion_date": planned_completion_date.isoformat(),
        "actual_completion_date": actual_completion_date.isoformat() if actual_completion_date else "",
        "delay_days": delay_days,
        "physical_progress": physical_progress,
        "financial_progress": financial_progress,
        "work_status": "Completed" if completed else "Ongoing",
        "inspection_count": int(inspection_count),
        "last_inspection_date": last_inspection_date.isoformat() if last_inspection_date else "",
        "issues_reported": int(issues_reported),
        "issues_resolved": int(issues_resolved),
        "implementing_agency": random.choice(AGENCIES),
        "agency_type": "Government",
        "contractor_id": f"CONT-{random.randint(1000, 9999)}",
        "contractor_name": f"Contractor {random.randint(1, 50)}",
        "contract_value": contract_value,
        "tender_id": f"TND-{random.randint(10000, 99999)}",
        "estimated_tender_value": estimated_tender_value,
        "bid_count": int(bid_count),
        "winning_bid": winning_bid,
        "second_lowest_bid": second_lowest_bid,
        "procurement_method": random.choice(PROCUREMENT_METHODS),
        "estimated_beneficiaries": estimated_beneficiaries,
        "population_served": population_served,
        "dataset_type": "synthetic",
    }


def main():
    rows = []
    idx = 1
    for category, (n_rows, base_cost, base_benef, base_duration) in CATEGORY_PROFILES.items():
        n_anomalous = max(1, int(n_rows * ANOMALY_FRACTION))
        anomalous_flags = [True] * n_anomalous + [False] * (n_rows - n_anomalous)
        random.shuffle(anomalous_flags)
        for i in range(n_rows):
            rows.append(generate_project(idx, category, base_cost, base_benef, base_duration, anomalous_flags[i]))
            idx += 1

    df = pd.DataFrame(rows)
    out_dir = __import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sample_projects.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} synthetic rows -> {out_path}")


if __name__ == "__main__":
    main()
