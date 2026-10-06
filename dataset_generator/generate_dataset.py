import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

NUM_ROWS = 250_000
OUTPUT_FILE = Path("data/messy_retail_data_250K.csv")

random.seed(42)


# ============================================================
# Master Data
# ============================================================

FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Arjun",
    "Riya", "Ankit", "Neha", "Rohan", "Pooja"
]

LAST_NAMES = [
    "Sharma", "Das", "Dutta", "Roy", "Sen",
    "Gupta", "Banerjee", "Ghosh", "Saha", "Paul"
]

CITIES = [
    "Kolkata", "Delhi", "Mumbai", "Bangalore",
    "Chennai", "Hyderabad", "Pune", "Ahmedabad"
]

CATEGORIES = [
    "Electronics", "Clothing", "Groceries",
    "Furniture", "Books", "Sports"
]

PRODUCTS = {
    "Electronics": [
        "Laptop", "Smartphone", "Headphones", "Tablet"
    ],
    "Clothing": [
        "T-Shirt", "Jeans", "Jacket", "Shoes"
    ],
    "Groceries": [
        "Rice", "Milk", "Bread", "Cooking Oil"
    ],
    "Furniture": [
        "Chair", "Table", "Sofa", "Bed"
    ],
    "Books": [
        "Python Programming", "Data Science",
        "Machine Learning", "Database Systems"
    ],
    "Sports": [
        "Football", "Cricket Bat", "Tennis Racket", "Basketball"
    ]
}

PAYMENT_METHODS = [
    "Cash", "Credit Card", "Debit Card",
    "UPI", "Net Banking"
]

ORDER_STATUSES = [
    "Completed", "Pending", "Cancelled", "Returned"
]


# ============================================================
# Helper Functions
# ============================================================

def random_date():
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)

    days = (end_date - start_date).days

    return start_date + timedelta(
        days=random.randint(0, days)
    )


def random_customer_name():
    return (
        random.choice(FIRST_NAMES)
        + " "
        + random.choice(LAST_NAMES)
    )


# ============================================================
# Generate Dataset
# ============================================================

def generate_dataset():

    rows = []

    headers = [
        "Order_ID",
        "Customer_Name",
        "Customer_Email",
        "City",
        "Category",
        "Product",
        "Quantity",
        "Unit_Price",
        "Discount",
        "Total_Amount",
        "Order_Date",
        "Payment_Method",
        "Order_Status",
        "Customer_Age",
        "Customer_Rating"
    ]

    # --------------------------------------------------------
    # Generate clean base records + 45% dirty records
    # --------------------------------------------------------

    for i in range(1, NUM_ROWS + 1):

        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        customer_name = f"{first_name} {last_name}"

        customer_email = (
            f"{first_name.lower()}."
            f"{last_name.lower()}@example.com"
        )

        city = random.choice(CITIES)
        category = random.choice(CATEGORIES)
        product = random.choice(PRODUCTS[category])

        quantity = random.randint(1, 10)

        unit_price = round(
            random.uniform(100, 50_000), 2
        )

        discount = round(
            random.uniform(0, 30), 2
        )

        total_amount = round(
            quantity * unit_price * (1 - discount / 100),
            2
        )

        order_date = random_date().strftime("%Y-%m-%d")

        payment_method = random.choice(PAYMENT_METHODS)
        order_status = random.choice(ORDER_STATUSES)

        customer_age = random.randint(18, 70)

        customer_rating = random.randint(1, 5)

        row = [
            f"ORD-{i:05d}",
            customer_name,
            customer_email,
            city,
            category,
            product,
            quantity,
            unit_price,
            discount,
            total_amount,
            order_date,
            payment_method,
            order_status,
            customer_age,
            customer_rating
        ]

        # ----------------------------------------------------
        # Introduce 45% dirty records
        # ----------------------------------------------------

        if random.random() < 0.45:

            issue_type = random.choice([
                "mixed_payment_case",
                "mixed_product_case",
                "mixed_status_case",
                "email_domain_case",
                "misspelled_email_domain",
                "special_characters_name",
                "absurd_age",
                "negative_rating",
                "messy_date"
            ])

            if issue_type == "mixed_payment_case":

                row[11] = random.choice([
                    row[11].upper(),
                    row[11].lower(),
                    row[11].title()
                ])

            elif issue_type == "mixed_product_case":

                row[5] = random.choice([
                    row[5].upper(),
                    row[5].lower(),
                    row[5].title()
                ])

            elif issue_type == "mixed_status_case":

                row[12] = random.choice([
                    row[12].upper(),
                    row[12].lower(),
                    row[12].title()
                ])

            elif issue_type == "email_domain_case":

                row[2] = row[2].replace(
                    "@example.com",
                    "@ExAmPlE.cOm"
                )

            elif issue_type == "misspelled_email_domain":

                row[2] = row[2].replace(
                    "@example.com",
                    "@exampl.com"
                )

            elif issue_type == "special_characters_name":

                row[1] = (
                    row[1].split()[0]
                    + "@"
                    + row[1].split()[1]
                    + "#"
                )

            elif issue_type == "absurd_age":

                row[13] = random.choice([
                    452,
                    "4@6",
                    "_37",
                    "2 8",
                    999,
                    -25,
                    "abc"
                ])

            elif issue_type == "negative_rating":

                row[14] = random.choice([
                    -1, -2, -3, -4, -5
                ])

            elif issue_type == "messy_date":

                row[10] = random.choice([
                    "15/03/2025",
                    "03-15-2025",
                    "2025-03-15",
                    "March 15 2025",
                    " 15/03/2025 ",
                    "31/02/2025",
                    "2025-13-45",
                    "15/XX/2025",
                    ""
                ])

        rows.append(row)

    # ========================================================
    # DAMAGE LAYER 1
    # Blank Cells: 5% - 6% of data cells
    # ========================================================

    data_cell_count = NUM_ROWS * (len(headers) - 1)

    blank_percentage = random.uniform(0.05, 0.06)

    blank_cell_count = int(
        data_cell_count * blank_percentage
    )

    possible_blank_positions = []

    for row_index in range(NUM_ROWS):
        for column_index in range(1, len(headers)):
            possible_blank_positions.append(
                (row_index, column_index)
            )

    random.shuffle(possible_blank_positions)

    for row_index, column_index in possible_blank_positions[
        :blank_cell_count
    ]:
        rows[row_index][column_index] = ""

    # ========================================================
    # DAMAGE LAYER 2
    # Missing-value text: 7% - 8% of data cells
    # ========================================================

    missing_percentage = random.uniform(0.07, 0.08)

    missing_cell_count = int(
        data_cell_count * missing_percentage
    )

    possible_missing_positions = []

    for row_index in range(NUM_ROWS):
        for column_index in range(1, len(headers)):

            # Don't overwrite an existing blank cell
            if rows[row_index][column_index] != "":
                possible_missing_positions.append(
                    (row_index, column_index)
                )

    random.shuffle(possible_missing_positions)

    missing_values = [
        "NA",
        "None",
        "null",
        "INVALID",
    ]

    for row_index, column_index in possible_missing_positions[
        :missing_cell_count
    ]:
        rows[row_index][column_index] = random.choice(
            missing_values
        )

    # ========================================================
    # DAMAGE LAYER 3
    # Duplicated Rows: 10% - 15%
    # ========================================================

    duplicate_percentage = random.uniform(0.10, 0.15)

    duplicate_count = int(
        NUM_ROWS * duplicate_percentage
    )

    # Select existing rows to duplicate
    duplicate_source_rows = random.sample(
        rows,
        duplicate_count
    )

    # Remove the same number of rows from the end
    # so the final dataset remains exactly 10,000 rows.
    rows = rows[:-duplicate_count]

    # Add duplicated records
    rows.extend(duplicate_source_rows)

    # ========================================================
    # Shuffle final dataset
    # ========================================================

    random.shuffle(rows)

    # ========================================================
    # Write CSV
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(headers)
        writer.writerows(rows)

    # ========================================================
    # Summary
    # ========================================================

    print(
        f"Dataset generated successfully: {OUTPUT_FILE}"
    )

    print(
        f"Total rows generated: {len(rows)}"
    )

    print(
        f"Blank cells introduced: {blank_cell_count}"
    )

    print(
        f"Missing-value cells introduced: {missing_cell_count}"
    )

    print(
        f"Duplicated rows introduced: {duplicate_count}"
    )


# ============================================================
# Run Generator
# ============================================================

if __name__ == "__main__":
    generate_dataset()
