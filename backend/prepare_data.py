import kagglehub
import shutil
import os
from pathlib import Path
import glob

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
COMBINED_DIR = DATASET_DIR / "combined"

def setup_dirs():
    """Create necessary directories."""
    print(f"Creating directories in {COMBINED_DIR}...")
    COMBINED_DIR.mkdir(parents=True, exist_ok=True)
    
    classes = [
        "COVID-19",
        "Tuberculosis",
        "Bacterial Pneumonia",
        "Viral Pneumonia",
        "Normal",
    ]
    for cls in classes:
        (COMBINED_DIR / cls).mkdir(parents=True, exist_ok=True)
    print("Directories created.")

def copy_images(src_dir, dest_dir):
    """Copy images from source to destination, handling 'images' subdir."""
    
    # Check if 'images' subdir exists
    src_path = Path(src_dir)
    if (src_path / "images").exists():
        src_path = src_path / "images"
    
    print(f"Copying from {src_path} to {dest_dir}...")
    
    files = glob.glob(f"{src_path}/*.png") + glob.glob(f"{src_path}/*.jpg") + glob.glob(f"{src_path}/*.jpeg")
    
    if not files:
        print(f"WARNING: No images found in {src_path}")
        return

    count = 0
    for f in files:
        try:
            shutil.copy(f, dest_dir)
            count += 1
        except Exception as e:
            print(f"Error copying {f}: {e}")
            
    print(f"  -> Copied {count} images.")

def main():
    setup_dirs()
    
    print("\n--- Downloading COVID-19 Radiography Database ---")
    covid_path = kagglehub.dataset_download("tawsifurrahman/covid19-radiography-database")
    print(f"Downloaded to: {covid_path}")
    
    print("\nProcessing COVID-19 Data...")
    # Map: Source Folder -> Destination Folder
    # Note check if downloaded structure has dataset name as root
    # Usually kagglehub returns path to the dataset root
    
    # 1. COVID-19
    copy_images(
        src_dir=os.path.join(covid_path, "COVID-19_Radiography_Dataset", "COVID"),
        dest_dir=COMBINED_DIR / "COVID-19"
    )
    
    # 2. Viral Pneumonia
    copy_images(
        src_dir=os.path.join(covid_path, "COVID-19_Radiography_Dataset", "Viral Pneumonia"),
        dest_dir=COMBINED_DIR / "Viral Pneumonia"
    )
    
    # 3. Bacterial Pneumonia (Lung_Opacity)
    copy_images(
        src_dir=os.path.join(covid_path, "COVID-19_Radiography_Dataset", "Lung_Opacity"),
        dest_dir=COMBINED_DIR / "Bacterial Pneumonia"
    )
    
    # 4. Normal (Part 1)
    copy_images(
        src_dir=os.path.join(covid_path, "COVID-19_Radiography_Dataset", "Normal"),
        dest_dir=COMBINED_DIR / "Normal"
    )

    print("\n--- Downloading Tuberculosis TB Chest X-ray Database ---")
    tb_path = kagglehub.dataset_download("tawsifurrahman/tuberculosis-tb-chest-xray-dataset")
    print(f"Downloaded to: {tb_path}")
    
    print("\nProcessing Tuberculosis Data...")
    
    # 5. Tuberculosis
    # Check structure. User says: TB_Chest_Radiography_Database / Tuberculosis
    copy_images(
        src_dir=os.path.join(tb_path, "TB_Chest_Radiography_Database", "Tuberculosis"),
        dest_dir=COMBINED_DIR / "Tuberculosis"
    )
    
    # 6. Normal (Part 2 - Optional, add more normal images)
    copy_images(
        src_dir=os.path.join(tb_path, "TB_Chest_Radiography_Database", "Normal"),
        dest_dir=COMBINED_DIR / "Normal"
    )

    print("\n--- Dataset Preparation Complete! ---")
    print(f"Data is ready in: {COMBINED_DIR}")
    print("You can now run 'python ml_model/train.py'")

if __name__ == "__main__":
    main()
