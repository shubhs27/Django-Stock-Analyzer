import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import os
import glob
from decouple import config

# Database connection parameters - using environment variables
DB_CONFIG = {
    "host": config("DB_HOST", default="localhost"),
    "database": config("DB_NAME"),
    "user": config("DB_USER"),
    "password": config("DB_PASSWORD"),
    "port": config("DB_PORT", default="5432"),
}

# Create connection string
conn_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def check_table_structure():
    """Check if Django tables exist and have the expected structure"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Check if Django tables exist
        cur.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('stocks_company', 'ohlc_data');
        """
        )

        existing_tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        return existing_tables

    except Exception as e:
        print(f"Error checking table structure: {str(e)}")
        return []


def create_table_if_not_exists():
    """Create the OHLC table only if Django migrations haven't been run"""
    existing_tables = check_table_structure()

    if "ohlc_data" in existing_tables:
        print("Django tables detected. Using existing Django table structure.")
        return True

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS ohlc_data (
            id SERIAL PRIMARY KEY,
            company_symbol VARCHAR(10),
            date DATE,
            open DECIMAL(10,2),
            high DECIMAL(10,2),
            low DECIMAL(10,2),
            close DECIMAL(10,2),
            volume BIGINT,
            file_source VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_symbol, date)
        );
        
        CREATE INDEX IF NOT EXISTS idx_company_symbol_date ON ohlc_data(company_symbol, date);
        CREATE INDEX IF NOT EXISTS idx_date ON ohlc_data(date);
        """

        cur.execute(create_table_query)
        conn.commit()
        cur.close()
        conn.close()
        print("Table created successfully!")
        return True

    except Exception as e:
        print(f"Error creating table: {str(e)}")
        return False


def clean_price_column(series):
    """Clean price columns by removing $ symbol"""
    return series.astype(str).str.replace("$", "").astype(float)


def import_csv_files(folder_path):
    """Import all CSV files from the specified folder"""

    try:
        # Create database engine
        engine = create_engine(conn_string)

        # Get all CSV files in the folder
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

        if not csv_files:
            print(f"No CSV files found in {folder_path}")
            return

        print(f"Found {len(csv_files)} CSV files")

        for file_path in csv_files:
            try:
                # Extract filename for tracking
                filename = os.path.basename(file_path)
                print(f"Processing: {filename}")

                # Read CSV file
                df = pd.read_csv(file_path)

                # Standardize column names for your specific CSV format
                column_mapping = {
                    "Date": "date",
                    "Close/Last": "close",
                    "Volume": "volume",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                }

                # Rename columns if they exist
                df = df.rename(
                    columns={k: v for k, v in column_mapping.items() if k in df.columns}
                )

                # Clean up the data for your specific format
                price_columns = ["open", "high", "low", "close"]
                for col in price_columns:
                    if col in df.columns:
                        df[col] = clean_price_column(df[col])

                # Add company symbol if not present
                if "company_symbol" not in df.columns:
                    # Extract company name from filename and map to symbol
                    company_name = filename.split(".")[0]  # Remove .csv extension
                    df["company_symbol"] = company_name.upper()

                # Add file source
                df["file_source"] = filename

                # Convert date column to datetime
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")

                # Add created_at timestamp for Django compatibility
                df["created_at"] = pd.Timestamp.now()

                # Select only the columns we need and ensure they exist
                required_columns = [
                    "company_symbol",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "file_source",
                    "created_at",
                ]
                existing_columns = [
                    col for col in required_columns if col in df.columns
                ]
                df = df[existing_columns]

                # Remove any rows with missing essential data
                df = df.dropna(subset=["date", "close"])

                # Import to PostgreSQL using upsert to handle duplicates
                try:
                    df.to_sql(
                        "ohlc_data",
                        engine,
                        if_exists="append",
                        index=False,
                        method="multi",
                        chunksize=1000,  # Process in smaller chunks
                    )
                    print(f"Successfully imported {len(df)} rows from {filename}")

                except Exception as db_error:
                    print(f"Database error for {filename}: {str(db_error)}")

                    # Try inserting row by row to handle duplicates
                    print(f"Attempting row-by-row insert for {filename}...")
                    success_count = 0
                    duplicate_count = 0

                    for _, row in df.iterrows():
                        try:
                            row_df = pd.DataFrame([row])
                            row_df.to_sql(
                                "ohlc_data", engine, if_exists="append", index=False
                            )
                            success_count += 1
                        except Exception as row_error:
                            if (
                                "duplicate key" in str(row_error).lower()
                                or "unique constraint" in str(row_error).lower()
                            ):
                                duplicate_count += 1
                            else:
                                print(f"Row error: {str(row_error)}")

                    print(
                        f"Row-by-row result: {success_count} inserted, {duplicate_count} duplicates skipped"
                    )

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue

        print("Import process completed!")

    except Exception as e:
        print(f"Error in import process: {str(e)}")


def create_companies_table():
    """Create companies table and populate with unique symbols"""
    existing_tables = check_table_structure()

    if "stocks_company" in existing_tables:
        print("stocks_company table already exists (Django managed)")
        return populate_companies_from_existing_data()

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Create companies table
        create_companies_query = """
        CREATE TABLE IF NOT EXISTS stocks_company (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE,
            symbol VARCHAR(10) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cur.execute(create_companies_query)

        # Insert unique company symbols from ohlc_data
        insert_companies_query = """
        INSERT INTO stocks_company (name, symbol)
        SELECT DISTINCT company_symbol, company_symbol
        FROM ohlc_data
        WHERE company_symbol NOT IN (SELECT symbol FROM stocks_company WHERE symbol IS NOT NULL)
        ON CONFLICT (symbol) DO NOTHING;
        """

        cur.execute(insert_companies_query)
        conn.commit()
        cur.close()
        conn.close()
        print("Companies table created and populated!")
        return True

    except Exception as e:
        print(f"Error creating companies table: {str(e)}")
        return False


def populate_companies_from_existing_data():
    """Populate companies table from existing stock data when Django tables exist"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Insert unique company symbols from ohlc_data into Django managed table
        insert_companies_query = """
        INSERT INTO stocks_company (name, symbol, created_at)
        SELECT DISTINCT company_symbol, company_symbol, CURRENT_TIMESTAMP
        FROM ohlc_data
        WHERE company_symbol NOT IN (SELECT symbol FROM stocks_company WHERE symbol IS NOT NULL)
        ON CONFLICT (symbol) DO NOTHING;
        """

        cur.execute(insert_companies_query)
        conn.commit()

        # Get count of inserted companies
        cur.execute("SELECT COUNT(*) FROM stocks_company;")
        company_count = cur.fetchone()[0]

        cur.close()
        conn.close()
        print(f"Companies table populated! Total companies: {company_count}")
        return True

    except Exception as e:
        print(f"Error populating companies table: {str(e)}")
        return False


def verify_import():
    """Verify the imported data"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Get total count
        cur.execute("SELECT COUNT(*) FROM ohlc_data;")
        total_count = cur.fetchone()[0]
        print(f"Total records imported: {total_count}")

        if total_count == 0:
            print("No data found in ohlc_data table!")
            cur.close()
            conn.close()
            return

        # Get count by company
        cur.execute(
            "SELECT company_symbol, COUNT(*) FROM ohlc_data GROUP BY company_symbol ORDER BY company_symbol;"
        )
        company_counts = cur.fetchall()

        print("\nRecords per company:")
        for company, count in company_counts:
            print(f"  {company}: {count} records")

        # Get date range
        cur.execute("SELECT MIN(date), MAX(date) FROM ohlc_data;")
        date_range = cur.fetchone()
        print(f"\nDate range: {date_range[0]} to {date_range[1]}")

        # Show sample data
        cur.execute("SELECT * FROM ohlc_data ORDER BY date DESC LIMIT 5;")
        sample_data = cur.fetchall()

        print("\nSample data (latest 5 records):")
        for row in sample_data:
            print(f"  {row}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error verifying import: {str(e)}")


def main():
    """Main execution function"""
    FOLDER_PATH = "./StocksData"

    print("Starting CSV import process...")
    print("Checking database structure...")

    existing_tables = check_table_structure()
    if existing_tables:
        print(f"Found existing tables: {existing_tables}")
        print("Using Django-managed table structure.")
    else:
        print("No existing tables found. Creating new tables.")

    # Step 1: Create table (if needed)
    if not create_table_if_not_exists():
        print("Failed to create table. Exiting.")
        return

    # Step 2: Import CSV files
    import_csv_files(FOLDER_PATH)

    # Step 3: Create and populate companies table
    create_companies_table()

    # Step 4: Verify import
    verify_import()

    print("Process completed!")


if __name__ == "__main__":
    main()
