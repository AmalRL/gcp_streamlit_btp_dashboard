import os
import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import storage
import certifi
import datetime

# -----------------------------
# SSL FIX
# -----------------------------
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# -----------------------------
# CONFIG
# -----------------------------
BUCKET_NAME = "btpss-dashboard-data"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:/Users/Amal/Downloads/btpssdashboard-25c58d6c57a3.json"

# -----------------------------
# GCP CLIENT
# -----------------------------
@st.cache_resource
def get_client():
    return storage.Client()

client = get_client()

# -----------------------------
# LOAD CSV FROM GCP
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
# LOAD DATA BASED ON SELECTION
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
st.subheader(":pushpin: Onboarding, WAU & Power Users")

if not metrics_df.empty:
    row = metrics_df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Users", int(row["total_users"]))
    col2.metric("Onboarded Users", int(row["onboarding_users"]))
    col3.metric("% Onboarding", f"{row['onboarding_percentage']}%")
    col4.metric("Avg Weeks Active", f"{row['avg_weeks_active']} weeks")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Age ≤ 36 Months", int(row["age_36_users"]))
    col6.metric("WAU (Last Week)", int(row["wau_users"]))
    col7.metric("% WAU", f"{row['wau_percentage']}%")
    col8.metric("Power Users", int(row["power_users"]))

    col9, col10 = st.columns(2)
    col9.metric("Power Users %", f"{row['power_user_percentage']}%")

# -----------------------------
# INTERVENTION SECTION
# -----------------------------
st.subheader(":package: Intervention Delivery Rate")

today = datetime.date.today()
last_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7 + 7)

selected_sunday = st.date_input(
    "Select Week Start (Sunday only)",
    value=last_sunday
)

if selected_sunday.weekday() != 6:
    st.warning("⚠️ Please select a Sunday")
    st.stop()

st.write(f"Selected Week: {selected_sunday}")

# -----------------------------
# FILTER USING week_start
# -----------------------------
intervention_df["week_start"] = pd.to_datetime(intervention_df["week_start"])

df2 = intervention_df[
    intervention_df["week_start"] == pd.to_datetime(selected_sunday)
]

# -----------------------------
# DISPLAY
# -----------------------------
if not df2.empty:

    st.dataframe(df2)

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

st.caption("Source: Google Cloud Storage (CSV files)")
