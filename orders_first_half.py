# This file handles missing data, normalize/standardize data, and handle
# duplicates and outliers. The process is done over the first half of the
# orders dataset.
#
# For phase 2 of CSCI521 project
#
# Author: Logan Usilton

import numpy as np
import pandas as pd

orders = pd.read_csv("data/orders_large_half_1.csv")
customers = pd.read_csv("data/customers_large.csv")
items = pd.read_csv("data/order_items_large.csv")
products = pd.read_csv("data/products_large.csv")
print(orders.describe(include="all"))

# Calculate sales amount - get product price based on items w/ same order id
for i in range(len(items)):
    o = items.loc[i, "order_id"]
    if o >= len(orders):
        continue
    if orders.loc[orders["order_id"] == o, "sales_amount"].values[0] >= 0:
        continue
    p = items.loc[i, "product_id"]
    if p >= len(products):
        continue
    amt = products.loc[products["product_id"] == p, "unit_price"].values[0]
    amt *= items.loc[i, "quantity"]
    orders.loc[orders["order_id"] == o, "sales_amount"] += amt

for i in range(len(orders)):
    if orders.loc[i, "sales_amount"] < 0:
        orders.loc[i, "sales_amount"] = 0

# Calculate tax amount - city tax percentage * sales_amount
tax = {"Syracuse": 0.081, "Buffalo": 0.0812, "Rochester": 0.0814, "Albany": 0.0811, "Ithaca": 0.0812}

for i in range(len(orders)):
    if orders.loc[i, "tax_amount"] >= 0:
        continue
    orders.loc[i, "tax_amount"] = 0
    c = orders.loc[i, "customer_id"]
    if c >= len(customers):
        orders.drop(i, inplace=True)
        continue
    city = customers.loc[c, "city"]
    orders.loc[i, "tax_amount"] = orders.loc[i, "sales_amount"] * tax[city]

# Address missing/incorrect values
for i in range(len(orders)):
    # Orders need an order date
    if pd.isna(orders.iloc[i, 2]):
        # Set order date to ship date
        orders.iloc[i, 2] = orders.iloc[i, 3]
    # Ship date must come after order date
    if orders.iloc[i, 2] > orders.iloc[i, 3]:
        # If ship date before order date, make ship date same as order date
        orders.iloc[i, 3] = orders.iloc[i, 2]

# Drop any order whose customer_id does not exist in customer database
for c_id in orders["customer_id"]:
    if c_id not in customers["customer_id"]:
        orders = orders[orders["customer_id"] != c_id]

# Remove any duplicates (outside of order_id)
orders.drop_duplicates(subset=["customer_id", "order_date", "ship_date", "sales_amount", "tax_amount", "discount"])

# Normalization - convert dates into datetime format
pd.to_datetime(orders.loc[:, "order_date"])
pd.to_datetime(orders.loc[:, "ship_date"])

print(orders.head(15))

orders.to_csv("data/orders_clean_half_1.csv")