# Coordinate Correction Scripts

These scripts correct coordinates for all locations by scraping Google Maps directly, avoiding the need for paid Google Maps API.

Two versions are available:
1. **Python version** - Uses Playwright (browser automation)
2. **Node.js version** - Uses Crawlee + Puppeteer (as requested)

## Option 1: Python Version (Playwright)

### Setup

```bash
cd MVP
pip install -r requirements_scraping.txt
playwright install chromium
```

### Run

```bash
python correct_coordinates_crawlee.py
```

## Option 2: Node.js Version (Crawlee + Puppeteer)

### Setup

```bash
cd MVP
npm install
```

This will install `crawlee` and `puppeteer` as dependencies.

### Run

```bash
npm run correct-coords
# OR
node correct_coordinates_crawlee.js
```

## How It Works

1. **Loads** `scraped_data/enriched_spots.json`
2. **Creates backup** before making changes
3. **For each location:**
   - Searches Google Maps using place name + address
   - Extracts coordinates from the Google Maps URL
   - Compares with existing coordinates
   - Updates if difference > 5km
4. **Saves** corrected data to:
   - `scraped_data/enriched_spots_corrected.json` (new file)
   - `scraped_data/enriched_spots.json` (updated original)

## Features

- ✅ **Free** - No API costs
- ✅ **Automatic** - Processes all locations
- ✅ **Safe** - Creates backup before changes
- ✅ **Smart** - Only updates coordinates that differ significantly (>5km)
- ✅ **Rate Limited** - 2 second delay between requests to avoid blocking

## Configuration

Edit the script to adjust:

- `DISTANCE_THRESHOLD_KM = 5.0` - Minimum distance difference to trigger update
- `REQUEST_DELAY = 2.0` - Delay between requests (seconds)

## Troubleshooting

### Python Version - Playwright Installation Issues

If you get import errors:
```bash
pip install playwright --upgrade
playwright install chromium
```

### Node.js Version - Crawlee/Puppeteer Issues

If you get module errors:
```bash
npm install crawlee puppeteer --save
```

### Browser Launch Issues

Both scripts run in headless mode by default. If you need to debug:
- **Python**: Change `headless=True` to `headless=False` in the script
- **Node.js**: Change `headless: true` to `headless: false` in the script
- You'll see the browser window open

### Rate Limiting

If Google Maps blocks requests:
- Increase `REQUEST_DELAY` to 3-5 seconds (or 3000-5000ms for Node.js)
- Run the script in smaller batches
- Use a VPN if needed
- Add random delays between requests

## After Running

1. Review `enriched_spots_corrected.json` to verify corrections
2. If satisfied, the original file has been updated
3. Run `fix_spots_mapping_v2.py` to regenerate `spots-simple.json`:

```bash
python fix_spots_mapping_v2.py
```

## Example Output

```
================================================================================
CORRECTING COORDINATES USING GOOGLE MAPS SCRAPING (CRAWLEE/PLAYWRIGHT)
================================================================================

📂 Loading data from: scraped_data/enriched_spots.json
✅ Loaded 97 locations

💾 Creating backup: scraped_data/enriched_spots.json.backup
✅ Backup created

🔍 Processing locations (threshold: 5.0km)...
--------------------------------------------------------------------------------

[1/97] Merdeka Square
  ✓ Coordinates OK (difference: 0.12 km)

[2/97] Hiking Area @ Penang National Park
  📍 Current: (4.681557, 102.055927)
  ✅ Corrected: (5.471944, 100.201389)
  📏 Distance: 234.56 km

...

SUMMARY
================================================================================
Total locations: 97
✅ Corrected: 12
✓ Unchanged: 83
⚠️  Errors: 2
```

