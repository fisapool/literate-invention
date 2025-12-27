#!/usr/bin/env python3
"""
Update spots-simple.json to only include images that actually exist
After filtering to suitable images, some images in the JSON don't exist anymore
"""

import json
from pathlib import Path

MVP_DIR = Path(__file__).parent
SPOTS_DIR = MVP_DIR / 'public' / 'images' / 'spots'
DATA_DIR = MVP_DIR / 'data'
INPUT_FILE = DATA_DIR / 'spots-simple.json'
OUTPUT_FILE = DATA_DIR / 'spots-simple.json'

def get_existing_images():
    """Get all existing images organized by spot."""
    existing = {}
    
    if not SPOTS_DIR.exists():
        print(f"Warning: {SPOTS_DIR} does not exist!")
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

def update_spots_json():
    """Update spots-simple.json to only include existing images."""
    print("="*80)
    print("UPDATING SPOTS JSON - REMOVING MISSING IMAGES")
    print("="*80)
    
    # Get existing images
    existing_images = get_existing_images()
    print(f"\nFound {len(existing_images)} spots with images")
    total_images = sum(len(imgs) for imgs in existing_images.values())
    print(f"Total existing images: {total_images}")
    
    # Load original enriched spots data for metadata
    PROJECT_ROOT = MVP_DIR.parent
    enriched_file = PROJECT_ROOT / 'scraped_data' / 'enriched_spots.json'
    
    spots_data = []
    if enriched_file.exists():
        with open(enriched_file, 'r', encoding='utf-8') as f:
            spots_data = json.load(f)
        print(f"Loaded {len(spots_data)} spots from enriched_spots.json")
    else:
        print(f"Warning: {enriched_file} not found, using minimal data")
    
    # Build spots list from existing images
    spots = []
    updated_count = 0
    removed_count = 0
    
    for spot_name in sorted(existing_images.keys()):
        # Extract spot index from name like "spot_0" -> 0
        try:
            spot_idx = int(spot_name.replace('spot_', ''))
        except ValueError:
            continue
        
        # Get spot metadata from enriched data if available
        if spot_idx < len(spots_data):
            spot_data = spots_data[spot_idx]
            google_data = spot_data.get('google_maps_data', {})
            name = google_data.get('place_name', f"Spot {spot_idx + 1}")
            lat = spot_data.get('latitude', 0)
            lng = spot_data.get('longitude', 0)
            description = spot_data.get('description', 'Beautiful drone location')
            category = google_data.get('category', 'Nature')
            rating = google_data.get('rating')
            address = google_data.get('address', '')
        else:
            name = f"Spot {spot_idx + 1}"
            lat = 0
            lng = 0
            description = 'Beautiful drone location'
            category = 'Nature'
            rating = None
            address = ''
        
        # Build image paths
        images = [f"images/spots/{spot_name}/{img}" for img in existing_images[spot_name]]
        
        spot = {
            "id": spot_idx + 1,
            "name": name,
            "lat": lat,
            "lng": lng,
            "description": description,
            "category": category,
            "images": sorted(images),
            "rating": rating,
            "address": address,
            "notes": "Check local rules"
        }
        spots.append(spot)
    
    # Save updated JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(spots, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Spots in JSON: {len(spots)}")
    print(f"Total images: {total_images}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("="*80)

if __name__ == '__main__':
    update_spots_json()

