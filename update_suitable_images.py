#!/usr/bin/env python3
"""
Update MVP public/images to only include suitable images
Removes all existing images and copies only suitable labeled images
"""

import pandas as pd
import shutil
from pathlib import Path
import os

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MVP_DIR = Path(__file__).parent
TRAINING_DATA_DIR = PROJECT_ROOT / 'training_data'
SCRAPED_DATA_DIR = PROJECT_ROOT / 'scraped_data'
IMAGES_SOURCE = SCRAPED_DATA_DIR / 'images'
IMAGES_TARGET = MVP_DIR / 'public' / 'images' / 'spots'

def normalize_path(path_str):
    """Normalize path from CSV format to actual file path."""
    # Remove scraped_data\images\ prefix and convert backslashes
    path = path_str.replace('scraped_data\\images\\', '').replace('scraped_data/images/', '')
    path = path.replace('\\', '/')
    return path

def main():
    print("="*80)
    print("UPDATING MVP IMAGES - KEEPING ONLY SUITABLE IMAGES")
    print("="*80)
    
    suitable_images = []
    
    # Load labeled data (manually labeled)
    labeled_file = TRAINING_DATA_DIR / 'all_labeled.csv'
    if labeled_file.exists():
        df_labeled = pd.read_csv(labeled_file)
        print(f"\nLoaded {len(df_labeled)} labeled images")
        
        # Filter suitable images
        suitable_labeled = df_labeled[df_labeled['label'] == 'suitable'].copy()
        print(f"Found {len(suitable_labeled)} manually labeled suitable images")
        
        for _, row in suitable_labeled.iterrows():
            suitable_images.append(row['image_path'])
    else:
        print(f"Warning: {labeled_file} not found, skipping labeled images")
    
    # Load predicted data (from inference)
    ML_DIR = PROJECT_ROOT / 'ml'
    predictions_file = ML_DIR / 'data' / 'predictions_all_unlabeled.csv'
    if predictions_file.exists():
        df_pred = pd.read_csv(predictions_file)
        print(f"\nLoaded {len(df_pred)} predicted images")
        
        # Filter suitable predictions
        suitable_pred = df_pred[df_pred['label'] == 'suitable'].copy()
        print(f"Found {len(suitable_pred)} predicted suitable images")
        
        # Convert absolute paths to relative paths
        for _, row in suitable_pred.iterrows():
            img_path = Path(row['image_path'])
            # Convert to relative path from scraped_data/images
            try:
                rel_path = img_path.relative_to(SCRAPED_DATA_DIR / 'images')
                suitable_images.append(f"scraped_data\\images\\{rel_path}")
            except ValueError:
                # Try alternative path format
                if 'scraped_data' in str(img_path):
                    suitable_images.append(str(img_path).replace(str(PROJECT_ROOT) + '\\', ''))
    else:
        print(f"Warning: {predictions_file} not found, skipping predicted images")
    
    # Remove duplicates
    suitable_images = list(set(suitable_images))
    print(f"\nTotal unique suitable images: {len(suitable_images)}")
    
    if len(suitable_images) == 0:
        print("No suitable images found!")
        return
    
    # Create DataFrame for easier processing
    suitable_df = pd.DataFrame({'image_path': suitable_images})
    
    # Remove all existing images in target directory
    print(f"\nRemoving existing images from {IMAGES_TARGET}")
    if IMAGES_TARGET.exists():
        # Remove all spot directories
        for spot_dir in IMAGES_TARGET.iterdir():
            if spot_dir.is_dir():
                shutil.rmtree(spot_dir)
                print(f"  Removed {spot_dir.name}")
        print("  All existing images removed")
    else:
        IMAGES_TARGET.mkdir(parents=True, exist_ok=True)
        print(f"  Created directory: {IMAGES_TARGET}")
    
    # Copy suitable images
    print(f"\nCopying suitable images...")
    copied_count = 0
    missing_count = 0
    
    for idx, row in suitable_df.iterrows():
        # Get source path
        source_path_str = row['image_path']
        normalized = normalize_path(source_path_str)
        source_path = IMAGES_SOURCE / normalized
        
        if not source_path.exists():
            print(f"  Warning: Source image not found: {source_path}")
            missing_count += 1
            continue
        
        # Get target path (maintain spot folder structure)
        target_path = IMAGES_TARGET / normalized
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy image
        try:
            shutil.copy2(source_path, target_path)
            copied_count += 1
            if copied_count % 10 == 0:
                print(f"  Copied {copied_count} images...")
        except Exception as e:
            print(f"  Error copying {source_path}: {e}")
            missing_count += 1
    
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total suitable images: {len(suitable_df)}")
    print(f"Successfully copied: {copied_count}")
    print(f"Missing/errors: {missing_count}")
    print(f"\nTarget directory: {IMAGES_TARGET}")
    print("="*80)

if __name__ == '__main__':
    main()

