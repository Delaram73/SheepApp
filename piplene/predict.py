# pipeline/predict.py
import os
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

SEQ_LENGTH = 30

def build_seq_3(df_flat: pd.DataFrame):
    x = np.stack([
        df_flat[[f"x_{i}" for i in range(1, SEQ_LENGTH+1)]].to_numpy(np.float32),
        df_flat[[f"y_{i}" for i in range(1, SEQ_LENGTH+1)]].to_numpy(np.float32),
        df_flat[[f"z_{i}" for i in range(1, SEQ_LENGTH+1)]].to_numpy(np.float32),
    ], axis=-1)
    return x  # shape: (N, 30, 3)

def predict_labels(df_flat: pd.DataFrame, model_path: str, labels: list[str]) -> pd.DataFrame:
    model = load_model(model_path)
    x = build_seq_3(df_flat)
    probs = model.predict(x, verbose=0)
    idx = probs.argmax(axis=1)
    conf = probs.max(axis=1)
    out = df_flat.copy()
    out["behaviour"] = [labels[i] for i in idx]
    out["confidence"] = conf
    return out

def write_behaviour_to_influx(
    df_labels: pd.DataFrame, *,
    url: str, org: str, bucket: str, token: str,
    measurement: str = "behavior_pred",
    tag_sheep: str = "sheep_id",
) -> int:
    times = pd.to_datetime(df_labels["Time"], utc=True, errors="coerce")
    mask = times.notna()
    if not mask.any():
        return 0

    with InfluxDBClient(url=url, token=token, org=org) as client:
        with client.write_api(write_options=SYNCHRONOUS) as w:
            points = []
            for t, beh, conf, sheep in zip(
                times[mask],
                df_labels.loc[mask, "behaviour"],
                df_labels.loc[mask, "confidence"],
                df_labels.loc[mask, tag_sheep] if tag_sheep in df_labels.columns else [None]*mask.sum()
            ):
                p = (
                    Point(measurement)
                    .field("behaviour", str(beh))
                    .field("confidence", float(conf))
                    .time(t.to_pydatetime(), WritePrecision.NS)
                )
                if sheep:
                    p = p.tag("sheep_id", str(sheep))
                points.append(p)
            w.write(bucket=bucket, org=org, record=points)
    return len(points)

