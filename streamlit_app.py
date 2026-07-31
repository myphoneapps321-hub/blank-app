import io
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Data Explorer",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------------------------------- #
# Sample data
# --------------------------------------------------------------------------- #
@st.cache_data
def make_sample_data(rows: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate a reproducible sample sales dataset."""
    rng = np.random.default_rng(seed)
    start = date.today() - timedelta(days=rows)
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Clothing", "Home", "Toys", "Food"]

    df = pd.DataFrame(
        {
            "date": [start + timedelta(days=int(i)) for i in range(rows)],
            "region": rng.choice(regions, size=rows),
            "category": rng.choice(categories, size=rows),
            "units": rng.integers(1, 50, size=rows),
            "price": np.round(rng.uniform(5, 200, size=rows), 2),
        }
    )
    df["revenue"] = np.round(df["units"] * df["price"], 2)
    return df


@st.cache_data
def load_uploaded(data: bytes) -> pd.DataFrame:
    """Parse an uploaded CSV, coercing obvious date columns."""
    df = pd.read_csv(io.BytesIO(data))
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                converted = pd.to_datetime(df[col], errors="raise")
                df[col] = converted
            except (ValueError, TypeError):
                pass
    return df


# --------------------------------------------------------------------------- #
# Sidebar — data source
# --------------------------------------------------------------------------- #
st.sidebar.title("📊 Data Explorer")
st.sidebar.caption("Upload a CSV or explore the built-in sample dataset.")

uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")

if uploaded is not None:
    df = load_uploaded(uploaded.getvalue())
    source = f"`{uploaded.name}`"
else:
    df = make_sample_data()
    source = "built-in sample sales data"

st.title("📊 Interactive Data Explorer")
st.write(f"Exploring {source} — **{len(df):,}** rows, **{df.shape[1]}** columns.")

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
datetime_cols = df.select_dtypes(include="datetime").columns.tolist()


# --------------------------------------------------------------------------- #
# Sidebar — filters
# --------------------------------------------------------------------------- #
st.sidebar.header("Filters")
filtered = df.copy()

for col in categorical_cols:
    options = sorted(df[col].dropna().unique().tolist())
    if 1 < len(options) <= 50:
        chosen = st.sidebar.multiselect(col, options, default=options)
        filtered = filtered[filtered[col].isin(chosen)]

for col in datetime_cols:
    col_min, col_max = df[col].min(), df[col].max()
    if pd.notna(col_min) and pd.notna(col_max) and col_min != col_max:
        start, end = st.sidebar.slider(
            col,
            min_value=col_min.to_pydatetime(),
            max_value=col_max.to_pydatetime(),
            value=(col_min.to_pydatetime(), col_max.to_pydatetime()),
        )
        filtered = filtered[(filtered[col] >= start) & (filtered[col] <= end)]

if filtered.empty:
    st.warning("No rows match the current filters. Widen your selection.")
    st.stop()


# --------------------------------------------------------------------------- #
# Key metrics
# --------------------------------------------------------------------------- #
if numeric_cols:
    st.subheader("Key metrics")
    metric_col = st.selectbox("Metric column", numeric_cols)
    c1, c2, c3, c4 = st.columns(4)
    series = filtered[metric_col]
    c1.metric("Total", f"{series.sum():,.2f}")
    c2.metric("Average", f"{series.mean():,.2f}")
    c3.metric("Max", f"{series.max():,.2f}")
    c4.metric("Rows", f"{len(filtered):,}")


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
tab_trend, tab_break, tab_table = st.tabs(["📈 Trend", "📊 Breakdown", "🔎 Data"])

with tab_trend:
    if datetime_cols and numeric_cols:
        date_col = st.selectbox("Date axis", datetime_cols, key="trend_date")
        value_col = st.selectbox("Value", numeric_cols, key="trend_value")
        trend = (
            filtered.set_index(date_col)[value_col]
            .resample("W")
            .sum()
            .rename("value")
        )
        st.line_chart(trend)
    else:
        st.info("Need a date column and a numeric column to draw a trend.")

with tab_break:
    if categorical_cols and numeric_cols:
        group_col = st.selectbox("Group by", categorical_cols, key="break_group")
        value_col = st.selectbox("Value", numeric_cols, key="break_value")
        agg = (
            filtered.groupby(group_col)[value_col]
            .sum()
            .sort_values(ascending=False)
        )
        st.bar_chart(agg)
    else:
        st.info("Need a categorical column and a numeric column for a breakdown.")

with tab_table:
    st.dataframe(filtered, use_container_width=True)
    st.download_button(
        "⬇️ Download filtered CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_data.csv",
        mime="text/csv",
    )
    with st.expander("Summary statistics"):
        st.dataframe(filtered.describe(include="all"), use_container_width=True)
