# Sales Data Warehouse

An end-to-end data warehousing project built with PostgreSQL and Python.

## Stack
- PostgreSQL 18 + pgAdmin 4
- Python (pandas, SQLAlchemy)
- Star Schema design

## Structure
- `etl.py` — Extract, Transform, Load pipeline
- `queries.sql` — Reporting queries
- `report_*.csv` — Exported query results

## Schema
- **FactSales** — Core sales transactions
- **DimProduct** — Product dimension
- **DimCustomer** — Customer dimension
- **DimDate** — Date dimension
