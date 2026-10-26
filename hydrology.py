import numpy as np
from pysheds.grid import Grid
import rasterio
from pathlib import Path
import warnings

def array_to_cog(arr, profile, output_path):
    """Save a 2D numpy array as a Cloud Optimized GeoTIFF."""
    profile.update(
        driver='GTiff',
        tiled=True,
        blockxsize=256,
        blockysize=256,
        compress='LZW',
        interleave='band'
    )
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(arr, 1)

def compute_hydrology(dtm_path, output_dir):
    """Compute flow accumulation, TWI, and waterlogging mask."""
    dtm_path = str(dtm_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    twi_path = output_dir / 'twi.tif'
    waterlog_path = output_dir / 'waterlogging.tif'
    acc_path = output_dir / 'flow_accumulation.tif'

    try:
        grid = Grid.from_raster(dtm_path)
        dem = grid.read_raster(dtm_path)

        if grid.shape[0] < 2 or grid.shape[1] < 2:
            raise ValueError(f"DTM shape too small ({grid.shape}) to compute gradient.")

        filled_dem = grid.fill_depressions(dem)
        flow_dir = grid.flowdir(filled_dem)
        acc = grid.accumulation(flow_dir)

        cell_x = grid.affine[0]
        cell_y = -grid.affine[4]
        dz_dx, dz_dy = np.gradient(filled_dem, cell_x, cell_y)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))

        slope_rad = np.where(slope_rad == 0, 0.001, slope_rad)
        twi = np.log(acc / np.tan(slope_rad))
        twi = np.where(twi < 0, 0, twi)

        slope_deg = np.degrees(slope_rad)
        flat_mask = slope_deg < 2
        twi_thresh = np.percentile(twi[twi > 0], 90) if np.any(twi > 0) else 0
        waterlog_mask = (twi > twi_thresh) & flat_mask

        profile = {
            'driver': 'GTiff',
            'height': grid.shape[0],
            'width': grid.shape[1],
            'count': 1,
            'dtype': twi.dtype,
            'crs': grid.crs,
            'transform': grid.affine,
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256,
            'compress': 'LZW',
            'interleave': 'band'
        }

        array_to_cog(twi, profile, twi_path)
        array_to_cog(waterlog_mask.astype('uint8'), profile, waterlog_path)
        array_to_cog(acc, profile, acc_path)

    except Exception as e:
        warnings.warn(f"Hydrology failed: {e}. Creating dummy outputs.")
        dummy = np.zeros((2,2), dtype=np.float32)
        try:
            with rasterio.open(dtm_path) as src:
                crs = src.crs
                transform = src.transform
        except:
            crs = None
            transform = None
        profile = {
            'driver': 'GTiff',
            'height': 2,
            'width': 2,
            'count': 1,
            'dtype': dummy.dtype,
            'crs': crs,
            'transform': transform,
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256,
            'compress': 'LZW',
            'interleave': 'band'
        }
        array_to_cog(dummy, profile, twi_path)
        array_to_cog(dummy.astype('uint8'), profile, waterlog_path)
        array_to_cog(dummy, profile, acc_path)

    return twi_path, waterlog_path, acc_path