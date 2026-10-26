import numpy as np
import laspy
from scipy.interpolate import griddata
from scipy.interpolate import NearestNDInterpolator
import rasterio
from rasterio.transform import from_origin
from pathlib import Path
from .utils import array_to_cog
import warnings

def generate_dtm(classified_las_path, output_dir, resolution=2.0, max_ground_points=500000, fill_nodata=True):
    """
    Generate DTM from ground points, using the full point cloud extent.
    If number of ground points exceeds max_ground_points, sample them.
    """
    classified_las_path = Path(classified_las_path)
    las = laspy.read(classified_las_path)

    # Check classification labels
    ground_mask = las.classification == 1
    n_ground = ground_mask.sum()
    print(f"Number of ground points: {n_ground}")

    # If no ground points, fall back to all points
    if n_ground == 0:
        warnings.warn("No ground points found! Using all points as ground (fallback).")
        ground_mask = np.ones(len(las.points), dtype=bool)
        n_ground = ground_mask.sum()

    # Sample ground points if too many
    if n_ground > max_ground_points:
        print(f"Sampling {max_ground_points} ground points from {n_ground}...")
        indices = np.random.choice(n_ground, max_ground_points, replace=False)
        # Extract ground points coordinates and elevations as arrays
        x_all = las.x
        y_all = las.y
        z_all = las.z
        # Create a boolean mask for sampled points (we need to map indices to full array)
        # It's easier to get the indices of ground points, then subset
        ground_indices = np.where(ground_mask)[0]
        sampled_indices = ground_indices[indices]
        x_ground = x_all[sampled_indices]
        y_ground = y_all[sampled_indices]
        z_ground = z_all[sampled_indices]
    else:
        x_ground = las.x[ground_mask]
        y_ground = las.y[ground_mask]
        z_ground = las.z[ground_mask]

    # Use the full point cloud's extent for the grid
    x_all = las.x
    y_all = las.y
    x_min, x_max = x_all.min(), x_all.max()
    y_min, y_max = y_all.min(), y_all.max()

    # Define grid (ensure at least 2 cells in each direction)
    nx = max(int((x_max - x_min) / resolution) + 1, 2)
    ny = max(int((y_max - y_min) / resolution) + 1, 2)

    # Create meshgrid
    grid_x, grid_y = np.meshgrid(np.linspace(x_min, x_max, nx),
                                 np.linspace(y_min, y_max, ny))

    # Interpolate: first try linear interpolation, then fill NaNs with nearest neighbour
    grid_z = griddata((x_ground, y_ground), z_ground, (grid_x, grid_y), method='linear')
    if fill_nodata:
        # Fill any NaN cells using nearest neighbour interpolation
        nan_mask = np.isnan(grid_z)
        if nan_mask.any() and len(x_ground) > 0:
            # Use nearest neighbour to fill missing values
            # Build points array as (n,2)
            points = np.column_stack((x_ground, y_ground))
            nn = NearestNDInterpolator(points, z_ground)
            grid_z[nan_mask] = nn(grid_x[nan_mask], grid_y[nan_mask])

    # Profile for output raster
    transform = from_origin(x_min, y_max, resolution, resolution)
    profile = {
        'driver': 'GTiff',
        'height': grid_z.shape[0],
        'width': grid_z.shape[1],
        'count': 1,
        'dtype': grid_z.dtype,
        'crs': las.header.parse_crs(),  # may be None if missing
        'transform': transform,
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
        'compress': 'LZW',
        'interleave': 'band'
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{classified_las_path.stem}_dtm.tif"
    array_to_cog(grid_z, profile, output_path)
    return output_path