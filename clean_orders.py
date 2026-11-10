import os
import pandas as pd

BASE_DIR = os.getcwd()
ORDERS_FILE = os.path.join(BASE_DIR, "orders_large.csv")
CUSTOMERS_FILE = os.path.join(BASE_DIR, "customers_large.csv")
ORDER_ITEMS_FILE = os.path.join(BASE_DIR, "order_items_large.csv")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products_large.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "orders_cleaned.csv")


def calculate_tax(orders, customers):
    """
    Calculate tax based on order's tax and sales amount, and customer's city
    """
    orders = orders.copy()
    customers = customers[["customer_id", "city"]].copy()

    orders["customer_id"] = orders["customer_id"].astype("string").str.strip()
    customers["customer_id"] = customers["customer_id"].astype("string").str.strip()
    orders[["sales_amount", "tax_amount"]] = orders[
        ["sales_amount", "tax_amount"]
    ].apply(pd.to_numeric, errors="coerce").fillna(0)

    joined = orders.merge(customers, on="customer_id", how="left")
    joined["city"] = joined["city"].fillna("(unmatched customer)")
    totals = joined.groupby("city")[["sales_amount", "tax_amount"]].sum()

    return (totals["tax_amount"] / totals["sales_amount"]).where(
        totals["sales_amount"] != 0, 0
    ).to_dict()




def read_inputs():
    orders = pd.read_csv(ORDERS_FILE, dtype={"order_id": "string", "customer_id": "string"})
    customers = pd.read_csv(CUSTOMERS_FILE, dtype={"customer_id": "string"})
    items = pd.read_csv(
        ORDER_ITEMS_FILE,
        dtype={"order_id": "string", "product_id": "string"},
    )
    products = pd.read_csv(PRODUCTS_FILE, dtype={"product_id": "string"})
    return orders, customers, items, products


def clean_orders():
    # read data
    orders, customers, items, products = read_inputs()
    city_tax_rates = calculate_tax(orders, customers)
    order_columns = orders.columns.tolist()
    original_count = len(orders)

    # Default shipping date to be the same date as the order date.
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["ship_date"] = pd.to_datetime(orders["ship_date"])

    early_ship = orders["ship_date"] < orders["order_date"]
    orders.loc[early_ship, "ship_date"] = orders.loc[early_ship, "order_date"]


    # For all negative sales amount, summing up each order item’s quantity * unit price
    # if product id is not found, their sales were recalculated using the known item prices
    # treating missing prices as 0.
    products["unit_price"] = pd.to_numeric(products["unit_price"])
    items["quantity"] = pd.to_numeric(items["quantity"])
    orders["sales_amount"] = pd.to_numeric(orders["sales_amount"])

    product_prices = products.set_index("product_id")["unit_price"]
    items["line_total"] = items["quantity"] * items["product_id"].map(product_prices)
    item_totals = items.groupby("order_id")["line_total"].sum()

    negative_sales = orders["sales_amount"] < 0
    orders.loc[negative_sales, "sales_amount"] = (
        orders.loc[negative_sales, "order_id"].map(item_totals).fillna(0).round(2)
    )

    # fix negative tax amount

    city_tax_rates = calculate_tax(orders, customers)

    city_lookup = (
        customers.drop_duplicates("customer_id", keep="last")
        .set_index("customer_id")["city"]
    )
    orders["city"] = orders["customer_id"].map(city_lookup)

    orders["sales_amount"] = pd.to_numeric(orders["sales_amount"])
    orders["tax_amount"] = pd.to_numeric(orders["tax_amount"])
    rates = orders["city"].map(city_tax_rates)
    fix = (orders["tax_amount"] < 0) & rates.notna()

    orders.loc[fix, "tax_amount"] = (orders.loc[fix, "sales_amount"] * rates[fix]).round(2)
    orders = orders.drop(columns="city")

    # delete all the rows where customer id is not found in customer's table.
    customer_ids = customers["customer_id"]
    orders["customer_id"] = orders["customer_id"]

    orders = orders[orders["customer_id"].isin(customer_ids)].copy()

    orders.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    clean_orders()
