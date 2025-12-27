#!/usr/bin/env python3
"""
Fix the mapping between spot folders and locations
The issue: spot folders don't match enriched_spots.json indices
Solution: Map based on actual image paths in enriched_spots.json
"""

import json
from pathlib import Path
from collections import defaultdict

MVP_DIR = Path(__file__).parent
PROJECT_ROOT = MVP_DIR.parent
SPOTS_DIR = MVP_DIR / 'public' / 'images' / 'spots'
DATA_DIR = MVP_DIR / 'data'
ENRICHED_FILE = PROJECT_ROOT / 'scraped_data' / 'enriched_spots.json'
OUTPUT_FILE = DATA_DIR / 'spots-simple.json'

def get_spot_folder_from_path(path_str):
    """Extract spot folder name from image path."""
    # Handle different path formats
    path = path_str.replace('\\', '/')
    
    # Remove common prefixes
    prefixes = ['images/', 'scraped_data/images/', 'images\\', 'scraped_data\\images\\']
    for prefix in prefixes:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    
    # Look for spot_X pattern
    if 'spot_' in path:
        parts = path.split('/')
        for part in parts:
            if part.startswith('spot_'):
                return part
    return None

def build_location_to_spot_mapping():
    """Build mapping from location index to spot folder based on image paths."""
    if not ENRICHED_FILE.exists():
        print(f"Error: {ENRICHED_FILE} not found!")
        return {}
    
    with open(ENRICHED_FILE, 'r', encoding='utf-8') as f:
        enriched_data = json.load(f)
    
    # Map: location_index -> spot_folder
    location_to_spot = {}
    # Also track: spot_folder -> [location_indices] (in case of conflicts)
    spot_to_locations = defaultdict(list)
    
    for loc_idx, location in enumerate(enriched_data):
        google_data = location.get('google_maps_data', {})
        images = google_data.get('images', [])
        
        # Find spot folder from images
        spot_folders_found = set()
        for img in images:
            local_path = img.get('local_path', '')
            if local_path:
                spot_folder = get_spot_folder_from_path(local_path)
                if spot_folder:
                    spot_folders_found.add(spot_folder)
        
        # If we found spot folders, map this location to the most common one
        if spot_folders_found:
            # Count occurrences
            spot_counts = {}
            for img in images:
                local_path = img.get('local_path', '')
                if local_path:
                    spot_folder = get_spot_folder_from_path(local_path)
                    if spot_folder:
                        spot_counts[spot_folder] = spot_counts.get(spot_folder, 0) + 1
            
            if spot_counts:
                # Use the most common spot folder
                most_common_spot = max(spot_counts.items(), key=lambda x: x[1])[0]
                location_to_spot[loc_idx] = most_common_spot
                spot_to_locations[most_common_spot].append(loc_idx)
    
    return location_to_spot, spot_to_locations

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
    print("FIXING SPOTS JSON - CORRECTING LOCATION-TO-SPOT MAPPING")
    print("="*80)
    
    # Build correct mapping
    location_to_spot, spot_to_locations = build_location_to_spot_mapping()
    print(f"\nBuilt mapping: {len(location_to_spot)} locations mapped to spots")
    
    # Get existing images
    existing_images = get_existing_images()
    print(f"Found {len(existing_images)} spot folders with images")
    
    # Load enriched data
    if not ENRICHED_FILE.exists():
        print(f"Error: {ENRICHED_FILE} not found!")
        return
    
    with open(ENRICHED_FILE, 'r', encoding='utf-8') as f:
        enriched_data = json.load(f)
    
    print(f"Loaded {len(enriched_data)} locations from enriched_spots.json")
    
    # Build reverse mapping: spot_folder -> location_index
    spot_to_location = {}
    
    # First, use the mapping from enriched data (most accurate)
    for loc_idx, spot_folder in location_to_spot.items():
        if spot_folder in existing_images:  # Only map spots that have images
            # If multiple locations map to same spot, use the first one
            if spot_folder not in spot_to_location:
                spot_to_location[spot_folder] = loc_idx
    
    # Then, handle spots that exist but aren't in the mapping
    # Only use folder index as fallback if the location doesn't already have a spot mapped
    # AND the location's images don't point to a different spot
    mapped_locations = set(spot_to_location.values())
    for spot_folder in existing_images.keys():
        if spot_folder not in spot_to_location:
            # Try to extract index from folder name
            try:
                spot_idx = int(spot_folder.replace('spot_', ''))
                # Only use as fallback if:
                # 1. Location exists in enriched_data
                # 2. Location doesn't already have a spot mapped to it
                # 3. Location's images don't point to a different spot (check this!)
                if spot_idx < len(enriched_data) and spot_idx not in mapped_locations:
                    # Check if this location's images actually point to this spot
                    location = enriched_data[spot_idx]
                    location_images = location.get('google_maps_data', {}).get('images', [])
                    location_spots = {get_spot_folder_from_path(img.get('local_path', '')) 
                                     for img in location_images if img.get('local_path')}
                    # Only use fallback if location has no images OR images point to this spot
                    if not location_spots or spot_folder in location_spots:
                        spot_to_location[spot_folder] = spot_idx
                        mapped_locations.add(spot_idx)
            except ValueError:
                pass
    
    print(f"Mapped {len(spot_to_location)} spots to locations")
    
    # Debug: Show the actual mappings
    print("\nSample location-to-spot mappings:")
    for loc_idx, spot_folder in list(location_to_spot.items())[:10]:
        loc_name = enriched_data[loc_idx].get('google_maps_data', {}).get('place_name', f'Location {loc_idx}')
        print(f"  Location {loc_idx} ({loc_name}) -> {spot_folder}")
    
    print("\nSample spot-to-location mappings:")
    for spot_folder, loc_idx in list(spot_to_location.items())[:10]:
        loc_name = enriched_data[loc_idx].get('google_maps_data', {}).get('place_name', f'Location {loc_idx}')
        print(f"  {spot_folder} -> Location {loc_idx} ({loc_name})")
    
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
                "id": len(spots) + 1,  # Sequential IDs
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
            # No location data available - use fallback
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

