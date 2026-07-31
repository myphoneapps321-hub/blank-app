# 📊 Interactive Data Explorer

A self-contained Streamlit app for exploring tabular data. It ships with a
built-in sample sales dataset so it works out of the box, and also accepts your
own CSV uploads.

## Features

- **Upload any CSV** or explore the generated sample data
- **Automatic filters** — dynamic multiselects for categorical columns and
  range sliders for date columns
- **Key metrics** — total, average, max, and row count for any numeric column
- **Trend chart** — weekly time-series of any numeric column
- **Breakdown chart** — grouped totals by any categorical column
- **Data table** with summary statistics and a filtered-CSV download

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
