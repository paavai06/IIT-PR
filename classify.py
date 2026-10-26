import numpy as np
import laspy
from sklearn.ensemble import RandomForestClassifier
import joblib
from .utils import compute_features, write_classified_las
from pathlib import Path

def reservoir_sample_points(las_path, sample_size, random_seed=42):
    """
    Randomly sample points from a LAS file using reservoir sampling.
    Returns an array of shape (sample_size, 3) with (x, y, z).
    """
    rng = np.random.default_rng(random_seed)
    sample = []
    count = 0
    with laspy.open(las_path) as f:
        for points in f.chunk_iterator(100000):
            chunk_xyz = np.vstack((points.x, points.y, points.z)).T
            for pt in chunk_xyz:
                count += 1
                if len(sample) < sample_size:
                    sample.append(pt)
                else:
                    j = rng.integers(0, count)
                    if j < sample_size:
                        sample[j] = pt
    return np.array(sample)

def generate_pseudo_labels(las_path, max_points=200000, ground_percentile=30, random_seed=42):
    """
    Generate pseudo-labels using a percentile threshold on elevation.
    """
    xyz = reservoir_sample_points(las_path, max_points, random_seed)
    z = xyz[:, 2]
    threshold = np.percentile(z, ground_percentile)
    labels = (z <= threshold).astype(int)
    return labels, xyz

def train_model(las_path, model_output_path, sample_size=200000):
    """
    Train a Random Forest classifier on a sampled subset.
    """
    print("Generating pseudo-labels on sample...")
    labels, xyz = generate_pseudo_labels(las_path, max_points=sample_size)
    print("Computing features on sample...")
    features = compute_features(xyz)   # uses k=30 neighbours
    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=20, n_jobs=-1, random_state=42)
    clf.fit(features, labels)
    joblib.dump(clf, model_output_path)
    print(f"Model saved to {model_output_path}")
    return clf

def classify_point_cloud(las_path, model_path, output_las_path, chunk_size=100000):
    """
    Apply trained model to classify entire point cloud.
    """
    clf = joblib.load(model_path)
    with laspy.open(las_path) as f:
        header = f.header
        with laspy.open(output_las_path, mode='w', header=header) as writer:
            for points in f.chunk_iterator(chunk_size):
                xyz = np.vstack((points.x, points.y, points.z)).T
                feats = compute_features(xyz)
                preds = clf.predict(feats)
                points.classification = preds
                writer.write_points(points)
    return output_las_path