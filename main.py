import argparse
from pathlib import Path
from src.classify import classify_point_cloud
from src.dtm import generate_dtm
from src.hydrology import compute_hydrology
from src.drainage import design_drainage

def process_village(las_path, out_dir, model_path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Step 1: Classify
    classified_dir = out_dir / 'classified_las'
    classified_dir.mkdir(exist_ok=True)
    classified_las = classified_dir / f"{las_path.stem}_classified.las"
    classify_point_cloud(las_path, model_path, classified_las)
    # Step 2: DTM
    dtm_dir = out_dir / 'dtm'
    dtm_dir.mkdir(exist_ok=True)
    dtm_path = generate_dtm(classified_las, dtm_dir)
    # Step 3: Hydrology
    hydro_dir = out_dir / 'hydrology'
    hydro_dir.mkdir(exist_ok=True)
    twi_path, waterlog_path, acc_path = compute_hydrology(dtm_path, hydro_dir)
    # Step 4: Drainage
    drain_dir = out_dir / 'drainage'
    drain_dir.mkdir(exist_ok=True)
    drainage_path = design_drainage(dtm_path, waterlog_path, drain_dir)
    print(f"Processing complete for {las_path.name}")
    return {
        'classified': classified_las,
        'dtm': dtm_path,
        'twi': twi_path,
        'waterlog': waterlog_path,
        'drainage': drainage_path
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run DTM and drainage pipeline on a village LAS file.')
    parser.add_argument('--input', required=True, help='Path to input LAS file')
    parser.add_argument('--outdir', required=True, help='Output directory')
    parser.add_argument('--model', default='models/ground_classifier.pkl', help='Path to trained model')
    args = parser.parse_args()
    process_village(Path(args.input), Path(args.outdir), args.model)