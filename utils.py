import numpy as np
from scipy.spatial import cKDTree
import laspy
import rasterio
from rasterio.transform import from_origin
from pathlib import Path

def compute_features(xyz, k=30):
    """Compute geometric features for each point using k-nearest neighbors."""
    tree = cKDTree(xyz)
    distances, indices = tree.query(xyz, k=k+1)
    features = []
    for i, neigh in enumerate(indices[:, 1:]):
        pts = xyz[neigh]
        cov = np.cov(pts.T)
        eigvals = np.linalg.eigvalsh(cov)
        eigvals = np.sort(eigvals)[::-1]
        total = eigvals.sum() + 1e-12
        linearity = (eigvals[0] - eigvals[1]) / total
        planarity = (eigvals[1] - eigvals[2]) / total
        sphericity = eigvals[2] / total
        # Height variation
        z_range = pts[:, 2].max() - pts[:, 2].min()
        features.append([linearity, planarity, sphericity, z_range])
    return np.array(features)

def write_classified_las(input_las, output_las, labels):
    """Write a new LAS file with classification field set."""
    with laspy.open(input_las) as f:
        las = f.read()
    las.classification = labels
    with laspy.open(output_las, mode='w', header=las.header) as writer:
        writer.write_points(las)

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