"""
PostgreSQL database initialization script
Loads hotel data from CSV into PostgreSQL database
"""
import psycopg2
from psycopg2 import sql
import csv
import os

# Get the database URL from environment (Render), or use local as fallback
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:456456dekel@localhost:5432/hotel_webapp'
)

CSV_PATH = 'data/hotels.csv'


def init_database():
    """Initialize the database and load data from CSV"""

    # Connect to PostgreSQL using the URL string
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    # Drop table if exists
    cursor.execute("DROP TABLE IF EXISTS hotels CASCADE")
    print("Dropped existing hotels table (if it existed)")

    # Read first line of CSV to get column names
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"Found {len(headers)} columns: {headers}")

    # Create table dynamically based on CSV headers
    # Using TEXT type for all columns for simplicity
    columns = ', '.join([f'"{header}" TEXT' for header in headers])
    create_table_sql = f"""
        CREATE TABLE hotels (
            id SERIAL PRIMARY KEY,
            {columns}
        )
    """

    cursor.execute(create_table_sql)
    print("Created hotels table")

    # Load data from CSV
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row_count = 0

        for row in reader:
            placeholders = ', '.join(['%s' for _ in headers])
            # סידרנו את השורה הבעייתית לכאן:
            formatted_headers = ', '.join([f'"{h}"' for h in headers])
            insert_sql = f"INSERT INTO hotels ({formatted_headers}) VALUES ({placeholders})"

            cursor.execute(insert_sql, [row[h] for h in headers])
            row_count += 1

            if row_count % 1000 == 0:
                print(f"Loaded {row_count} rows...")
                conn.commit()

    conn.commit()
    print(f"Successfully loaded {row_count} rows into database")

    # Create indexes for common search columns
    print("\nCreating indexes...")
    try:
        cursor.execute('CREATE INDEX idx_hotels_name ON hotels USING gin(to_tsvector(\'english\', "name"))')
        print("Created index on name column")
    except:
        pass

    # Show sample data
    cursor.execute("SELECT * FROM hotels LIMIT 5")
    print("\nSample data:")
    for row in cursor.fetchall():
        print(row)

    # Show table info
    cursor.execute("""
        SELECT COUNT(*) as total_rows 
        FROM hotels
    """)
    total = cursor.fetchone()[0]
    print(f"\nTotal rows in database: {total}")

    cursor.close()
    conn.close()
    print(f"\nDatabase initialized successfully!")


if __name__ == '__main__':
    init_database()