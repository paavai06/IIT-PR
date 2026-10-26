import geopandas as gpd
from pysheds.grid import Grid
from pathlib import Path
import warnings

def design_drainage(dtm_path, waterlog_path, output_dir, stream_threshold=100):
    """Extract natural drainage network from DTM and save as GeoPackage."""
    dtm_path = str(dtm_path)
    grid = Grid.from_raster(dtm_path)
    dem = grid.read_raster(dtm_path)
    filled_dem = grid.fill_depressions(dem)
    flow_dir = grid.flowdir(filled_dem)
    acc = grid.accumulation(flow_dir)
    streams = acc > stream_threshold
    branches = grid.extract_river_network(flow_dir, streams)

    # Convert to GeoDataFrame if needed
    if not isinstance(branches, gpd.GeoDataFrame):
        if hasattr(branches, '__geo_interface__'):
            try:
                import geojson
                if isinstance(branches, geojson.FeatureCollection):
                    branches = gpd.GeoDataFrame.from_features(branches['features'])
                else:
                    branches = gpd.GeoDataFrame.from_features(branches.__geo_interface__['features'])
            except Exception:
                warnings.warn("Could not convert to GeoDataFrame. Creating empty.")
                branches = gpd.GeoDataFrame(geometry=[])
        else:
            branches = gpd.GeoDataFrame(geometry=[])

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = output_dir / 'drainage_network.gpkg'
    branches.to_file(gpkg_path, driver='GPKG')
    return gpkg_path