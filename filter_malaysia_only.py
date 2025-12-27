#!/usr/bin/env python3
"""
Filter spots-simple.json to only include Malaysia locations
Malaysia coordinates: 
- Latitude: 0.8°N to 7.4°N
- Longitude: 99.6°E to 119.3°E
"""

import json
from pathlib import Path

MVP_DIR = Path(__file__).parent
DATA_DIR = MVP_DIR / 'data'
INPUT_FILE = DATA_DIR / 'spots-simple.json'
OUTPUT_FILE = DATA_DIR / 'spots-simple.json'

# Malaysia boundaries
MALAYSIA_LAT_MIN = 0.8
MALAYSIA_LAT_MAX = 7.4
MALAYSIA_LNG_MIN = 99.6
MALAYSIA_LNG_MAX = 119.3

def is_malaysia_location(lat, lng, name="", description="", address=""):
    """Check if coordinates are within Malaysia boundaries and not Singapore."""
    if lat == 0 and lng == 0:
        return False  # Invalid coordinates
    
    # Check for Singapore locations by name/description/address
    text = f"{name} {description} {address}".lower()
    if "singapore" in text or "pulau ubin" in text:
        return False
    
    # Check coordinates are within Malaysia boundaries
    return (MALAYSIA_LAT_MIN <= lat <= MALAYSIA_LAT_MAX and 
            MALAYSIA_LNG_MIN <= lng <= MALAYSIA_LNG_MAX)

def filter_malaysia_spots():
    """Filter spots to only include Malaysia locations."""
    print("="*80)
    print("FILTERING SPOTS - MALAYSIA ONLY")
    print("="*80)
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found!")
        return
    
    # Load current spots
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        spots = json.load(f)
    
    print(f"\nLoaded {len(spots)} spots")
    
    # Filter to Malaysia only
    malaysia_spots = []
    removed_count = 0
    
    for spot in spots:
        lat = spot.get('lat', 0)
        lng = spot.get('lng', 0)
        name = spot.get('name', '')
        description = spot.get('description', '')
        address = spot.get('address', '')
        
        if is_malaysia_location(lat, lng, name, description, address):
            malaysia_spots.append(spot)
        else:
            removed_count += 1
            reason = "Invalid coords" if lat == 0 and lng == 0 else "Outside Malaysia/Singapore"
            print(f"  Removed: {name} ({lat}, {lng}) - {reason}")
    
    # Re-number IDs sequentially
    for i, spot in enumerate(malaysia_spots):
        spot['id'] = i + 1
    
    # Save filtered spots
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(malaysia_spots, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Original spots: {len(spots)}")
    print(f"Malaysia spots: {len(malaysia_spots)}")
    print(f"Removed: {removed_count}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("="*80)
    
    # Show some examples
    print("\nSample Malaysia spots:")
    for spot in malaysia_spots[:5]:
        print(f"  {spot['id']}: {spot['name']} ({spot['lat']}, {spot['lng']})")

if __name__ == '__main__':
    filter_malaysia_spots()

