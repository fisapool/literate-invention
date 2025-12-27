#!/usr/bin/env python3
"""
Correct coordinates for all locations using Crawlee + Puppeteer to scrape Google Maps
This script scrapes coordinates directly from Google Maps without using the paid API.
"""

import json
import time
import re
import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple
import math

# Note: This script uses Playwright (via Crawlee) which is more reliable than Puppeteer
# For Puppeteer, you'd need to use crawlee-puppeteer-crawler, but Playwright is recommended

MVP_DIR = Path(__file__).parent
PROJECT_ROOT = MVP_DIR.parent
ENRICHED_FILE = PROJECT_ROOT / 'scraped_data' / 'enriched_spots.json'
BACKUP_FILE = PROJECT_ROOT / 'scraped_data' / 'enriched_spots.json.backup'
CORRECTED_FILE = PROJECT_ROOT / 'scraped_data' / 'enriched_spots_corrected.json'

# Distance threshold in kilometers - if coordinates differ by more than this, update them
DISTANCE_THRESHOLD_KM = 5.0  # 5km threshold

# Delay between requests to avoid being blocked
REQUEST_DELAY = 2.0  # 2 seconds between requests


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers using Haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def extract_coords_from_url(url: str) -> Optional[Tuple[float, float]]:
    """Extract coordinates from Google Maps URL."""
    # Pattern: @lat,lng or /@lat,lng,zoom
    patterns = [
        r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',  # @lat,lng
        r'/@(-?\d+\.?\d*),(-?\d+\.?\d*)',  # /@lat,lng
        r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',  # !3dlat!4dlng (old format)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                # Validate coordinates (Malaysia is roughly 0-7°N, 99-120°E)
                if 0 <= lat <= 10 and 99 <= lng <= 120:
                    return (lat, lng)
            except ValueError:
                continue
    
    return None


async def scrape_google_maps_coords(place_name: str, address: str = "") -> Optional[Tuple[float, float]]:
    """
    Scrape coordinates from Google Maps using Playwright (via Crawlee).
    Returns (latitude, longitude) or None if not found.
    """
    try:
        from playwright.async_api import async_playwright
        
        # Build search query
        query = place_name if place_name else address
        if not query:
            return None
        
        # Add "Malaysia" to help with search accuracy
        if "Malaysia" not in query and "Malaysia" not in address:
            query = f"{query}, Malaysia"
        
        async with async_playwright() as p:
            # Launch browser (headless by default)
            browser = await p.chromium.launch(headless=True)
            context = await browser.create_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navigate to Google Maps search
                search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                await page.goto(search_url, wait_until='networkidle', timeout=30000)
                
                # Wait for map to load
                await page.wait_for_timeout(3000)
                
                # Try to get coordinates from URL (most reliable)
                current_url = page.url
                coords = extract_coords_from_url(current_url)
                
                if coords:
                    await browser.close()
                    return coords
                
                # Alternative: Try to extract from page content
                # Look for data attributes or script tags with coordinates
                try:
                    # Check if there's a data attribute with coordinates
                    coords_element = await page.query_selector('[data-value*="@"]')
                    if coords_element:
                        data_value = await coords_element.get_attribute('data-value')
                        if data_value:
                            coords = extract_coords_from_url(data_value)
                            if coords:
                                await browser.close()
                                return coords
                except:
                    pass
                
                # Try to get from page title or meta tags
                try:
                    # Sometimes coordinates are in the page title
                    title = await page.title()
                    coords = extract_coords_from_url(title)
                    if coords:
                        await browser.close()
                        return coords
                except:
                    pass
                
                await browser.close()
                return None
                
            except Exception as e:
                print(f"    ⚠️  Error scraping: {str(e)}")
                await browser.close()
                return None
                
    except ImportError:
        print("\n❌ ERROR: Playwright not installed!")
        print("\nTo install:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return None
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
        return None


def correct_coordinates():
    """Main function to correct coordinates for all locations."""
    print("="*80)
    print("CORRECTING COORDINATES USING GOOGLE MAPS SCRAPING (CRAWLEE/PLAYWRIGHT)")
    print("="*80)
    
    # Load enriched spots data
    if not ENRICHED_FILE.exists():
        print(f"❌ Error: {ENRICHED_FILE} not found!")
        return
    
    print(f"\n📂 Loading data from: {ENRICHED_FILE}")
    with open(ENRICHED_FILE, 'r', encoding='utf-8') as f:
        enriched_data = json.load(f)
    
    print(f"✅ Loaded {len(enriched_data)} locations")
    
    # Create backup
    print(f"\n💾 Creating backup: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(enriched_data, f, indent=2, ensure_ascii=False)
    print("✅ Backup created")
    
    # Process each location
    corrected_count = 0
    unchanged_count = 0
    error_count = 0
    corrections = []
    
    print(f"\n🔍 Processing locations (threshold: {DISTANCE_THRESHOLD_KM}km)...")
    print("-" * 80)
    
    async def process_locations():
        nonlocal corrected_count, unchanged_count, error_count, corrections
        
        for idx, location in enumerate(enriched_data):
            google_data = location.get('google_maps_data', {})
            place_name = google_data.get('place_name', '')
            address = google_data.get('address', '')
            current_lat = location.get('latitude', 0)
            current_lng = location.get('longitude', 0)
            
            # Skip if no place name
            if not place_name:
                unchanged_count += 1
                continue
            
            # Scrape coordinates
            print(f"\n[{idx + 1}/{len(enriched_data)}] {place_name}")
            new_coords = await scrape_google_maps_coords(place_name, address)
            
            # Rate limiting
            await asyncio.sleep(REQUEST_DELAY)
            
            if new_coords:
                new_lat, new_lng = new_coords
                distance = calculate_distance(current_lat, current_lng, new_lat, new_lng)
                
                if distance > DISTANCE_THRESHOLD_KM:
                    print(f"  📍 Current: ({current_lat:.6f}, {current_lng:.6f})")
                    print(f"  ✅ Corrected: ({new_lat:.6f}, {new_lng:.6f})")
                    print(f"  📏 Distance: {distance:.2f} km")
                    
                    # Update coordinates
                    location['latitude'] = new_lat
                    location['longitude'] = new_lng
                    corrected_count += 1
                    
                    corrections.append({
                        'index': idx,
                        'name': place_name,
                        'old_coords': (current_lat, current_lng),
                        'new_coords': (new_lat, new_lng),
                        'distance_km': distance
                    })
                else:
                    print(f"  ✓ Coordinates OK (difference: {distance:.2f} km)")
                    unchanged_count += 1
            else:
                print(f"  ⚠️  Could not scrape coordinates, keeping original")
                error_count += 1
    
    # Run async processing
    asyncio.run(process_locations())
    
    # Save corrected data
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total locations: {len(enriched_data)}")
    print(f"✅ Corrected: {corrected_count}")
    print(f"✓ Unchanged: {unchanged_count}")
    print(f"⚠️  Errors: {error_count}")
    
    if corrected_count > 0:
        print(f"\n💾 Saving corrected data to: {CORRECTED_FILE}")
        with open(CORRECTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        print("✅ Corrected data saved")
        
        # Also update the original file
        print(f"\n💾 Updating original file: {ENRICHED_FILE}")
        with open(ENRICHED_FILE, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        print("✅ Original file updated")
        
        # Show corrections summary
        print(f"\n📋 Corrections made:")
        print("-" * 80)
        for correction in corrections[:10]:  # Show first 10
            print(f"  [{correction['index']}] {correction['name']}")
            print(f"      Old: {correction['old_coords'][0]:.6f}, {correction['old_coords'][1]:.6f}")
            print(f"      New: {correction['new_coords'][0]:.6f}, {correction['new_coords'][1]:.6f}")
            print(f"      Distance: {correction['distance_km']:.2f} km")
        if len(corrections) > 10:
            print(f"  ... and {len(corrections) - 10} more corrections")
    else:
        print("\n✅ No corrections needed - all coordinates are accurate!")
    
    print("="*80)
    print(f"\n💡 Next steps:")
    print(f"   1. Review the corrected data in: {CORRECTED_FILE}")
    print(f"   2. If satisfied, the original file has been updated")
    print(f"   3. Run fix_spots_mapping_v2.py to regenerate spots-simple.json")
    print("="*80)


if __name__ == '__main__':
    correct_coordinates()

