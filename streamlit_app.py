import io
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Sales Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data
def make_sample_data(seed: int = 42) -> pd.DataFrame:
    """Generate a realistic-looking sample sales dataset."""
    rng = np.random.default_rng(seed)
    n_days = 540
    start = date.today() - timedelta(days=n_days)
    dates = pd.date_range(start, periods=n_days, freq="D")

    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Clothing", "Home", "Sports", "Books"]

    rows = []
    for d in dates:
        # More orders on weekends, a gentle upward trend over time.
        trend = 1 + (d - dates[0]).days / n_days * 0.6
        weekend = 1.35 if d.weekday() >= 5 else 1.0
        n_orders = rng.poisson(8 * trend * weekend)
        for _ in range(n_orders):
            category = rng.choice(categories)
            base_price = {
                "Electronics": 220,
                "Clothing": 55,
                "Home": 90,
                "Sports": 75,
                "Books": 20,
            }[category]
            units = int(rng.integers(1, 5))
            price = base_price * rng.uniform(0.7, 1.4)
            rows.append(
                {
                    "date": d,
                    "region": rng.choice(regions, p=[0.3, 0.25, 0.25, 0.2]),
                    "category": category,
                    "units": units,
                    "revenue": round(units * price, 2),
                }
            )

    return pd.DataFrame(rows)


@st.cache_data
def load_uploaded(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    # Try to parse a date column automatically.
    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


# --------------------------------------------------------------------------- #
# Sidebar — data source & filters
# --------------------------------------------------------------------------- #
st.sidebar.title("📊 Sales Explorer")
st.sidebar.caption("Interactive dashboard demo")

uploaded = st.sidebar.file_uploader(
    "Upload a CSV",
    type="csv",
    help="Expected columns: date, region, category, units, revenue. "
    "Leave empty to explore the built-in sample data.",
)

if uploaded is not None:
    try:
        df = load_uploaded(uploaded.getvalue())
        st.sidebar.success(f"Loaded {len(df):,} rows from your file.")
    except Exception as exc:  # noqa: BLE001
        st.sidebar.error(f"Could not read file: {exc}")
        st.stop()
else:
    df = make_sample_data()
    st.sidebar.info("Showing built-in sample data. Upload a CSV to use your own.")

# Ensure the expected schema exists for the sample-data experience.
required = {"date", "region", "category", "units", "revenue"}
has_schema = required.issubset(df.columns)

st.sidebar.divider()
st.sidebar.subheader("Filters")

if has_schema:
    df["date"] = pd.to_datetime(df["date"])
    min_d, max_d = df["date"].min().date(), df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        lo, hi = date_range
        df = df[(df["date"].dt.date >= lo) & (df["date"].dt.date <= hi)]

    regions = sorted(df["region"].unique())
    chosen_regions = st.sidebar.multiselect("Regions", regions, default=regions)
    df = df[df["region"].isin(chosen_regions)]

    categories = sorted(df["category"].unique())
    chosen_cats = st.sidebar.multiselect("Categories", categories, default=categories)
    df = df[df["category"].isin(chosen_cats)]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
st.title("Sales Explorer")

if not has_schema:
    st.warning(
        "Your CSV doesn't have the expected columns "
        "(`date`, `region`, `category`, `units`, `revenue`), "
        "so the dashboard below is disabled. Here's a preview of what you uploaded:"
    )
    st.dataframe(df, use_container_width=True)
    st.stop()

if df.empty:
    st.warning("No data matches the current filters. Try widening them.")
    st.stop()

# KPIs -----------------------------------------------------------------------
total_rev = df["revenue"].sum()
total_units = int(df["units"].sum())
n_orders = len(df)
avg_order = total_rev / n_orders if n_orders else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total revenue", f"${total_rev:,.0f}")
c2.metric("Units sold", f"{total_units:,}")
c3.metric("Orders", f"{n_orders:,}")
c4.metric("Avg. order value", f"${avg_order:,.2f}")

st.divider()

# Charts ---------------------------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Revenue over time")
    daily = (
        df.set_index("date")
        .resample("W")["revenue"]
        .sum()
        .rename("Weekly revenue")
    )
    st.line_chart(daily, use_container_width=True)

with right:
    st.subheader("Revenue by category")
    by_cat = (
        df.groupby("category")["revenue"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(by_cat, use_container_width=True)

st.subheader("Revenue by region")
by_region = df.groupby("region")["revenue"].sum().sort_values(ascending=False)
st.bar_chart(by_region, use_container_width=True, horizontal=True)

# Detail table & download ----------------------------------------------------
st.divider()
with st.expander("Show raw data"):
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

st.download_button(
    "⬇️ Download filtered data (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_sales.csv",
    mime="text/csv",
)
