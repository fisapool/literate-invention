#!/usr/bin/env python3
"""
Fix the mapping between spot folders and locations
Version 2: Match based on actual image files in folders and their labels
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

MVP_DIR = Path(__file__).parent
PROJECT_ROOT = MVP_DIR.parent
SPOTS_DIR = MVP_DIR / 'public' / 'images' / 'spots'
DATA_DIR = MVP_DIR / 'data'
ENRICHED_FILE = PROJECT_ROOT / 'scraped_data' / 'enriched_spots.json'
LABELED_FILE = PROJECT_ROOT / 'training_data' / 'all_labeled.csv'
OUTPUT_FILE = DATA_DIR / 'spots-simple.json'

def get_spot_folder_from_path(path_str):
    """Extract spot folder name from image path."""
    path = path_str.replace('\\', '/')
    prefixes = ['images/', 'scraped_data/images/', 'images\\', 'scraped_data\\images\\']
    for prefix in prefixes:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if 'spot_' in path:
        parts = path.split('/')
        for part in parts:
            if part.startswith('spot_'):
                return part
    return None

def get_image_filename_from_path(path_str):
    """Extract just the filename from a path."""
    return Path(path_str).name

def build_spot_to_location_mapping():
    """Build mapping from spot folders to locations based on actual images and labels."""
    # Load labeled data to see which images belong to which locations
    if not LABELED_FILE.exists():
        print(f"Warning: {LABELED_FILE} not found, using enriched_spots.json only")
        return {}
    
    df_labeled = pd.read_csv(LABELED_FILE)
    print(f"Loaded {len(df_labeled)} labeled images")
    
    # Load enriched spots
    if not ENRICHED_FILE.exists():
        print(f"Error: {ENRICHED_FILE} not found!")
        return {}
    
    with open(ENRICHED_FILE, 'r', encoding='utf-8') as f:
        enriched_data = json.load(f)
    
    # Build a mapping: image_filename -> location_index
    # by checking which location in enriched_spots.json has this image
    image_to_location = {}
    for loc_idx, location in enumerate(enriched_data):
        google_data = location.get('google_maps_data', {})
        images = google_data.get('images', [])
        for img in images:
            local_path = img.get('local_path', '')
            if local_path:
                filename = get_image_filename_from_path(local_path)
                spot_folder = get_spot_folder_from_path(local_path)
                # Store as spot_folder/filename -> location
                key = f"{spot_folder}/{filename}" if spot_folder else filename
                image_to_location[key] = loc_idx
    
    print(f"Built mapping for {len(image_to_location)} images to locations")
    
    # Now, for each spot folder, find which location has the most matching images
    spot_to_location_votes = defaultdict(lambda: defaultdict(int))
    
    # Get actual images in each spot folder
    existing_images = {}
    for spot_dir in SPOTS_DIR.iterdir():
        if spot_dir.is_dir():
            spot_name = spot_dir.name
            images = []
            for img_file in spot_dir.iterdir():
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    images.append(img_file.name)
            if images:
                existing_images[spot_name] = images
    
    # For each spot folder, check which location has the most matching images
    for spot_folder, image_files in existing_images.items():
        for img_file in image_files:
            key = f"{spot_folder}/{img_file}"
            if key in image_to_location:
                loc_idx = image_to_location[key]
                spot_to_location_votes[spot_folder][loc_idx] += 1
    
    # Choose the location with most votes for each spot
    spot_to_location = {}
    for spot_folder, votes in spot_to_location_votes.items():
        if votes:
            best_location = max(votes.items(), key=lambda x: x[1])[0]
            spot_to_location[spot_folder] = best_location
            loc_name = enriched_data[best_location].get('google_maps_data', {}).get('place_name', f'Location {best_location}')
            print(f"  {spot_folder} -> Location {best_location} ({loc_name}) - {votes[best_location]} votes")
    
    return spot_to_location, enriched_data

def get_existing_images():
    """Get all existing images organized by spot folder."""
    existing = {}
    if not SPOTS_DIR.exists():
        return existing
    
    for spot_dir in SPOTS_DIR.iterdir():
        if spot_dir.is_dir():
            spot_name = spot_dir.name
            images = []
            for img_file in spot_dir.iterdir():
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    images.append(img_file.name)
            if images:
                existing[spot_name] = sorted(images)
    
    return existing

def fix_spots_json():
    """Fix spots-simple.json with correct location-to-spot mapping."""
    print("="*80)
    print("FIXING SPOTS JSON - VERSION 2 (BASED ON ACTUAL IMAGES)")
    print("="*80)
    
    # Build mapping based on actual images
    spot_to_location, enriched_data = build_spot_to_location_mapping()
    print(f"\nMapped {len(spot_to_location)} spots to locations")
    
    # Get existing images
    existing_images = get_existing_images()
    print(f"Found {len(existing_images)} spot folders with images")
    
    # Build spots list
    spots = []
    for spot_folder in sorted(existing_images.keys()):
        loc_idx = spot_to_location.get(spot_folder)
        
        # Build image paths
        images = [f"images/spots/{spot_folder}/{img}" for img in existing_images[spot_folder]]
        
        # Get location data if available
        if loc_idx is not None and loc_idx < len(enriched_data):
            location = enriched_data[loc_idx]
            google_data = location.get('google_maps_data', {})
            
            spot = {
                "id": len(spots) + 1,
                "name": google_data.get('place_name', f"Spot {loc_idx + 1}"),
                "lat": location.get('latitude', 0),
                "lng": location.get('longitude', 0),
                "description": location.get('description', 'Beautiful drone location'),
                "category": google_data.get('category', 'Nature'),
                "images": sorted(images),
                "rating": google_data.get('rating'),
                "address": google_data.get('address', ''),
                "notes": "Check local rules"
            }
        else:
            # No location data available
            try:
                spot_idx = int(spot_folder.replace('spot_', ''))
            except ValueError:
                spot_idx = len(spots)
            
            spot = {
                "id": len(spots) + 1,
                "name": f"Drone Spot {spot_idx + 1}",
                "lat": 0,
                "lng": 0,
                "description": "Beautiful drone location",
                "category": "Nature",
                "images": sorted(images),
                "rating": None,
                "address": "",
                "notes": "Check local rules"
            }
        
        spots.append(spot)
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(spots, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Spots created: {len(spots)}")
    print(f"Total images: {sum(len(s['images']) for s in spots)}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("="*80)
    
    # Show some examples
    print("\nExample mappings:")
    for i, spot in enumerate(spots[:5]):
        print(f"  Spot {spot['id']}: {spot['name']} -> {spot['images'][0].split('/')[2] if spot['images'] else 'no images'}")

if __name__ == '__main__':
    fix_spots_json()

