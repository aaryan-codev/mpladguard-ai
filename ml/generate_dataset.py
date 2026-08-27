import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

NUM_RECORDS = 500

# Sample parameters
constituencies = ["Pune", "Satara", "Kolhapur", "Sangli", "Nashik", "Nagpur", "Thane"]
work_types = [
    "Construction of Community Hall",
    "Installation of Solar Streetlights",
    "Concrete Road Construction",
    "Drinking Water Pipeline Installation",
    "Public Library Building",
    "Supply of Benches to Public Park"
]
vendors = [f"VEND_{1000 + i}" for i in range(40)]
vendor_banks = {v: f"BANK_ACC_{random.randint(10000, 99999)}" for v in vendors}
vendor_ips = {v: f"192.168.1.{random.randint(2, 254)}" for v in vendors}

# Inject deliberate fraud/cartel patterns
# Fake ring: Vendors 5, 6, 7 share the same bank account and IP address
cartel_vendors = ["VEND_1005", "VEND_1006", "VEND_1007"]
cartel_bank = "BANK_ACC_77777"
cartel_ip = "192.168.1.99"
for v in cartel_vendors:
    vendor_banks[v] = cartel_bank
    vendor_ips[v] = cartel_ip

records = []
base_date = datetime(2025, 1, 1)

for i in range(1, NUM_RECORDS + 1):
    project_id = f"MPLAD_2026_{10000 + i}"
    constituency = random.choice(constituencies)
    work = random.choice(work_types)
    vendor = random.choice(vendors)
    
    # Base estimated cost
    base_cost = random.randint(200000, 2500000)
    actual_cost = base_cost
    
    # Flag generation
    is_anomaly = 0
    anomaly_type = "None"

    # Fraud Scenario 1: Cost Inflated Outlier (10% chance)
    if random.random() < 0.10:
        actual_cost = int(base_cost * random.uniform(2.5, 4.0))
        is_anomaly = 1
        anomaly_type = "Price Inflation Outlier"

    # Fraud Scenario 2: Geotag / EXIF Coordinate Tampering (8% chance)
    # Valid Pune Lat/Long bounding box vs Out-of-bounds coordinate
    lat = round(random.uniform(18.4, 18.6), 6)
    lon = round(random.uniform(73.7, 73.9), 6)
    if random.random() < 0.08:
        lat = round(random.uniform(28.5, 28.7), 6) # Shifted to Delhi area
        lon = round(random.uniform(77.1, 77.3), 6)
        is_anomaly = 1
        anomaly_type = "GPS Geofence Violation"

    # Fraud Scenario 3: Cartel Circular Bidding
    if vendor in cartel_vendors:
        is_anomaly = 1
        anomaly_type = "Vendor Cartel Cluster"

    sanction_date = base_date + timedelta(days=random.randint(1, 365))
    
    records.append({
        "project_id": project_id,
        "constituency": constituency,
        "work_description": work,
        "vendor_id": vendor,
        "vendor_bank_acc": vendor_banks[vendor],
        "vendor_ip_address": vendor_ips[vendor],
        "sanctioned_amount_inr": base_cost,
        "invoiced_amount_inr": actual_cost,
        "latitude": lat,
        "longitude": lon,
        "sanction_date": sanction_date.strftime("%Y-%m-%d"),
        "is_fraud_label": is_anomaly,
        "anomaly_reason": anomaly_type
    })

df = pd.DataFrame(records)

# Ensure data folder exists inside ml/
os.makedirs("data", exist_ok=True)
output_path = "data/synthetic_sakshi_data.csv"
df.to_csv(output_path, index=False)
print(f"Successfully generated {NUM_RECORDS} MPLADS project records at '{output_path}'!")