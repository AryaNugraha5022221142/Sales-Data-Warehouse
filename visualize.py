import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from urllib.parse import quote_plus
from sqlalchemy import create_engine

password = quote_plus("712Amazing")
engine = create_engine(f"postgresql+psycopg2://postgres:{password}@localhost:5432/sales_dw")

# --- Chart 1: Revenue by Category ---
df1 = pd.read_sql("SELECT p.category, SUM(f.totalsales) AS total_revenue FROM warehouse.factsales f JOIN warehouse.dimproduct p ON f.productkey = p.productkey GROUP BY p.category ORDER BY total_revenue DESC", engine)

plt.figure(figsize=(8,5))
sns.barplot(data=df1, x="category", y="total_revenue", palette="Blues_d")
plt.title("Revenue by Category")
plt.savefig("chart_category.png")
plt.show()

# --- Chart 2: Monthly Trend ---
df2 = pd.read_sql("SELECT d.year, d.monthofyear, SUM(f.totalsales) AS monthly_revenue FROM warehouse.factsales f JOIN warehouse.dimdate d ON f.datekey = d.datekey GROUP BY d.year, d.monthofyear ORDER BY d.year, d.monthofyear", engine)
df2["period"] = df2["year"].astype(str) + "-" + df2["monthofyear"].astype(str).str.zfill(2)

plt.figure(figsize=(14,5))
plt.plot(df2["period"], df2["monthly_revenue"], marker="o")
plt.xticks(rotation=90)
plt.title("Monthly Sales Trend")
plt.tight_layout()
plt.savefig("chart_monthly.png")
plt.show()

# --- Chart 3: Sales by Region ---
df3 = pd.read_sql("SELECT c.region, SUM(f.totalsales) AS total_revenue FROM warehouse.factsales f JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey GROUP BY c.region ORDER BY total_revenue DESC", engine)

plt.figure(figsize=(7,7))
plt.pie(df3["total_revenue"], labels=df3["region"], autopct="%1.1f%%", startangle=140)
plt.title("Sales by Region")
plt.savefig("chart_region.png")
plt.show()

print("✅ All charts saved!")
