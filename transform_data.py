#!/usr/bin/env python3
"""
Transform enriched_spots.json to spots-simple.json format for MVP
"""
import json
import os
from pathlib import Path

def normalize_image_path(path):
    """Convert Windows path to Unix path and adjust for public folder"""
    # Replace backslashes with forward slashes
    normalized = path.replace('\\', '/')
    # Remove 'images' prefix if present and add 'images/spots' prefix
    if normalized.startswith('images/'):
        normalized = normalized.replace('images/', 'images/spots/', 1)
    elif normalized.startswith('images\\'):
        normalized = normalized.replace('images\\', 'images/spots/', 1)
    else:
        # If no images prefix, add it
        if not normalized.startswith('images/spots/'):
            normalized = f"images/spots/{normalized}"
    return normalized

def transform_spots():
    """Transform enriched spots data to simple format"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Paths
    input_file = project_root / 'scraped_data' / 'enriched_spots.json'
    output_file = script_dir / 'data' / 'spots-simple.json'
    data_dir = script_dir / 'data'
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    
    # Read input data
    print(f"Reading from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Transform data
    simple = []
    for i, spot in enumerate(data):
        google_data = spot.get('google_maps_data', {})
        
        # Extract images
        images = []
        if 'images' in google_data:
            for img in google_data['images']:
                if 'local_path' in img:
                    images.append(normalize_image_path(img['local_path']))
        
        # If no images from google_maps_data, try to find images in spot folder
        if not images:
            spot_folder = script_dir / 'public' / 'images' / 'spots' / f'spot_{i}'
            if spot_folder.exists():
                image_files = sorted([f for f in spot_folder.iterdir() 
                                     if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']])
                images = [f"images/spots/spot_{i}/{img.name}" for img in image_files[:5]]  # Limit to 5 images
        
        transformed_spot = {
            "id": i + 1,
            "name": google_data.get("place_name", f"Spot {i + 1}"),
            "lat": spot.get("latitude", 0),
            "lng": spot.get("longitude", 0),
            "description": spot.get("description", "Beautiful drone location"),
            "category": google_data.get("category", "Nature"),
            "images": images,
            "rating": google_data.get("rating"),
            "address": google_data.get("address", ""),
            "notes": "Check local rules"
        }
        simple.append(transformed_spot)
    
    # Write output
    print(f"Writing {len(simple)} spots to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simple, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully transformed {len(simple)} spots")
    return len(simple)

if __name__ == '__main__':
    transform_spots()

