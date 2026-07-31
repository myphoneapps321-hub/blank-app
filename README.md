# 📊 Sales Explorer

An interactive Streamlit dashboard for exploring sales data. It ships with a
realistic built-in sample dataset, and you can upload your own CSV to explore
it instead.

## Features

- **KPI cards** — total revenue, units sold, order count, average order value
- **Interactive filters** — date range, region, and category (in the sidebar)
- **Charts** — weekly revenue trend, revenue by category, revenue by region
- **CSV upload** — bring your own data with columns
  `date, region, category, units, revenue`
- **Download** — export the filtered data back out as CSV

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
