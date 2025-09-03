# app.py — AirFly Insights (simple Streamlit app).
import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="AirFly Insights", layout="wide")
st.title("✈️ AirFly Insights — Delay hotspots & cancellations")
st.markdown("Story: Where delays & cancellations happen most, when, why, and quick recommendations.")

DATA_DIR = "data"  # in repo, include small CSVs in this folder

@st.cache_data
def load_data():
    data = {}
    # aggregated CSVs
    for name in ["route_stats","airport_stats","monthly_stats","carrier_delays"]:
        path = os.path.join(DATA_DIR, f"{name}.csv")
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
    # full optional parquet
    fullp = os.path.join(DATA_DIR, "airline_cleaned.parquet")
    if os.path.exists(fullp):
        data["full"] = pd.read_parquet(fullp)
    return data

data = load_data()

# Sidebar filters
st.sidebar.header("Filters")
month_opts = ["All"]
if "monthly_stats" in data:
    month_opts += sorted(data["monthly_stats"]["Month"].dropna().astype(int).unique().tolist())
month = st.sidebar.selectbox("Month", month_opts)

# KPIs (use full if available)
if "full" in data:
    df = data["full"]
    if month != "All":
        df = df[df["Month"] == int(month)]
    c1,c2,c3 = st.columns(3)
    c1.metric("Total flights", int(df.shape[0]))
    c2.metric("Avg arrival delay (min)", round(df["ArrDelay"].mean(skipna=True),2))
    c3.metric("Cancellation rate", f"{round(df['Cancelled'].mean()*100,2)}%")
else:
    st.info("Aggregated data loaded. For full KPIs add airline_cleaned.parquet in data/")

# Plot 1: Top routes
st.subheader("Top routes (by flights)")
if "route_stats" in data:
    rt = data["route_stats"].nlargest(15, "flights")
else:
    rt = data["full"].groupby("Route").agg(flights=('Route','count'), avg_arr_delay=('ArrDelay','mean')).reset_index().nlargest(15, "flights")
fig = px.bar(rt, x="flights", y=rt.columns[0], orientation="h", labels={"y":"Route","flights":"Flights"})
st.plotly_chart(fig, use_container_width=True)

# Plot 2: Busiest origin airports
st.subheader("Busiest origin airports")
if "airport_stats" in data:
    ap = data["airport_stats"].nlargest(15, "departures")
else:
    ap = data["full"].groupby("Origin").agg(departures=('Origin','count'), avg_arr_delay=('ArrDelay','mean')).reset_index().nlargest(15, "departures")
fig2 = px.bar(ap, x="departures", y=ap.columns[0], orientation="h", labels={"Origin":"Airport","departures":"Departures"})
st.plotly_chart(fig2, use_container_width=True)

# Plot 3: Monthly average arrival delay
st.subheader("Monthly average arrival delay")
if "monthly_stats" in data:
    m = data["monthly_stats"]
else:
    m = data["full"].groupby("Month").agg(avg_arr_delay=('ArrDelay','mean'), cancellations=('Cancelled','sum')).reset_index()
fig3 = px.line(m, x="Month", y="avg_arr_delay", markers=True)
st.plotly_chart(fig3, use_container_width=True)

# Plot 4: Cancellation reasons (if full)
st.subheader("Cancellation reasons")
if "full" in data:
    dfc = data["full"].copy()
    cmap = {'A':'Carrier','B':'Weather','C':'NAS','D':'Security'}
    dfc['CancellationReason'] = dfc['CancellationCode'].map(cmap)
    cancel_counts = dfc[dfc['Cancelled']==1]['CancellationReason'].value_counts().reset_index()
    cancel_counts.columns = ["Reason","Count"]
    fig4 = px.bar(cancel_counts, x="Count", y="Reason", orientation="h")
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Full dataset required to show cancellation reasons (place airline_cleaned.parquet in data/).")

# Plot 5: Delay causes by carrier
st.subheader("Average delay (by cause) — Top carriers")
if "carrier_delays" in data:
    cd = data["carrier_delays"]
else:
    cd = data["full"].groupby("UniqueCarrier")[['CarrierDelay','WeatherDelay','NASDelay','SecurityDelay','LateAircraftDelay']].mean().reset_index()
topc = cd.sort_values("CarrierDelay", ascending=False).head(8).melt(id_vars="UniqueCarrier", var_name="Cause", value_name="Minutes")
fig5 = px.bar(topc, x="UniqueCarrier", y="Minutes", color="Cause", barmode="group")
st.plotly_chart(fig5, use_container_width=True)

st.markdown("### Recommendations")
st.write("- Focus staffing at peak departure hours.  \n- Target top delay-prone carriers for ops improvements.  \n- Prioritize winter-month preparations at high-delay airports.")

st.write("Data source: giovamata/airlinedelaycauses (Kaggle).")
