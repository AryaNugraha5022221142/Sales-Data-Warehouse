import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# --- CONNECTION ---
password = quote_plus("712Amazing")
engine = create_engine(f"postgresql+psycopg2://postgres:{password}@localhost:5432/sales_dw")

# --- CLEAR TABLES ---
with engine.connect() as conn:
    conn.execute(text("TRUNCATE warehouse.FactSales CASCADE"))
    conn.execute(text("TRUNCATE warehouse.DimDate CASCADE"))
    conn.execute(text("TRUNCATE warehouse.DimCustomer CASCADE"))
    conn.execute(text("TRUNCATE warehouse.DimProduct CASCADE"))
    conn.commit()
print("✅ Tables cleared")

# --- EXTRACT ---
df = pd.read_csv("train.csv")
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True)
print("✅ Extracted:", len(df), "rows")

# --- TRANSFORM & LOAD: DimDate ---
dates = df[["order_date"]].drop_duplicates().copy()
dates["datekey"]     = dates["order_date"].dt.strftime("%Y%m%d").astype(int)
dates["fulldate"]    = dates["order_date"]
dates["year"]        = dates["order_date"].dt.year
dates["quarter"]     = dates["order_date"].dt.quarter
dates["monthofyear"] = dates["order_date"].dt.month
dates["monthname"]   = dates["order_date"].dt.strftime("%B")
dates["dayofweek"]   = dates["order_date"].dt.strftime("%A")
dates["isweekend"]   = dates["order_date"].dt.dayofweek >= 5
dates = dates.drop(columns=["order_date"])
dates.to_sql("dimdate", engine, schema="warehouse", if_exists="append", index=False)
print("✅ DimDate loaded:", len(dates), "rows")

# --- TRANSFORM & LOAD: DimCustomer ---
customers = df[["customer_id","customer_name","segment","region","state","city"]].drop_duplicates("customer_id").copy()
customers.columns = ["customerid","customername","segment","region","state","city"]
customers.to_sql("dimcustomer", engine, schema="warehouse", if_exists="append", index=False)
print("✅ DimCustomer loaded:", len(customers), "rows")

# --- TRANSFORM & LOAD: DimProduct ---
products = df[["product_id","product_name","category","sub_category"]].drop_duplicates("product_id").copy()
products.columns = ["productid","productname","category","subcategory"]
products.to_sql("dimproduct", engine, schema="warehouse", if_exists="append", index=False)
print("✅ DimProduct loaded:", len(products), "rows")

# --- TRANSFORM & LOAD: FactSales ---
dim_date     = pd.read_sql("SELECT datekey, fulldate FROM warehouse.dimdate", engine)
dim_customer = pd.read_sql("SELECT customerkey, customerid FROM warehouse.dimcustomer", engine)
dim_product  = pd.read_sql("SELECT productkey, productid FROM warehouse.dimproduct", engine)

dim_date["fulldate"] = pd.to_datetime(dim_date["fulldate"])

fact = df.copy()
fact["fulldate"] = fact["order_date"]

fact = fact.merge(dim_date,     on="fulldate",                                how="left")
fact = fact.merge(dim_customer, left_on="customer_id", right_on="customerid", how="left")
fact = fact.merge(dim_product,  left_on="product_id",  right_on="productid",  how="left")

fact_final = fact[["datekey","customerkey","productkey","order_id","sales"]].copy()
fact_final.columns = ["datekey","customerkey","productkey","orderid","totalsales"]
fact_final["quantitysold"] = None
fact_final["unitprice"]    = None
fact_final["discount"]     = None
fact_final["totalprofit"]  = None

fact_final.to_sql("factsales", engine, schema="warehouse", if_exists="append", index=False)
print("✅ FactSales loaded:", len(fact_final), "rows")
print("\n🎉 ETL Complete!")

# --- EXPORT REPORTS TO CSV ---
reports = {
    "report_revenue_by_category": "SELECT p.category, SUM(f.totalsales) AS total_revenue, COUNT(f.orderid) AS total_orders FROM warehouse.factsales f JOIN warehouse.dimproduct p ON f.productkey = p.productkey GROUP BY p.category ORDER BY total_revenue DESC",
    "report_monthly_trend":       "SELECT d.year, d.monthname, d.monthofyear, SUM(f.totalsales) AS monthly_revenue FROM warehouse.factsales f JOIN warehouse.dimdate d ON f.datekey = d.datekey GROUP BY d.year, d.monthname, d.monthofyear ORDER BY d.year, d.monthofyear",
    "report_top_customers":       "SELECT c.customername, c.segment, c.region, SUM(f.totalsales) AS total_spent FROM warehouse.factsales f JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey GROUP BY c.customername, c.segment, c.region ORDER BY total_spent DESC LIMIT 10",
    "report_by_region":           "SELECT c.region, SUM(f.totalsales) AS total_revenue, COUNT(f.orderid) AS total_orders FROM warehouse.factsales f JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey GROUP BY c.region ORDER BY total_revenue DESC",
    "report_top_products":        "SELECT p.productname, p.category, p.subcategory, SUM(f.totalsales) AS total_revenue FROM warehouse.factsales f JOIN warehouse.dimproduct p ON f.productkey = p.productkey GROUP BY p.productname, p.category, p.subcategory ORDER BY total_revenue DESC LIMIT 10",
}

for filename, query in reports.items():
    pd.read_sql(query, engine).to_csv(f"{filename}.csv", index=False)
    print(f"✅ Exported {filename}.csv")

print("\n🎉 All reports exported!")
