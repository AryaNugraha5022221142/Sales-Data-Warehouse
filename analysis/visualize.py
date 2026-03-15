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

CHARTS_DIR = "analysis/charts"
OUTPUT_DIR = "output"
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def save_chart(filename):
    path = os.path.join(CHARTS_DIR, filename)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ Saved: {path}")

def currency_formatter(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)

# ============================================================
# DATA LOADING
# ============================================================
print("📦 Loading data from warehouse...\n")

df_category = pd.read_sql("""
    SELECT p.category,
           SUM(f.totalsales)    AS total_revenue,
           COUNT(f.saleskey)    AS total_orders
    FROM warehouse.factsales f
    JOIN warehouse.dimproduct p ON f.productkey = p.productkey
    GROUP BY p.category
    ORDER BY total_revenue DESC
""", engine)
df_category["total_revenue"] = df_category["total_revenue"].fillna(0).astype(float)
df_category["total_orders"]  = df_category["total_orders"].fillna(0).astype(float)

df_monthly = pd.read_sql("""
    SELECT d.year, d.monthofyear, d.monthname,
           SUM(f.totalsales) AS monthly_revenue
    FROM warehouse.factsales f
    JOIN warehouse.dimdate d ON f.datekey = d.datekey
    GROUP BY d.year, d.monthofyear, d.monthname
    ORDER BY d.year, d.monthofyear
""", engine)
df_monthly["monthly_revenue"] = df_monthly["monthly_revenue"].fillna(0).astype(float)
df_monthly["period"] = df_monthly["year"].astype(str) + "-" + \
                       df_monthly["monthofyear"].astype(str).str.zfill(2)

df_region = pd.read_sql("""
    SELECT c.region, SUM(f.totalsales) AS total_revenue
    FROM warehouse.factsales f
    JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey
    GROUP BY c.region
    ORDER BY total_revenue DESC
""", engine)
df_region["total_revenue"] = df_region["total_revenue"].fillna(0).astype(float)

df_mom = pd.read_sql("SELECT * FROM warehouse.vw_mom_revenue", engine)
df_mom["revenue"]        = df_mom["revenue"].fillna(0).astype(float)
df_mom["mom_growth_pct"] = df_mom["mom_growth_pct"].fillna(0).astype(float)

df_cum = pd.read_sql("SELECT * FROM warehouse.vw_cumulative_revenue", engine)
df_cum["fulldate"]            = pd.to_datetime(df_cum["fulldate"])
df_cum["daily_revenue"]       = df_cum["daily_revenue"].fillna(0).astype(float)
df_cum["cumulative_revenue"]  = df_cum["cumulative_revenue"].fillna(0).astype(float)

df_rfm = pd.read_sql("SELECT * FROM warehouse.vw_rfm_segments", engine)
df_rfm["r_score"] = df_rfm["r_score"].fillna(1).astype(int)
df_rfm["f_score"] = df_rfm["f_score"].fillna(1).astype(int)
df_rfm["m_score"] = df_rfm["m_score"].fillna(1).astype(int)

print("✅ All data loaded.\n")

# ============================================================
# CHART 1: Revenue & Profit by Category (Grouped Bar)
# ============================================================

fig, ax = plt.subplots(figsize=(9, 5))
colors = sns.color_palette("Blues_d", len(df_category))
bars = ax.bar(
    df_category["category"].tolist(),
    df_category["total_revenue"].tolist(),
    color=colors, edgecolor="white", linewidth=0.8
)
ax.set_title("Revenue & Order Count by Product Category", fontsize=14, fontweight="bold")
ax.set_ylabel("Total Revenue (USD)")
currency_formatter(ax)

for bar, orders in zip(bars, df_category["total_orders"].tolist()):
    h = bar.get_height()
    # Revenue label on top
    ax.annotate(f"${h:,.0f}",
                (bar.get_x() + bar.get_width() / 2, h),
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    # Order count label inside bar
    ax.annotate(f"{int(orders):,} orders",
                (bar.get_x() + bar.get_width() / 2, h * 0.5),
                ha="center", va="center", fontsize=9,
                color="white", fontweight="bold")

plt.tight_layout()
save_chart("chart_category.png")

# ============================================================
# CHART 2: Monthly Revenue Trend (Line + Area)
# ============================================================
fig, ax = plt.subplots(figsize=(14, 5))
periods  = df_monthly["period"].tolist()
revenues = df_monthly["monthly_revenue"].tolist()
ax.plot(periods, revenues, marker="o", linewidth=2,
        color="steelblue", markersize=4)
ax.fill_between(periods, revenues, alpha=0.15, color="steelblue")
ax.set_title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
ax.set_xlabel("Period")
ax.set_ylabel("Revenue (USD)")
currency_formatter(ax)
plt.xticks(rotation=90, fontsize=7)
plt.tight_layout()
save_chart("chart_monthly.png")

# ============================================================
# CHART 3: Sales by Region (Horizontal Bar)
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
colors  = sns.color_palette("Blues_d", len(df_region))
regions  = df_region["region"].tolist()
revenues = df_region["total_revenue"].tolist()
bars = ax.barh(regions, revenues, color=colors, edgecolor="white")
ax.set_title("Total Sales by Region", fontsize=14, fontweight="bold")
ax.set_xlabel("Total Revenue (USD)")
currency_formatter(ax, axis="x")
ax.invert_yaxis()
for bar in bars:
    w = bar.get_width()
    ax.annotate(f"  ${w:,.0f}",
                (w, bar.get_y() + bar.get_height() / 2),
                va="center", fontsize=9, fontweight="bold")
plt.tight_layout()
save_chart("chart_region.png")

# ============================================================
# CHART 4: MoM Revenue Growth (Aggregated Dual-Axis)
# ============================================================
MONTH_ORDER = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

# Fix aggregation — use median for growth % to resist outliers
df_mom_agg = df_mom.groupby(
    ["monthofyear", "monthname"], as_index=False
).agg(
    revenue=("revenue", "mean"),           # mean is fine for revenue
    mom_growth_pct=("mom_growth_pct", "median")  # median resists the spike
).sort_values("monthofyear")

df_mom_agg["monthname"] = pd.Categorical(
    df_mom_agg["monthname"], categories=MONTH_ORDER, ordered=True
)
df_mom_agg = df_mom_agg.sort_values("monthname").reset_index(drop=True)

months      = df_mom_agg["monthname"].tolist()
rev_vals    = df_mom_agg["revenue"].tolist()
growth_vals = df_mom_agg["mom_growth_pct"].tolist()

fig, ax1 = plt.subplots(figsize=(13, 5))
ax1.bar(months, rev_vals, color="steelblue", alpha=0.75, label="Avg Monthly Revenue")
ax1.set_ylabel("Avg Revenue (USD)", color="steelblue", fontsize=10)
ax1.tick_params(axis="y", labelcolor="steelblue")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.xticks(rotation=30, ha="right")

ax2 = ax1.twinx()
ax2.plot(months, growth_vals, color="red", marker="o",
         linewidth=2, label="Median MoM Growth %")
ax2.axhline(0, color="red", linestyle="--", linewidth=0.8, alpha=0.4)
ax2.set_ylabel("Median MoM Growth %", color="red", fontsize=10)
ax2.tick_params(axis="y", labelcolor="red")
ax2.set_ylim(-30, 300)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
fig.suptitle("Month-over-Month Revenue Growth (Median Across All Years)",
             fontsize=14, fontweight="bold")
plt.tight_layout()
save_chart("chart_mom_growth.png")

# ============================================================
# CHART 5: Cumulative Revenue Over Time (Area)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 5))
dates   = df_cum["fulldate"].tolist()
cum_rev = df_cum["cumulative_revenue"].tolist()
ax.plot(dates, cum_rev, color="#1a7a4a", linewidth=2.5)
ax.fill_between(dates, cum_rev, alpha=0.15, color="#2ecc71")
ax.set_title("Cumulative Revenue Over Time", fontsize=14, fontweight="bold")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Revenue (USD)")
currency_formatter(ax)
plt.tight_layout()
save_chart("chart_cumulative_revenue.png")

# ============================================================
# CHART 6: RFM Customer Segmentation (Named Groups)
# ============================================================
def rfm_label(row):
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 3 and f >= 3 and m >= 3:
        return "Champions"
    elif r >= 3 and f >= 2:
        return "Loyal Customers"
    elif r >= 3 and f <= 2:
        return "Potential Loyalists"
    elif r <= 2 and f >= 3:
        return "At Risk"
    else:
        return "Lost / Inactive"

df_rfm["segment_label"] = df_rfm.apply(rfm_label, axis=1)
rfm_grouped = df_rfm["segment_label"].value_counts().reset_index()
rfm_grouped.columns = ["segment", "customer_count"]

SEGMENT_ORDER  = ["Champions", "Loyal Customers", "Potential Loyalists",
                  "At Risk", "Lost / Inactive"]
SEGMENT_COLORS = ["#2ecc71", "#3498db", "#f39c12", "#e74c3c", "#95a5a6"]

rfm_grouped["segment"] = pd.Categorical(
    rfm_grouped["segment"], categories=SEGMENT_ORDER, ordered=True
)
rfm_grouped = rfm_grouped.sort_values("segment").reset_index(drop=True)

fig, ax = plt.subplots(figsize=(10, 5))
seg_names   = rfm_grouped["segment"].tolist()
seg_counts  = rfm_grouped["customer_count"].tolist()
bars = ax.bar(seg_names, seg_counts,
              color=SEGMENT_COLORS[:len(seg_names)],
              edgecolor="white", linewidth=0.8)
ax.set_title("Customer Segmentation by RFM Score", fontsize=14, fontweight="bold")
ax.set_xlabel("Segment")
ax.set_ylabel("Number of Customers")
for bar in bars:
    h = int(bar.get_height())
    ax.annotate(str(h),
                (bar.get_x() + bar.get_width() / 2, h + 0.5),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
plt.tight_layout()
save_chart("chart_rfm_segments.png")

# ============================================================
# EXPORT CSVs
# ============================================================
print("\n📤 Exporting CSVs...")
df_category.to_csv(f"{OUTPUT_DIR}/report_revenue_by_category.csv", index=False)
df_monthly.to_csv(f"{OUTPUT_DIR}/report_monthly_trend.csv",        index=False)
df_region.to_csv(f"{OUTPUT_DIR}/report_by_region.csv",             index=False)
df_mom.to_csv(f"{OUTPUT_DIR}/report_mom_revenue.csv",              index=False)
df_cum.to_csv(f"{OUTPUT_DIR}/report_cumulative_revenue.csv",       index=False)
df_rfm.to_csv(f"{OUTPUT_DIR}/report_rfm_segments.csv",             index=False)
print("✅ All CSVs saved to output/")
print("\n🎉 Done — 6 charts and 6 CSVs generated.")
