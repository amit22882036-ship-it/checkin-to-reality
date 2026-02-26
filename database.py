"""
PostgreSQL database helper functions
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Get the database URL from environment (Render), or use local as fallback
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:456456dekel@localhost:5432/hotel_webapp'
)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    # Connect using the URL string
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
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
                   risk_level, amenities_count, url,
                   metro_railway_access, nightlife_count_500m,
                   high_rated_restaurants_500m, parks_500m,
                   noise_sources_500m, nearest_transport_m,
                   restaurants_500m, avg_restaurant_rating_500m,
                   has_spa, has_kitchen, has_balcony, has_restaurant,
                   has_pet_friendly, has_elevator,
                   complaint_noise, complaint_cleanliness,
                   complaint_location, complaint_amenities,
                   complaint_host, complaint_value,
                   praise_quiet, praise_clean, praise_location,
                   praise_amenities, praise_host, praise_value
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
                   risk_level, amenities_count, url,
                   metro_railway_access, nightlife_count_500m,
                   high_rated_restaurants_500m, parks_500m,
                   noise_sources_500m, nearest_transport_m,
                   restaurants_500m, avg_restaurant_rating_500m
            FROM hotels
            WHERE lat IS NOT NULL AND lon IS NOT NULL
            AND lat != '' AND lon != ''
            AND lat ~ '^-?[0-9]'  -- Starts with optional minus and digit
            AND lon ~ '^-?[0-9]'  -- Starts with optional minus and digit
        """)
        return cursor.fetchall()


def calculate_location_badges(hotel):
    """Calculate location-based badges for a hotel"""
    badges = []

    try:
        # Metro Connected badge
        if hotel.get('metro_railway_access') == '1':
            badges.append({
                'icon': 'fa-train-subway',
                'text': 'Metro Connected',
                'color': 'primary',
                'description': 'Direct metro/railway access'
            })

        # Foodie Paradise badge
        high_rated = float(hotel.get('high_rated_restaurants_500m', 0) or 0)
        if high_rated > 10:
            badges.append({
                'icon': 'fa-utensils',
                'text': 'Foodie Paradise',
                'color': 'warning',
                'description': f'{int(high_rated)} top-rated restaurants nearby'
            })

        # Nightlife Hub badge
        nightlife = float(hotel.get('nightlife_count_500m', 0) or 0)
        if nightlife > 5:
            badges.append({
                'icon': 'fa-cocktail',
                'text': 'Nightlife Hub',
                'color': 'info',
                'description': f'{int(nightlife)} nightlife spots nearby'
            })

        # Green & Quiet badge
        parks = float(hotel.get('parks_500m', 0) or 0)
        noise = float(hotel.get('noise_sources_500m', 0) or 0)
        if parks > 0 and noise < 2:
            badges.append({
                'icon': 'fa-tree',
                'text': 'Green & Quiet',
                'color': 'success',
                'description': 'Parks nearby, low noise levels'
            })

        # Walking Distance badge
        transport = float(hotel.get('nearest_transport_m', 9999) or 9999)
        if transport < 200:
            badges.append({
                'icon': 'fa-walking',
                'text': 'Walk Everywhere',
                'color': 'secondary',
                'description': f'Transport {int(transport)}m away'
            })

        # Central Location badge
        distance = float(hotel.get('distance_from_center_km', 999) or 999)
        if distance < 1:
            badges.append({
                'icon': 'fa-map-pin',
                'text': 'City Center',
                'color': 'danger',
                'description': f'Only {distance}km from center'
            })

    except (ValueError, TypeError):
        pass  # Skip badges if data is invalid

    return badges


def calculate_neighborhood_score(hotel):
    """Calculate overall neighborhood quality score (0-10)"""
    score = 5.0  # Base score

    try:
        # Positive factors
        if hotel.get('metro_railway_access') == '1':
            score += 1.0

        restaurants = float(hotel.get('restaurants_500m', 0) or 0)
        score += min(restaurants / 20, 1.0)  # Max 1 point for 20+ restaurants

        high_rated = float(hotel.get('high_rated_restaurants_500m', 0) or 0)
        score += min(high_rated / 10, 1.0)  # Max 1 point for 10+ high-rated

        parks = float(hotel.get('parks_500m', 0) or 0)
        score += min(parks / 3, 0.5)  # Max 0.5 points for 3+ parks

        transport = float(hotel.get('nearest_transport_m', 9999) or 9999)
        if transport < 500:
            score += (500 - transport) / 500  # Up to 1 point for proximity

        # Negative factors
        noise = float(hotel.get('noise_sources_500m', 0) or 0)
        score -= min(noise / 5, 1.5)  # Lose up to 1.5 points for 5+ noise sources

        # Nightlife can be positive or negative depending on context
        nightlife = float(hotel.get('nightlife_count_500m', 0) or 0)
        if nightlife > 10:
            score -= 0.5  # Too much nightlife might mean noise
        elif nightlife > 0:
            score += 0.3  # Some nightlife is good for vibrancy

    except (ValueError, TypeError):
        return 5.0  # Return neutral score if calculation fails

    # Clamp between 0 and 10
    return max(0, min(10, round(score, 1)))