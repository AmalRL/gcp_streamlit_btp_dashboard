import os
import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import storage
from google.oauth2 import service_account
import certifi
import datetime
import json

# -----------------------------
# SSL FIX
# -----------------------------
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# -----------------------------
# CONFIG
# -----------------------------
BUCKET_NAME = "btpss-dashboard-data"

# -----------------------------
# GCP CLIENT (ENV JSON)
# -----------------------------
@st.cache_resource
def get_client():
    gcp_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if not gcp_json:
        raise ValueError("❌ GCP_SERVICE_ACCOUNT_JSON not set")

    credentials_dict = json.loads(gcp_json)

    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict
    )

    return storage.Client(credentials=credentials)

client = get_client()

# -----------------------------
# LOAD CSV
# -----------------------------
@st.cache_data(ttl=600)
def load_csv_from_gcp(file_name):
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)
    data = blob.download_as_bytes()
    return pd.read_csv(pd.io.common.BytesIO(data))

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Analytics Dashboard", layout="wide")

page = st.sidebar.selectbox(
    "Select Dashboard",
    ["BTP Analytics", "SS Analytics"]
)

# -----------------------------
# LOAD DATA
# -----------------------------
if page == "BTP Analytics":
    st.title("📊 BTP Analytics Dashboard")
    metrics_df = load_csv_from_gcp("btp_metrics.csv")
    intervention_df = load_csv_from_gcp("btp_interventions_4weeks.csv")
else:
    st.title("📊 SS Analytics Dashboard")
    metrics_df = load_csv_from_gcp("ss_metrics.csv")
    intervention_df = load_csv_from_gcp("ss_interventions_4weeks.csv")

# -----------------------------
# MAIN METRICS
# -----------------------------
st.subheader("📌 Key Metrics")

if not metrics_df.empty:
    row = metrics_df.iloc[0]

    # Build dynamic metric list
    metrics = [
        ("Total Users", "total_users"),
        ("Onboarded Users", "onboarding_users"),
        ("% Onboarding", "onboarding_percentage", "%"),
        ("Avg Weeks Active", "avg_weeks_active", " weeks"),
        ("Age ≤ 36 Months", "age_36_users"),
        ("WAU (Last Week)", "wau_users"),
        ("% WAU", "wau_percentage", "%"),
        ("Power Users", "power_users"),
        ("Power Users %", "power_user_percentage", "%"),
        ("Activated Users", "activated_users"),
        ("Activated %", "activated_percentage", "%"),
    ]

    # Filter only existing metrics
    available_metrics = [
        m for m in metrics if m[1] in row
    ]

    # Display in rows of 4
    for i in range(0, len(available_metrics), 4):
        cols = st.columns(4)
        chunk = available_metrics[i:i+4]

        for col, metric in zip(cols, chunk):
            label = metric[0]
            key = metric[1]
            suffix = metric[2] if len(metric) > 2 else ""

            value = row.get(key, 0)

            # Format %
            if suffix == "%":
                display_value = f"{value}%"
            elif suffix == " weeks":
                display_value = f"{value} weeks"
            else:
                display_value = int(value)

            col.metric(label, display_value)

# -----------------------------
# INTERVENTION SECTION
# -----------------------------
st.subheader("📦 Intervention Delivery Rate")

today = datetime.date.today()

# last completed Sunday
last_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7 + 7)

selected_sunday = st.date_input(
    "Select Week Start (Sunday only)",
    value=last_sunday
)

# enforce Sunday
if selected_sunday.weekday() != 6:
    st.warning("⚠️ Please select a Sunday")
    st.stop()

st.write(f"Selected Week: {selected_sunday}")

# -----------------------------
# FILTER DATA
# -----------------------------
if not intervention_df.empty:

    intervention_df["week_start"] = pd.to_datetime(intervention_df["week_start"])

    df2 = intervention_df[
        intervention_df["week_start"] == pd.to_datetime(selected_sunday)
    ]

    # -----------------------------
    # DISPLAY
    # -----------------------------
    if not df2.empty:

        st.dataframe(df2, use_container_width=True)

        fig = px.bar(
            df2,
            x="campaign_type",
            y="delivery_percentage",
            text="delivery_percentage",
            title="Delivery % by Campaign Type"
        )

        fig.update_traces(textposition="outside")

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No intervention data for selected week")

else:
    st.warning("Intervention dataset is empty")

# -----------------------------
# FOOTER
# -----------------------------
st.caption("Source: Google Cloud Storage (CSV files)")
