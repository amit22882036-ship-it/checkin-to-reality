// Global variables
let map;
let markersLayer;
let hotelsData = [];
let cities = [];
let filteredHotels = [];

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    loadCities();
    loadInitialHotels();
    setupEventListeners();
});

// Initialize the Leaflet map with custom styling
function initializeMap() {
    // Create map centered on Europe with custom options
    map = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([41.9028, 12.4964], 6);

    // Add styled map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors, © CARTO',
        maxZoom: 19
    }).addTo(map);

    // Position zoom control
    map.zoomControl.setPosition('topright');

    // Initialize marker cluster group with custom options
    markersLayer = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 60,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: function(cluster) {
            const childCount = cluster.getChildCount();
            let c = ' marker-cluster-';
            if (childCount < 10) {
                c += 'small';
            } else if (childCount < 100) {
                c += 'medium';
            } else {
                c += 'large';
            }

            return new L.DivIcon({
                html: `<div><span>${childCount}</span></div>`,
                className: 'marker-cluster' + c,
                iconSize: new L.Point(40, 40)
            });
        }
    });

    map.addLayer(markersLayer);
}

// Load list of cities for the filter dropdown
async function loadCities() {
    try {
        const response = await fetch('/api/cities');
        cities = await response.json();

        // Populate city filter dropdown
        const citySelect = document.getElementById('city-filter');
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading cities:', error);
    }
}

// Load initial hotels data
async function loadInitialHotels() {
    showLoading(true);
    try {
        const response = await fetch('/api/hotels/markers');

        if (!response.ok) {
            console.error('Failed to load hotels:', response.status);
            showNotification('Failed to load hotel data. Please refresh the page.', 'error');
            showLoading(false);
            return;
        }

        hotelsData = await response.json();

        if (!Array.isArray(hotelsData)) {
            console.error('Invalid hotel data format:', hotelsData);
            showNotification('Received invalid hotel data', 'error');
            showLoading(false);
            return;
        }

        console.log(`Loaded ${hotelsData.length} hotels initially`);
        filteredHotels = hotelsData;
        displayHotelsOnMap(hotelsData);
        updateStatistics(hotelsData);
    } catch (error) {
        console.error('Error loading hotels:', error);
        showNotification(`Error loading hotels: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Display hotels on the map with enhanced markers
function displayHotelsOnMap(hotels) {
    // Clear existing markers
    markersLayer.clearLayers();

    hotels.forEach(hotel => {
        // Parse and validate coordinates
        const lat = parseFloat(hotel.lat);
        const lon = parseFloat(hotel.lon);

        // Check if coordinates are valid numbers and in valid range
        if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
            // Determine marker color based on gap score category
            let markerColor = '#4F46E5'; // Default blue
            let markerIcon = 'fa-hotel';
            const gapScore = parseFloat(hotel.gap_score) || 0;

            const category = hotel.gap_category || '';
            if (category.includes('Much Better') || category.includes('Better Than Expected') || category === 'As Expected' || category === 'Reliable' || gapScore < 30) {
                markerColor = '#10B981'; // Green
                markerIcon = 'fa-check-circle';
            } else if (category === 'Medium Risk' || (gapScore >= 30 && gapScore < 70)) {
                markerColor = '#F59E0B'; // Orange
                markerIcon = 'fa-exclamation-triangle';
            } else if (category.includes('High Risk') || gapScore >= 70) {
                markerColor = '#EF4444'; // Red
                markerIcon = 'fa-times-circle';
            }

            // Create custom icon with Font Awesome
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `
                    <div style="
                        background-color: ${markerColor};
                        width: 32px;
                        height: 32px;
                        border-radius: 50%;
                        border: 3px solid white;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <i class="fas ${markerIcon}" style="color: white; font-size: 14px;"></i>
                    </div>
                `,
                iconSize: [32, 32],
                iconAnchor: [16, 16]
            });

            // Create marker
            const marker = L.marker([lat, lon], { icon: icon });

            // Create enhanced popup content
            const popupContent = createEnhancedPopupContent(hotel);
            marker.bindPopup(popupContent, {
                maxWidth: 400,
                className: 'hotel-popup'
            });

            markersLayer.addLayer(marker);
        }
    });

    // Adjust map bounds to show all markers
    if (hotels.length > 0) {
        const bounds = markersLayer.getBounds();
        if (bounds.isValid()) {
            // If only a few hotels, zoom in more; if many, fit all
            if (hotels.length < 5) {
                map.fitBounds(bounds, { padding: [100, 100], maxZoom: 14 });
            } else {
                map.fitBounds(bounds, { padding: [50, 50] });
            }
        }
    } else {
        // If no hotels found, show a message
        console.log('No hotels found matching the current filters');
        showNotification('No hotels found matching your filters', 'info');
    }
}

// Create enhanced popup content for hotel
function createEnhancedPopupContent(hotel) {
    // Determine gap category styling
    let gapClass = 'gap-low';
    const category = hotel.gap_category || '';
    const gapScore = parseFloat(hotel.gap_score) || 0;

    if (category.includes('Much Better') || category.includes('Better Than Expected') || category === 'As Expected' || category === 'Reliable') {
        gapClass = 'gap-low';
    } else if (category === 'Medium Risk' || (gapScore >= 30 && gapScore < 70)) {
        gapClass = 'gap-medium';
    } else if (category.includes('High Risk') || gapScore >= 70) {
        gapClass = 'gap-high';
    }

    // Create amenities icons
    const amenities = [];
    if (hotel.has_wifi === '1' || hotel.has_wifi === 1) amenities.push({icon: 'fa-wifi', label: 'WiFi'});
    if (hotel.has_parking === '1' || hotel.has_parking === 1) amenities.push({icon: 'fa-parking', label: 'Parking'});
    if (hotel.has_pool === '1' || hotel.has_pool === 1) amenities.push({icon: 'fa-swimming-pool', label: 'Pool'});
    if (hotel.has_gym === '1' || hotel.has_gym === 1) amenities.push({icon: 'fa-dumbbell', label: 'Gym'});
    if (hotel.has_breakfast === '1' || hotel.has_breakfast === 1) amenities.push({icon: 'fa-coffee', label: 'Breakfast'});
    if (hotel.has_ac === '1' || hotel.has_ac === 1) amenities.push({icon: 'fa-snowflake', label: 'AC'});

    const amenitiesHtml = amenities.map(a =>
        `<div class="amenity-icon">
            <i class="fas ${a.icon}"></i>
            <span>${a.label}</span>
        </div>`
    ).join('');

    // Parse complaints and praises
    let complaintsHtml = '';
    if (hotel.main_complaints) {
        const complaints = hotel.main_complaints.split(',').slice(0, 3);
        complaintsHtml = `
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #E5E7EB;">
                <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;">
                    <i class="fas fa-thumbs-down text-danger"></i> Main Concerns
                </div>
                <ul style="margin: 0; padding-left: 20px; font-size: 0.85rem; color: #6B7280;">
                    ${complaints.map(c => `<li>${c.trim()}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    let praisesHtml = '';
    if (hotel.main_praises) {
        const praises = hotel.main_praises.split(',').slice(0, 3);
        praisesHtml = `
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #E5E7EB;">
                <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;">
                    <i class="fas fa-thumbs-up text-success"></i> Top Praises
                </div>
                <ul style="margin: 0; padding-left: 20px; font-size: 0.85rem; color: #6B7280;">
                    ${praises.map(p => `<li>${p.trim()}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    const distanceKm = hotel.distance_from_center_km ? parseFloat(hotel.distance_from_center_km).toFixed(1) : 'N/A';
    const reviewScore = hotel.review_score || 'N/A';
    const realityScore = hotel.predicted_reality_score ? parseFloat(hotel.predicted_reality_score).toFixed(1) : 'N/A';
    const gapScoreFormatted = hotel.gap_score ? parseFloat(hotel.gap_score).toFixed(0) : 'N/A';

    return `
        <div class="hotel-popup">
            <div class="popup-header">
                <div class="popup-title">${hotel.title || 'Hotel'}</div>
                <div class="popup-location">
                    <i class="fas fa-map-marker-alt"></i> ${hotel.city} • ${distanceKm} km from center
                </div>
            </div>

            <div class="popup-metrics">
                <div class="metric-box">
                    <div class="metric-label">Review Score</div>
                    <div class="metric-value">${reviewScore}/10</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Reality Score</div>
                    <div class="metric-value">${realityScore}/10</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Gap Score</div>
                    <div class="metric-value">${gapScoreFormatted}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Reviews</div>
                    <div class="metric-value">${hotel.number_of_reviews || 0}</div>
                </div>
            </div>

            <div class="gap-badge ${gapClass}">
                <i class="fas fa-shield-alt"></i>
                ${hotel.gap_category || 'Risk Unknown'} • ${hotel.risk_level || 'Unknown'}
            </div>

            ${amenitiesHtml ? `<div class="amenity-list">${amenitiesHtml}</div>` : ''}

            ${complaintsHtml}
            ${praisesHtml}

            <a href="${hotel.url}" target="_blank" class="btn-booking">
                <i class="fas fa-external-link-alt"></i> View on Booking.com
            </a>
        </div>
    `;
}

// Update statistics
function updateStatistics(hotels) {
    document.getElementById('total-hotels').textContent = hotels.length.toLocaleString();

    const uniqueCities = [...new Set(hotels.map(h => h.city))];
    document.getElementById('cities-count').textContent = uniqueCities.length;
}

// Setup event listeners
function setupEventListeners() {
    // City filter - auto-apply when changed
    const cityFilter = document.getElementById('city-filter');
    cityFilter.addEventListener('change', function() {
        applyFilters();
    });

    // Hotel search input
    const hotelSearch = document.getElementById('hotel-search');
    hotelSearch.addEventListener('input', debounce(function() {
        const searchTerm = this.value.toLowerCase();
        if (searchTerm.length >= 2 || searchTerm === '') {
            searchHotels(searchTerm);
        }
    }, 300));

    // Review score sliders
    const reviewMin = document.getElementById('review-min');
    const reviewMax = document.getElementById('review-max');
    const reviewMinValue = document.getElementById('review-min-value');
    const reviewMaxValue = document.getElementById('review-max-value');

    reviewMin.addEventListener('input', function() {
        reviewMinValue.textContent = this.value;
        if (parseFloat(this.value) > parseFloat(reviewMax.value)) {
            reviewMax.value = this.value;
            reviewMaxValue.textContent = this.value;
        }
    });

    reviewMax.addEventListener('input', function() {
        reviewMaxValue.textContent = this.value;
        if (parseFloat(this.value) < parseFloat(reviewMin.value)) {
            reviewMin.value = this.value;
            reviewMinValue.textContent = this.value;
        }
    });

    // Minimum reviews slider
    const minReviews = document.getElementById('min-reviews');
    const minReviewsValue = document.getElementById('min-reviews-value');
    minReviews.addEventListener('input', function() {
        minReviewsValue.textContent = this.value;
    });

    // Distance slider
    const distanceFilter = document.getElementById('distance-filter');
    const distanceValue = document.getElementById('distance-value');

    distanceFilter.addEventListener('input', function() {
        distanceValue.textContent = this.value;
    });

    // Apply filters button
    document.getElementById('apply-filters').addEventListener('click', applyFilters);

    // Reset filters button
    document.getElementById('reset-filters').addEventListener('click', resetFilters);
}

// Search hotels by name
function searchHotels(searchTerm) {
    if (!searchTerm) {
        displayHotelsOnMap(filteredHotels);
        updateStatistics(filteredHotels);
        return;
    }

    const searchResults = filteredHotels.filter(hotel =>
        hotel.title && hotel.title.toLowerCase().includes(searchTerm)
    );

    displayHotelsOnMap(searchResults);
    updateStatistics(searchResults);
}

// Apply filters
async function applyFilters() {
    showLoading(true);

    // Collect filter values
    const filters = {};

    // City filter
    const cityFilter = document.getElementById('city-filter').value;
    if (cityFilter) {
        filters.city = cityFilter;
    }

    // Review score filters
    filters.review_min = parseFloat(document.getElementById('review-min').value);
    filters.review_max = parseFloat(document.getElementById('review-max').value);

    // Minimum reviews filter
    const minReviews = parseInt(document.getElementById('min-reviews').value);
    if (minReviews > 0) {
        filters.min_reviews = minReviews;
    }

    // Gap categories
    const gapCategories = [];
    document.querySelectorAll('.gap-filter:checked').forEach(checkbox => {
        gapCategories.push(checkbox.value);
    });
    if (gapCategories.length > 0) {
        filters.gap_categories = gapCategories;
    }

    // Amenities
    const amenities = [];
    document.querySelectorAll('.amenity-filter:checked').forEach(checkbox => {
        amenities.push(checkbox.value);
    });
    if (amenities.length > 0) {
        filters.amenities = amenities;
    }

    // Distance filter
    filters.max_distance = parseFloat(document.getElementById('distance-filter').value);

    console.log('Sending filters:', filters);

    try {
        const response = await fetch('/api/hotels/filtered', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filters)
        });

        // Check if response is successful
        if (!response.ok) {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            showNotification(`Error: ${errorData.error || 'Failed to apply filters'}`, 'error');
            showLoading(false);
            return;
        }

        const hotels = await response.json();
        console.log(`Received ${hotels.length} hotels`);

        // Check if we got valid data
        if (!Array.isArray(hotels)) {
            console.error('Invalid response format:', hotels);
            showNotification('Received invalid data from server', 'error');
            showLoading(false);
            return;
        }

        filteredHotels = hotels;

        // Apply hotel name search if present
        const searchTerm = document.getElementById('hotel-search').value.toLowerCase();
        if (searchTerm) {
            const searchResults = hotels.filter(hotel =>
                hotel.title && hotel.title.toLowerCase().includes(searchTerm)
            );
            displayHotelsOnMap(searchResults);
            updateStatistics(searchResults);
        } else {
            displayHotelsOnMap(hotels);
            updateStatistics(hotels);
        }
    } catch (error) {
        console.error('Error applying filters:', error);
        showNotification(`Error applying filters: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Reset all filters
function resetFilters() {
    // Reset city
    document.getElementById('city-filter').value = '';

    // Reset hotel search
    document.getElementById('hotel-search').value = '';

    // Reset review scores
    document.getElementById('review-min').value = 7;
    document.getElementById('review-max').value = 10;
    document.getElementById('review-min-value').textContent = '7.0';
    document.getElementById('review-max-value').textContent = '10.0';

    // Reset minimum reviews
    document.getElementById('min-reviews').value = 0;
    document.getElementById('min-reviews-value').textContent = '0';

    // Reset gap categories
    document.getElementById('gap-much-better').checked = true;
    document.getElementById('gap-better').checked = true;
    document.getElementById('gap-expected').checked = true;
    document.getElementById('gap-medium').checked = true;
    document.getElementById('gap-high').checked = false;

    // Reset amenities
    document.querySelectorAll('.amenity-filter').forEach(checkbox => {
        checkbox.checked = false;
    });

    // Reset distance
    document.getElementById('distance-filter').value = 20;
    document.getElementById('distance-value').textContent = '20';

    // Reload initial hotels
    loadInitialHotels();
}

// Show/hide loading overlay
function showLoading(show) {
    const loadingOverlay = document.getElementById('loading');
    if (show) {
        loadingOverlay.classList.remove('hidden');
    } else {
        loadingOverlay.classList.add('hidden');
    }
}

// Show notification (you can enhance this further)
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);

    // You could add a toast notification here
    // For now, we'll use console logging
    if (type === 'error') {
        console.error(message);
    }
}

// Debounce utility function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}