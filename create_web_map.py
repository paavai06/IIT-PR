import geopandas as gpd
import folium
import os

# ------------------------------
# 1. Load the drainage network
# ------------------------------
gpkg_path = "D:/IIT pr/outputs/village1/drainage/drainage_network.gpkg"

try:
    drainage_gdf = gpd.read_file(gpkg_path)
    print(f"Loaded {len(drainage_gdf)} features from {gpkg_path}")
except Exception as e:
    print(f"Error reading file: {e}")
    drainage_gdf = None

# ------------------------------
# 2. Create the base map
# ------------------------------
# If drainage exists and has a geometry column, use its centroid for center
if drainage_gdf is not None and not drainage_gdf.empty and 'geometry' in drainage_gdf.columns:
    # Ensure it's a GeoDataFrame (some files load as DataFrame if no geometry)
    if not isinstance(drainage_gdf, gpd.GeoDataFrame):
        drainage_gdf = gpd.GeoDataFrame(drainage_gdf, geometry='geometry')
    
    # Check if CRS is set; if not, set a default (UTM 43N) then convert to WGS84
    if drainage_gdf.crs is None:
        print("No CRS detected. Assuming EPSG:32643 (UTM 43N).")
        drainage_gdf = drainage_gdf.set_crs('EPSG:32643')
    
    # Convert to WGS84 for web mapping (if not already)
    if drainage_gdf.crs != 'EPSG:4326':
        drainage_gdf = drainage_gdf.to_crs('EPSG:4326')
    
    # Get map center from the data
    center_lat = drainage_gdf.geometry.centroid.y.mean()
    center_lon = drainage_gdf.geometry.centroid.x.mean()
    map_center = [center_lat, center_lon]
    zoom = 15
else:
    # If no drainage data, use a default location (you can hardcode your village center)
    # Example: approximate coordinates for your village (adjust if known)
    map_center = [30.7, 76.8]   # Replace with your actual village centroid
    zoom = 14
    print("No drainage features found. Showing base map only.")

# Create the map
m = folium.Map(location=map_center, zoom_start=zoom, tiles="OpenStreetMap")

# ------------------------------
# 3. Add drainage lines (if they exist)
# ------------------------------
if drainage_gdf is not None and not drainage_gdf.empty and isinstance(drainage_gdf, gpd.GeoDataFrame):
    folium.GeoJson(
        drainage_gdf,
        name='Drainage Network',
        style_function=lambda x: {
            'color': 'blue',
            'weight': 3,
            'opacity': 0.8
        },
        tooltip=folium.GeoJsonTooltip(fields=['fid', 'type'], aliases=['ID', 'Type'])
    ).add_to(m)
    print("Drainage network added to map.")
else:
    # Add a marker to indicate no drainage data
    folium.Marker(
        location=map_center,
        popup="Drainage network generated but no stream lines found.<br>Check your DTM or adjust threshold.",
        icon=folium.Icon(color='red')
    ).add_to(m)

# ------------------------------
# 4. (Optional) Add a layer control
# ------------------------------
folium.LayerControl().add_to(m)

# ------------------------------
# 5. Save the map
# ------------------------------
output_file = "drainage_web_map.html"
m.save(output_file)
print(f"✅ Interactive map saved as '{output_file}'. Open it in your browser.")