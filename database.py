"""
PostgreSQL database helper functions
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# PostgreSQL connection parameters
DB_CONFIG = {
    'dbname': 'hotel_webapp',
    'user': 'postgres',
    'password': '456456dekel',  # Change this
    'host': 'localhost',
    'port': 5432
}


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def get_all_hotels(limit=100):
    """Get all hotels with optional limit"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hotels LIMIT %s", (limit,))
        return cursor.fetchall()


def search_hotels(query, limit=50):
    """Search hotels by name or location"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Adjust column names based on your actual CSV structure
        sql = """
            SELECT * FROM hotels 
            WHERE "name" ILIKE %s OR "city" ILIKE %s OR "country" ILIKE %s
            LIMIT %s
        """
        search_term = f"%{query}%"
        cursor.execute(sql, (search_term, search_term, search_term, limit))
        return cursor.fetchall()


def get_hotel_by_id(hotel_id):
    """Get a specific hotel by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hotels WHERE id = %s", (hotel_id,))
        return cursor.fetchone()


def get_hotels_by_city(city, limit=50):
    """Get hotels in a specific city"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM hotels WHERE "city" = %s LIMIT %s', (city, limit))
        return cursor.fetchall()


def get_table_info():
    """Get information about the hotels table structure"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'hotels'
            ORDER BY ordinal_position
        """)
        return cursor.fetchall()


def get_stats():
    """Get database statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM hotels")
        return cursor.fetchone()


def get_filtered_hotels(filters=None):
    """Get hotels with advanced filtering"""
    if filters is None:
        filters = {}

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build WHERE clause based on filters
        where_conditions = []
        params = []

        # City filter
        if filters.get('city'):
            where_conditions.append('"city" = %s')
            params.append(filters['city'])

        # Review score filter - try to cast, skip invalid
        if filters.get('review_min') is not None:
            where_conditions.append('''review_score IS NOT NULL
                                       AND review_score != ''
                                       AND review_score ~ '^[0-9]'
                                       AND CAST(review_score AS NUMERIC) >= %s''')
            params.append(filters['review_min'])

        if filters.get('review_max') is not None:
            where_conditions.append('''review_score IS NOT NULL
                                       AND review_score != ''
                                       AND review_score ~ '^[0-9]'
                                       AND CAST(review_score AS NUMERIC) <= %s''')
            params.append(filters['review_max'])

        # Minimum number of reviews filter
        if filters.get('min_reviews') is not None:
            where_conditions.append('''number_of_reviews IS NOT NULL
                                       AND number_of_reviews != ''
                                       AND number_of_reviews ~ '^[0-9]'
                                       AND CAST(CAST(number_of_reviews AS NUMERIC) AS INTEGER) >= %s''')
            params.append(filters['min_reviews'])

        # Gap score categories filter
        if filters.get('gap_categories'):
            placeholders = ','.join(['%s'] * len(filters['gap_categories']))
            where_conditions.append(f'gap_category IN ({placeholders})')
            params.extend(filters['gap_categories'])

        # Distance filter - simplified
        if filters.get('max_distance') is not None:
            where_conditions.append('''distance_from_center_km IS NOT NULL
                                       AND distance_from_center_km != ''
                                       AND distance_from_center_km ~ '^[0-9]'
                                       AND CAST(distance_from_center_km AS NUMERIC) <= %s''')
            params.append(filters['max_distance'])

        # Amenities filter (requires at least one of the selected amenities)
        if filters.get('amenities'):
            amenity_conditions = []
            for amenity in filters['amenities']:
                amenity_conditions.append(f"{amenity} = '1'")  # Compare as text
            if amenity_conditions:
                where_conditions.append(f"({' OR '.join(amenity_conditions)})")

        # Build the query with all necessary fields
        query = """SELECT hotel_id, city, title, lat, lon, review_score,
                   predicted_reality_score, gap_score, gap_category,
                   number_of_reviews, distance_from_center_km,
                   has_wifi, has_parking, has_pool, has_gym,
                   has_breakfast, has_ac, main_complaints, main_praises,
                   risk_level, amenities_count, url
                   FROM hotels"""

        # Always filter out hotels without valid coordinates - simplified check
        base_conditions = [
            "lat IS NOT NULL",
            "lon IS NOT NULL",
            "lat != ''",
            "lon != ''",
            # Only check if they can be cast to numeric and are in valid range
            "lat ~ '^-?[0-9]'",  # Starts with optional minus and digit
            "lon ~ '^-?[0-9]'"   # Starts with optional minus and digit
        ]

        if where_conditions:
            query += " WHERE " + " AND ".join(base_conditions + where_conditions)
        else:
            query += " WHERE " + " AND ".join(base_conditions)

        query += " ORDER BY review_score DESC"

        # No default limit - only add if explicitly requested
        if filters.get('limit'):
            query += " LIMIT %s"
            params.append(filters['limit'])

        cursor.execute(query, params)
        return cursor.fetchall()


def get_cities():
    """Get list of unique valid cities"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get all cities with at least 10 hotels, excluding obvious bad data
        cursor.execute("""
            SELECT DISTINCT city, COUNT(*) as count
            FROM hotels
            WHERE city IS NOT NULL
            AND city != ''
            AND LENGTH(city) >= 3  -- Cities should have at least 3 characters
            AND LENGTH(city) < 50
            AND city NOT LIKE '%|||%'
            AND city NOT LIKE '%.%'
            AND city NOT LIKE '%,%'
            AND city NOT LIKE '%!%'
            AND city ~ '^[A-Za-z]'  -- Cities should start with a letter
            AND city !~ '^[0-9]+$'  -- Exclude purely numeric entries
            GROUP BY city
            HAVING COUNT(*) >= 10
            ORDER BY COUNT(*) DESC, city
        """)
        return [row['city'] for row in cursor.fetchall() if row['city']]


def get_hotel_markers_data():
    """Get minimal hotel data for map markers"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hotel_id, city, title, lat, lon, review_score,
                   predicted_reality_score, gap_score, gap_category,
                   number_of_reviews, distance_from_center_km,
                   has_wifi, has_parking, has_pool, has_gym,
                   has_breakfast, has_ac, main_complaints, main_praises,
                   risk_level, amenities_count, url
            FROM hotels
            WHERE lat IS NOT NULL AND lon IS NOT NULL
            AND lat != '' AND lon != ''
            AND lat ~ '^-?[0-9]'  -- Starts with optional minus and digit
            AND lon ~ '^-?[0-9]'  -- Starts with optional minus and digit
        """)
        return cursor.fetchall()
