# app.py — AirFly Insights (with Kaggle API auto-download).
import streamlit as st
import pandas as pd
import os
import plotly.express as px
import zipfile
from kaggle.api.kaggle_api_extended import KaggleApi

# Set Kaggle credentials from Streamlit secrets
os.environ["KAGGLE_USERNAME"] = st.secrets["KAGGLE_USERNAME"]
os.environ["KAGGLE_KEY"] = st.secrets["KAGGLE_KEY"]

st.set_page_config(page_title="AirFly Insights", layout="wide")
st.title("✈️ AirFly Insights — Delay hotspots & cancellations")
st.markdown("Story: Where delays & cancellations happen most, when, why, and quick recommendations.")

# -----------------------
# 1. Kaggle Dataset Setup
# -----------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Download dataset
zip_path = os.path.join(DATA_DIR, "airlinedelaycauses.zip")

from kaggle.api.kaggle_api_extended import KaggleApi

if not os.path.exists(csv_path):
    st.info("📥 Downloading dataset from Kaggle (first time may take ~1 min)...")

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files("giovamata/airlinedelaycauses", path=DATA_DIR, unzip=True)

# Extract dataset if not already extracted
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(DATA_DIR)

# Find the CSV file dynamically
csv_file = None
for f in os.listdir(DATA_DIR):
    if f.endswith(".csv"):
        csv_file = os.path.join(DATA_DIR, f)
        break

if csv_file is None:
    st.error("❌ CSV file not found after extraction!")
else:
    st.success(f"✅ Found dataset: {csv_file}")
    df = pd.read_csv(csv_file, low_memory=False)

# -----------------------
# 2. Load & preprocess data
# -----------------------
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, nrows=50000)

    # Feature engineering
    df['Route'] = df['Origin'].astype(str) + "-" + df['Dest'].astype(str)
    df['DepHour'] = pd.to_numeric(df['DepTime'].fillna(0)).astype(int) // 100
    for c in ['ArrDelay','DepDelay','CarrierDelay','WeatherDelay','NASDelay','SecurityDelay','LateAircraftDelay']:
        if c in df.columns:
            df[c] = df[c].fillna(0)
    return df

df = load_data(csv_file)

# -----------------------
# 3. Sidebar filters
# -----------------------
st.sidebar.header("Filters")
month_opts = ["All"] + sorted(df["Month"].dropna().astype(int).unique().tolist())
month = st.sidebar.selectbox("Month", month_opts)

# Apply filter
if month != "All":
    df = df[df["Month"] == int(month)]

# -----------------------
# 4. KPIs
# -----------------------
c1,c2,c3 = st.columns(3)
c1.metric("Total flights", int(df.shape[0]))
c2.metric("Avg arrival delay (min)", round(df["ArrDelay"].mean(skipna=True),2))
c3.metric("Cancellation rate", f"{round(df['Cancelled'].mean()*100,2)}%")

# -----------------------
# 5. Plots
# -----------------------

# Plot 1: Top routes
st.subheader("Top routes (by flights)")
rt = df.groupby("Route").agg(flights=('Route','count'), avg_arr_delay=('ArrDelay','mean')).reset_index().nlargest(15, "flights")
fig = px.bar(rt, x="flights", y="Route", orientation="h", labels={"flights":"Flights"})
st.plotly_chart(fig, use_container_width=True)

# Plot 2: Busiest origin airports
st.subheader("Busiest origin airports")
ap = df.groupby("Origin").agg(departures=('Origin','count'), avg_arr_delay=('ArrDelay','mean')).reset_index().nlargest(15, "departures")
fig2 = px.bar(ap, x="departures", y="Origin", orientation="h", labels={"Origin":"Airport","departures":"Departures"})
st.plotly_chart(fig2, use_container_width=True)

# Plot 3: Monthly average arrival delay
st.subheader("Monthly average arrival delay")
m = df.groupby("Month").agg(avg_arr_delay=('ArrDelay','mean'), cancellations=('Cancelled','sum')).reset_index()
fig3 = px.line(m, x="Month", y="avg_arr_delay", markers=True)
st.plotly_chart(fig3, use_container_width=True)

# Plot 4: Cancellation reasons
st.subheader("Cancellation reasons")
cmap = {'A':'Carrier','B':'Weather','C':'NAS','D':'Security'}
df['CancellationReason'] = df['CancellationCode'].map(cmap)
cancel_counts = df[df['Cancelled']==1]['CancellationReason'].value_counts().reset_index()
cancel_counts.columns = ["Reason","Count"]
fig4 = px.bar(cancel_counts, x="Count", y="Reason", orientation="h")
st.plotly_chart(fig4, use_container_width=True)

# Plot 5: Delay causes by carrier
st.subheader("Average delay (by cause) — Top carriers")
cd = df.groupby("UniqueCarrier")[['CarrierDelay','WeatherDelay','NASDelay','SecurityDelay','LateAircraftDelay']].mean().reset_index()
topc = cd.sort_values("CarrierDelay", ascending=False).head(8).melt(id_vars="UniqueCarrier", var_name="Cause", value_name="Minutes")
fig5 = px.bar(topc, x="UniqueCarrier", y="Minutes", color="Cause", barmode="group")
st.plotly_chart(fig5, use_container_width=True)

# -----------------------
# 6. Recommendations
# -----------------------
st.markdown("### Recommendations")
st.write("- Focus staffing at peak departure hours.  \n- Target top delay-prone carriers for ops improvements.  \n- Prioritize winter-month preparations at high-delay airports.")

st.write("Data source: [giovamata/airlinedelaycauses](https://www.kaggle.com/datasets/giovamata/airlinedelaycauses)")
