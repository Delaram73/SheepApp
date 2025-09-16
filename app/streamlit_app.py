
import streamlit as st
# app/streamlit_app.py
import os, tempfile
import streamlit as st
import pandas as pd
from pipeline.gt3x_to_csv import gt3x_to_df
from pipeline.flatten import flatten_xyz
from pipeline.predict import predict_labels, write_behaviour_to_influx

st.set_page_config(page_title="Sheep Behaviour Inference", layout="wide")
st.title("🐑 Sheep Behaviour – Upload & Predict")

# Secrets (Streamlit Cloud: App → Settings → Secrets)
INFLUX_URL    = st.secrets["influx"]["url"]
INFLUX_ORG    = st.secrets["influx"]["org"]
INFLUX_BUCKET = st.secrets["influx"]["bucket"]
INFLUX_TOKEN  = st.secrets["influx"]["token"]
MODEL_PATH    = st.secrets["model"]["path"]    # e.g., "models/sheep_blstm_model.h5"
LABELS        = st.secrets["model"]["labels"]  # e.g., ["grazing","lying","walking","..."]

uploaded = st.file_uploader("Upload a file (.gt3x or .csv)", type=["gt3x","csv"], accept_multiple_files=False)

if uploaded:
    with st.spinner("Reading data..."):
        if uploaded.name.lower().endswith(".gt3x"):
            # Save to temp file because pygt3x needs a path
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gt3x") as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            df = gt3x_to_df(tmp_path)
            os.unlink(tmp_path)
        else:
            df = pd.read_csv(uploaded)

        if "Time" not in df.columns and "time" in df.columns:
            df = df.rename(columns={"time":"Time"})

        st.write("Preview:", df.head())

    with st.spinner("Flattening..."):
        dff = flatten_xyz(df, seq_len=30, time_col="Time")
        st.write("Flattened shape:", dff.shape)
        st.dataframe(dff.head())

    with st.spinner("Predicting..."):
        out = predict_labels(dff, MODEL_PATH, LABELS)
        st.subheader("Predictions (first rows)")
        st.dataframe(out.head())

    # Write to InfluxDB
    if st.button("Write results to InfluxDB"):
        n = write_behaviour_to_influx(
            out, url=INFLUX_URL, org=INFLUX_ORG, bucket=INFLUX_BUCKET, token=INFLUX_TOKEN
        )
        st.success(f"Wrote {n} points to InfluxDB.")
        st.info("Open Grafana and build a panel from measurement **behavior_pred**.")

    # Download labeled CSV
    st.download_button(
        "Download labeled CSV",
        data=out.to_csv(index=False).encode("utf-8"),
        file_name="labeled_output.csv",
        mime="text/csv",
    )

# Set the title of the app
st.title("Welcome App")

# Print welcome message
st.write("👋 Welcome to my Streamlit app!!!!!!!!!!!!!!!")
