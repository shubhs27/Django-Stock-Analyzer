import os
import sys
import django
import pandas as pd
import glob
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stock_viewer.settings")
django.setup()

from stocks.models import Company, StockData


def load_stock_data():
    # Path to CSV files
    csv_path = "./StocksData"

    if not os.path.exists(csv_path):
        print(f"Directory {csv_path} does not exist")
        print("Please make sure your CSV files are in the StocksData directory")
        return

    # Find all CSV files
    csv_files = glob.glob(os.path.join(csv_path, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {csv_path}")
        return

    print(f"Found {len(csv_files)} CSV files")

    for file_path in csv_files:
        try:
            # Extract company name from filename
            company_name = os.path.basename(file_path).replace(".csv", "")

            print(f"Processing {company_name}...")

            # Create or get company
            company, created = Company.objects.get_or_create(
                name=company_name, defaults={"symbol": company_name.upper()}
            )

            if created:
                print(f"Created company: {company_name}")
            else:
                # Clear existing data for this company
                deleted_count = StockData.objects.filter(company=company).delete()[0]
                print(f"Cleared {deleted_count} existing records for: {company_name}")

            # Read CSV file
            df = pd.read_csv(file_path)

            print(f"CSV columns: {list(df.columns)}")
            print(f"CSV shape: {df.shape}")
            print(f"First few rows:")
            print(df.head())

            # Clean and process data
            df["Date"] = pd.to_datetime(df["Date"])

            # Clean price columns (remove $ sign)
            price_columns = ["Close/Last", "Open", "High", "Low"]
            for col in price_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace("$", "").astype(float)

            # Sort by date
            df = df.sort_values("Date")

            # Create StockData objects
            stock_data_objects = []
            for _, row in df.iterrows():
                stock_data = StockData(
                    company=company,
                    date=row["Date"].date(),
                    open_price=Decimal(str(row["Open"])),
                    high_price=Decimal(str(row["High"])),
                    low_price=Decimal(str(row["Low"])),
                    close_price=Decimal(str(row["Close/Last"])),
                    volume=(
                        int(row["Volume"])
                        if "Volume" in df.columns and pd.notna(row["Volume"])
                        else 0
                    ),
                )
                stock_data_objects.append(stock_data)

            # Bulk create for better performance
            StockData.objects.bulk_create(stock_data_objects, batch_size=1000)

            print(
                f"✅ Successfully loaded {len(stock_data_objects)} records for {company_name}"
            )

        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            import traceback

            traceback.print_exc()

    total_companies = Company.objects.count()
    total_records = StockData.objects.count()

    print(f"\nData loading complete!")
    print(f"{total_companies} companies loaded!")
    print(f"{total_records} total stock records!!")


if __name__ == "__main__":
    load_stock_data()
