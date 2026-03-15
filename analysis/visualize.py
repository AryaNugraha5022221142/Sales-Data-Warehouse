import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from urllib.parse import quote_plus
from sqlalchemy import create_engine
import os

# ============================================================
# CONFIG
# ============================================================
password = quote_plus("712Amazing")
engine = create_engine(f"postgresql+psycopg2://postgres:{password}@localhost:5432/sales_dw")

OUTPUT_DIR = "analysis/charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

STYLE = "seaborn-v0_8-whitegrid"
plt.style.use(STYLE)
PALETTE = "Blues_d"

# ============================================================
# HELPER
# ============================================================
def save_chart(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ Saved: {path}")

# ============================================================
# DATA LOADING — all queries via SQLAlchemy views
# ============================================================
print("📦 Loading data from warehouse views...")

df_category = pd.read_sql("""
    SELECT p.category, SUM(f.totalsales) AS total_revenue
    FROM warehouse.factsales f
    JOIN warehouse.dimproduct p ON f.productkey = p.productkey
    GROUP BY p.category
    ORDER BY total_revenue DESC
""", engine)

df_monthly = pd.read_sql("""
    SELECT d.year, d.monthofyear, d.monthname,
           SUM(f.totalsales) AS monthly_revenue
    FROM warehouse.factsales f
    JOIN warehouse.dimdate d ON f.datekey = d.datekey
    GROUP BY d.year, d.monthofyear, d.monthname
    ORDER BY d.year, d.monthofyear
""", engine)
df_monthly["period"] = df_monthly["year"].astype(str) + "-" + \
                        df_monthly["monthofyear"].astype(str).str.zfill(2)

df_region = pd.read_sql("""
    SELECT c.region, SUM(f.totalsales) AS total_revenue
    FROM warehouse.factsales f
    JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey
    GROUP BY c.region
    ORDER BY total_revenue DESC
""", engine)

df_mom = pd.read_sql("SELECT * FROM warehouse.vw_mom_revenue", engine)

df_cum = pd.read_sql("SELECT * FROM warehouse.vw_cumulative_revenue", engine)
df_cum["fulldate"] = pd.to_datetime(df_cum["fulldate"])

df_rfm = pd.read_sql("SELECT * FROM warehouse.vw_rfm_segments", engine)

print("✅ All data loaded.\n")

# ============================================================
# CHART 1: Revenue by Category (Bar)
# ============================================================
print("🎨 Generating charts...")

plt.figure(figsize=(9, 5))
sns.barplot(data=df_category, x="category", y="total_revenue", palette=PALETTE)
plt.title("Revenue by Product Category", fontsize=14, fontweight="bold")
plt.xlabel("Category")
plt.ylabel("Total Revenue")
plt.xticks(rotation=30, ha="right")
plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
save_chart("chart_category.png")

# ============================================================
# CHART 2: Monthly Revenue Trend (Line)
# ============================================================
plt.figure(figsize=(14, 5))
plt.plot(df_monthly["period"], df_monthly["monthly_revenue"],
         marker="o", linewidth=2, color="steelblue")
plt.fill_between(df_monthly["period"], df_monthly["monthly_revenue"],
                 alpha=0.1, color="steelblue")
plt.title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
plt.xlabel("Period")
plt.ylabel("Revenue")
plt.xticks(rotation=90)
plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.tight_layout()
save_chart("chart_monthly.png")

# ============================================================
# CHART 3: Sales by Region (Pie)
# ============================================================
plt.figure(figsize=(7, 7))
plt.pie(df_region["total_revenue"], labels=df_region["region"],
        autopct="%1.1f%%", startangle=140,
        colors=sns.color_palette("Blues_d", len(df_region)))
plt.title("Sales Distribution by Region", fontsize=14, fontweight="bold")
save_chart("chart_region.png")

# ============================================================
# CHART 4: Month-over-Month Revenue Growth (Bar + Line combo)
# ============================================================
fig, ax1 = plt.subplots(figsize=(12, 5))

ax1.bar(df_mom["monthname"], df_mom["revenue"],
        color="steelblue", alpha=0.7, label="Revenue")
ax1.set_ylabel("Revenue", color="steelblue")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax1.tick_params(axis="x", rotation=45)

ax2 = ax1.twinx()
ax2.plot(df_mom["monthname"], df_mom["mom_growth_pct"],
         color="red", marker="o", linewidth=2, label="MoM Growth %")
ax2.set_ylabel("MoM Growth %", color="red")
ax2.axhline(0, color="red", linestyle="--", linewidth=0.8, alpha=0.5)

fig.suptitle("Month-over-Month Revenue Growth", fontsize=14, fontweight="bold")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
plt.tight_layout()
save_chart("chart_mom_growth.png")

# ============================================================
# CHART 5: Cumulative Revenue Over Time (Area)
# ============================================================
plt.figure(figsize=(12, 5))
plt.plot(df_cum["fulldate"], df_cum["cumulative_revenue"],
         color="green", linewidth=2)
plt.fill_between(df_cum["fulldate"], df_cum["cumulative_revenue"],
                 alpha=0.15, color="green")
plt.title("Cumulative Revenue Over Time", fontsize=14, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Cumulative Revenue")
plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.tight_layout()
save_chart("chart_cumulative_revenue.png")

# ============================================================
# CHART 6: RFM Segment Distribution (Count bar)
# ============================================================
rfm_counts = df_rfm["rfm_segment"].value_counts().reset_index()
rfm_counts.columns = ["rfm_segment", "customer_count"]
rfm_counts = rfm_counts.sort_values("rfm_segment")

plt.figure(figsize=(12, 5))
sns.barplot(data=rfm_counts, x="rfm_segment", y="customer_count", palette="viridis")
plt.title("Customer Count by RFM Segment", fontsize=14, fontweight="bold")
plt.xlabel("RFM Segment (Recency-Frequency-Monetary)")
plt.ylabel("Number of Customers")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
save_chart("chart_rfm_segments.png")

print("\n🎉 All 6 charts saved to analysis/charts/")
