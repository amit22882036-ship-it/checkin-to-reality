from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import (get_stats, get_filtered_hotels, get_cities,
                      get_hotel_markers_data, get_all_hotels, search_hotels,
                      calculate_location_badges, calculate_neighborhood_score)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


# Routes for hotels 


@app.route('/api/hotels')
def api_hotels():
    """API endpoint to get hotels as JSON"""
    limit = request.args.get('limit', 100, type=int)
    hotels = get_all_hotels(limit=limit)
    return jsonify([dict(hotel) for hotel in hotels])


@app.route('/api/search')
def api_search():
    """API endpoint to search hotels"""
    query = request.args.get('q', '')
    if query:
        results = search_hotels(query)
        return jsonify([dict(hotel) for hotel in results])
    return jsonify([])


@app.route('/api/stats')
def api_stats():
    """API endpoint to get database stats"""
    stats = get_stats()
    return jsonify(dict(stats))


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/analysis')
def analysis():
    """Complaint and Praise Analysis Dashboard"""
    return render_template('analysis.html')



@app.route('/dashboard')
def dashboard_enhanced():
    """Enhanced hotel dashboard with improved UI and more filters"""
    return render_template('dashboard_enhanced.html')


@app.route('/hotels')
def hotels():
    """Hotels list page with Booking.com-style layout"""
    return render_template('hotels.html')


@app.route('/api/hotels/filtered', methods=['POST'])
def api_filtered_hotels():
    """API endpoint to get filtered hotels"""
    try:
        filters = request.json or {}

        # Parse filters from request
        parsed_filters = {}

        if filters.get('city'):
            parsed_filters['city'] = filters['city']

        if filters.get('review_min') is not None:
            parsed_filters['review_min'] = float(filters['review_min'])

        if filters.get('review_max') is not None:
            parsed_filters['review_max'] = float(filters['review_max'])

        if filters.get('gap_categories'):
            parsed_filters['gap_categories'] = filters['gap_categories']

        if filters.get('max_distance') is not None:
            parsed_filters['max_distance'] = float(filters['max_distance'])

        if filters.get('min_reviews') is not None:
            parsed_filters['min_reviews'] = int(filters['min_reviews'])

        if filters.get('amenities'):
            parsed_filters['amenities'] = filters['amenities']

        # Only add limit if explicitly requested
        if filters.get('limit'):
            parsed_filters['limit'] = filters['limit']

        hotels = get_filtered_hotels(parsed_filters)
        # Add location badges and neighborhood scores
        enriched_hotels = []
        for hotel in hotels:
            hotel_dict = dict(hotel)
            hotel_dict['location_badges'] = calculate_location_badges(hotel_dict)
            hotel_dict['neighborhood_score'] = calculate_neighborhood_score(hotel_dict)
            enriched_hotels.append(hotel_dict)
        return jsonify(enriched_hotels)

    except Exception as e:
        print(f"Error in api_filtered_hotels: {e}")
        print(f"Filters received: {filters}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/hotels/markers')
def api_hotel_markers():
    """API endpoint to get hotel data for map markers"""
    hotels = get_hotel_markers_data()
    # Add location badges and neighborhood scores
    enriched_hotels = []
    for hotel in hotels:
        hotel_dict = dict(hotel)
        hotel_dict['location_badges'] = calculate_location_badges(hotel_dict)
        hotel_dict['neighborhood_score'] = calculate_neighborhood_score(hotel_dict)
        enriched_hotels.append(hotel_dict)
    return jsonify(enriched_hotels)


@app.route('/api/cities')
def api_cities():
    """API endpoint to get list of cities"""
    cities = get_cities()
    return jsonify(cities)


if __name__ == '__main__':
    app.run(debug=True)
