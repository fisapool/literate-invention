/**
 * Correct coordinates for all locations using Crawlee + Puppeteer to scrape Google Maps
 * This script scrapes coordinates directly from Google Maps without using the paid API.
 */

const { PuppeteerCrawler } = require('crawlee');
const fs = require('fs').promises;
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const ENRICHED_FILE = path.join(PROJECT_ROOT, 'scraped_data', 'enriched_spots.json');
const BACKUP_FILE = path.join(PROJECT_ROOT, 'scraped_data', 'enriched_spots.json.backup');
const CORRECTED_FILE = path.join(PROJECT_ROOT, 'scraped_data', 'enriched_spots_corrected.json');

// Distance threshold in kilometers
const DISTANCE_THRESHOLD_KM = 5.0;
const REQUEST_DELAY = 500; // 0.5 seconds (reduced for speed)
const MAX_CONCURRENCY = 3; // Process 3 locations in parallel
const PAGE_WAIT_TIME = 1500; // 1.5 seconds (reduced from 3s)

/**
 * Calculate distance between two coordinates using Haversine formula
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
}

function toRad(degrees) {
    return degrees * (Math.PI / 180);
}

/**
 * Parse coordinate string in DMS format (e.g., "2°28'47.0"N 103°15'48.5"E")
 */
function parseDMSCoordinates(coordString) {
    // Pattern: degrees°minutes'seconds"direction (e.g., 2°28'47.0"N 103°15'48.5"E)
    const dmsPattern = /(\d+)°(\d+)'([\d.]+)"([NS])\s+(\d+)°(\d+)'([\d.]+)"([EW])/;
    const match = coordString.match(dmsPattern);
    
    if (match) {
        const latDeg = parseFloat(match[1]);
        const latMin = parseFloat(match[2]);
        const latSec = parseFloat(match[3]);
        const latDir = match[4];
        
        const lngDeg = parseFloat(match[5]);
        const lngMin = parseFloat(match[6]);
        const lngSec = parseFloat(match[7]);
        const lngDir = match[8];
        
        // Convert DMS to decimal
        let lat = latDeg + latMin / 60 + latSec / 3600;
        let lng = lngDeg + lngMin / 60 + lngSec / 3600;
        
        // Apply direction
        if (latDir === 'S') lat = -lat;
        if (lngDir === 'W') lng = -lng;
        
        // Validate coordinates (Malaysia is roughly 0-7°N, 99-120°E)
        if (lat >= 0 && lat <= 10 && lng >= 99 && lng <= 120) {
            return [lat, lng];
        }
    }
    
    return null;
}

/**
 * Extract coordinates from Google Maps URL
 */
function extractCoordsFromUrl(url) {
    // Pattern: @lat,lng or /@lat,lng,zoom
    const patterns = [
        /@(-?\d+\.?\d*),(-?\d+\.?\d*)/,  // @lat,lng
        /\/@(-?\d+\.?\d*),(-?\d+\.?\d*)/,  // /@lat,lng
        /!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/,  // !3dlat!4dlng (old format)
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            try {
                const lat = parseFloat(match[1]);
                const lng = parseFloat(match[2]);
                // Validate coordinates (Malaysia is roughly 0-7°N, 99-120°E)
                if (lat >= 0 && lat <= 10 && lng >= 99 && lng <= 120) {
                    return [lat, lng];
                }
            } catch (e) {
                continue;
            }
        }
    }
    
    return null;
}

/**
 * Scrape coordinates from Google Maps using Crawlee PuppeteerCrawler
 * Optimized version with batch processing
 */
async function scrapeGoogleMapsCoordsBatch(requests) {
    const results = new Map();
    
    const crawler = new PuppeteerCrawler({
        launchContext: {
            launchOptions: {
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox'], // Faster startup
            },
        },
        maxConcurrency: MAX_CONCURRENCY,
        requestHandler: async ({ request, page }) => {
            try {
                // Wait for initial page load
                await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                let currentUrl = page.url();
                
                // Debug: Log URL for first few requests
                if (request.userData.id <= 3) {
                    console.log(`    🔍 Initial URL: ${currentUrl.substring(0, 100)}...`);
                }
                
                // Check if we're on a search results page (not a specific location)
                // Google Maps search results have "/search/" in URL but no coordinates
                const isSearchResultsPage = currentUrl.includes('/search/') && !extractCoordsFromUrl(currentUrl);
                
                if (isSearchResultsPage) {
                    // Click on the first search result to get to the location page
                    try {
                        // Try multiple selectors for the first result
                        const firstResultSelectors = [
                            'a[href*="/place/"]',
                            'div[role="main"] a[data-value*="@"]',
                            'div[jsaction*="click"] a[href*="/place/"]',
                            'div[data-result-index="0"] a',
                            'div.m6QErb a[href*="/place/"]'
                        ];
                        
                        let clicked = false;
                        for (const selector of firstResultSelectors) {
                            try {
                                await page.waitForSelector(selector, { timeout: 3000 });
                                const firstResult = await page.$(selector);
                                if (firstResult) {
                                    await firstResult.click();
                                    clicked = true;
                                    break;
                                }
                            } catch (e) {
                                continue;
                            }
                        }
                        
                        if (clicked) {
                            // Wait for navigation to location page
                            await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }).catch(() => {});
                            await new Promise(resolve => setTimeout(resolve, 2000));
                            currentUrl = page.url();
                            
                            if (request.userData.id <= 3) {
                                console.log(`    ✅ Clicked first result, new URL: ${currentUrl.substring(0, 100)}...`);
                            }
                        }
                    } catch (e) {
                        if (request.userData.id <= 3) {
                            console.log(`    ⚠️  Could not click first result: ${e.message}`);
                        }
                    }
                }
                
                // Try to extract coordinates from URL
                let coords = extractCoordsFromUrl(currentUrl);
                
                if (coords) {
                    if (request.userData.id <= 3) {
                        console.log(`    ✅ Found coords in URL: ${coords[0]}, ${coords[1]}`);
                    }
                    results.set(request.userData.id, coords);
                    return;
                }
                
                // Try alternative: Look for data in the page HTML
                try {
                    // Wait a bit more for map to fully load
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Get page content to search for coordinates
                    const pageContent = await page.content();
                    
                    // Look for coordinates in the page HTML (Google Maps embeds them in various formats)
                    const coordPatterns = [
                        /@(-?\d+\.?\d*),(-?\d+\.?\d*)/g,
                        /!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/g,
                        /"lat":\s*(-?\d+\.?\d*).*?"lng":\s*(-?\d+\.?\d*)/g,
                        /\[(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\]/g,
                        /center.*?\[(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\]/g,
                        /data-value="[^"]*@(-?\d+\.?\d*),(-?\d+\.?\d*)/g
                    ];
                    
                    for (const pattern of coordPatterns) {
                        const matches = [...pageContent.matchAll(pattern)];
                        for (const match of matches) {
                            const lat = parseFloat(match[1]);
                            const lng = parseFloat(match[2]);
                            if (lat >= 0 && lat <= 10 && lng >= 99 && lng <= 120) {
                                coords = [lat, lng];
                                if (request.userData.id <= 3) {
                                    console.log(`    ✅ Found coords in HTML: ${lat}, ${lng}`);
                                }
                                break;
                            }
                        }
                        if (coords) break;
                    }
                    
                    if (coords) {
                        results.set(request.userData.id, coords);
                        return;
                    }
                    
                } catch (e) {
                    // Ignore extraction errors
                }
                
                // If still no coords, log for debugging
                if (request.userData.id <= 3) {
                    console.log(`    ⚠️  No coordinates found in URL or page content`);
                }
                
                results.set(request.userData.id, null);
            } catch (error) {
                console.log(`    ⚠️  Error scraping ${request.userData.placeName || 'location'}: ${error.message}`);
                results.set(request.userData.id, null);
            }
        },
    });
    
    // Run crawler for all requests
    await crawler.run(requests);
    
    return results;
}

async function scrapeGoogleMapsCoords(placeName, address = '') {
    const query = placeName || address;
    if (!query) {
        return null;
    }
    
    // Add "Malaysia" to help with search accuracy
    const searchQuery = query.includes('Malaysia') || address.includes('Malaysia') 
        ? query 
        : `${query}, Malaysia`;
    
    const searchUrl = `https://www.google.com/maps/search/${encodeURIComponent(searchQuery)}`;
    
    const request = { 
        url: searchUrl, 
        userData: { 
            id: placeName,
            name: placeName,
            result: null 
        } 
    };
    
    const results = await scrapeGoogleMapsCoordsBatch([request]);
    return results.get(placeName) || null;
}

/**
 * Main function to correct coordinates
 */
async function correctCoordinates() {
    console.log('='.repeat(80));
    console.log('CORRECTING COORDINATES USING GOOGLE MAPS SCRAPING (CRAWLEE/PUPPETEER)');
    console.log('='.repeat(80));
    
    // Load enriched spots data
    let enrichedData;
    try {
        const data = await fs.readFile(ENRICHED_FILE, 'utf-8');
        enrichedData = JSON.parse(data);
        console.log(`\n📂 Loaded ${enrichedData.length} locations from: ${ENRICHED_FILE}`);
    } catch (error) {
        console.error(`❌ Error loading file: ${error.message}`);
        return;
    }
    
    // Create backup
    console.log(`\n💾 Creating backup: ${BACKUP_FILE}`);
    await fs.writeFile(BACKUP_FILE, JSON.stringify(enrichedData, null, 2), 'utf-8');
    console.log('✅ Backup created');
    
    // Process each location
    let correctedCount = 0;
    let unchangedCount = 0;
    let errorCount = 0;
    const corrections = [];
    
    console.log(`\n🔍 Processing locations (threshold: ${DISTANCE_THRESHOLD_KM}km, concurrency: ${MAX_CONCURRENCY})...`);
    console.log('-'.repeat(80));
    
    // Filter locations that need processing
    const locationsToProcess = enrichedData
        .map((location, idx) => {
            const googleData = location.google_maps_data || {};
            const placeName = googleData.place_name || '';
            const address = googleData.address || '';
            const currentLat = location.latitude || 0;
            const currentLng = location.longitude || 0;
            
            // Skip if no place name or invalid coordinates
            if (!placeName || currentLat === 0 || currentLng === 0) {
                return null;
            }
            
            return { idx, location, placeName, address, currentLat, currentLng };
        })
        .filter(item => item !== null);
    
    console.log(`📊 Processing ${locationsToProcess.length} locations (skipping ${enrichedData.length - locationsToProcess.length} with missing data)\n`);
    
    // Process in batches for better performance
    const batchSize = MAX_CONCURRENCY;
    for (let i = 0; i < locationsToProcess.length; i += batchSize) {
        const batch = locationsToProcess.slice(i, i + batchSize);
        
        // Check if place names are already coordinates (DMS format)
        const batchWithCoords = batch.map(({ idx, placeName, address, currentLat, currentLng, location }) => {
            // Check if place name is already in coordinate format
            const dmsCoords = parseDMSCoordinates(placeName);
            if (dmsCoords) {
                return {
                    idx,
                    location,
                    placeName,
                    address,
                    currentLat,
                    currentLng,
                    preParsedCoords: dmsCoords
                };
            }
            return {
                idx,
                location,
                placeName,
                address,
                currentLat,
                currentLng,
                preParsedCoords: null
            };
        });
        
        // Prepare batch requests (only for locations that need scraping)
        const batchRequests = batchWithCoords
            .filter(item => !item.preParsedCoords)
            .map(({ idx, placeName, address, currentLat, currentLng, location }) => {
                const query = placeName || address;
                const searchQuery = query.includes('Malaysia') || address.includes('Malaysia') 
                    ? query 
                    : `${query}, Malaysia`;
                const searchUrl = `https://www.google.com/maps/search/${encodeURIComponent(searchQuery)}`;
                
                return {
                    url: searchUrl,
                    userData: {
                        id: idx,
                        idx,
                        placeName,
                        address,
                        currentLat,
                        currentLng,
                        location
                    }
                };
            });
        
        // Log batch start
        batchWithCoords.forEach(({ idx, placeName, preParsedCoords }) => {
            if (preParsedCoords) {
                console.log(`[${idx + 1}/${enrichedData.length}] ${placeName} (DMS format - parsing directly)`);
            } else {
                console.log(`[${idx + 1}/${enrichedData.length}] ${placeName}`);
            }
        });
        
        // Scrape all in batch (only for non-DMS locations)
        const results = batchRequests.length > 0 
            ? await scrapeGoogleMapsCoordsBatch(batchRequests)
            : new Map();
        
        // Add pre-parsed DMS coordinates to results
        batchWithCoords.forEach(({ idx, preParsedCoords }) => {
            if (preParsedCoords) {
                results.set(idx, preParsedCoords);
            }
        });
        
        // Process results
        for (const { idx, location, placeName, currentLat, currentLng, preParsedCoords } of batchWithCoords) {
            const newCoords = results.get(idx);
            
            if (newCoords) {
                const [newLat, newLng] = newCoords;
                
                // If this was pre-parsed from DMS, show it
                if (preParsedCoords) {
                    console.log(`  ✅ Parsed from DMS: (${newLat.toFixed(6)}, ${newLng.toFixed(6)})`);
                }
                
                const distance = calculateDistance(currentLat, currentLng, newLat, newLng);
                
                if (distance > DISTANCE_THRESHOLD_KM) {
                    console.log(`  📍 Current: (${currentLat.toFixed(6)}, ${currentLng.toFixed(6)})`);
                    console.log(`  ✅ Corrected: (${newLat.toFixed(6)}, ${newLng.toFixed(6)})`);
                    console.log(`  📏 Distance: ${distance.toFixed(2)} km`);
                    
                    // Update coordinates
                    location.latitude = newLat;
                    location.longitude = newLng;
                    correctedCount++;
                    
                    corrections.push({
                        index: idx,
                        name: placeName,
                        oldCoords: [currentLat, currentLng],
                        newCoords: [newLat, newLng],
                        distanceKm: distance
                    });
                } else {
                    console.log(`  ✓ Coordinates OK (difference: ${distance.toFixed(2)} km)`);
                    unchangedCount++;
                }
            } else {
                console.log(`  ⚠️  Could not scrape coordinates, keeping original`);
                errorCount++;
            }
        }
        
        // Progress update
        const processed = Math.min(i + batchSize, locationsToProcess.length);
        console.log(`\n📊 Progress: ${processed}/${locationsToProcess.length} processed (${correctedCount} corrected, ${unchangedCount} OK, ${errorCount} errors)\n`);
        
        // Small delay between batches
        if (i + batchSize < locationsToProcess.length) {
            await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
        }
    }
    
    // Count skipped locations
    unchangedCount += (enrichedData.length - locationsToProcess.length);
    
    // Save corrected data
    console.log(`\n${'='.repeat(80)}`);
    console.log('SUMMARY');
    console.log('='.repeat(80));
    console.log(`Total locations: ${enrichedData.length}`);
    console.log(`✅ Corrected: ${correctedCount}`);
    console.log(`✓ Unchanged: ${unchangedCount}`);
    console.log(`⚠️  Errors: ${errorCount}`);
    
    if (correctedCount > 0) {
        console.log(`\n💾 Saving corrected data to: ${CORRECTED_FILE}`);
        await fs.writeFile(CORRECTED_FILE, JSON.stringify(enrichedData, null, 2), 'utf-8');
        console.log('✅ Corrected data saved');
        
        // Also update the original file
        console.log(`\n💾 Updating original file: ${ENRICHED_FILE}`);
        await fs.writeFile(ENRICHED_FILE, JSON.stringify(enrichedData, null, 2), 'utf-8');
        console.log('✅ Original file updated');
        
        // Show corrections summary
        console.log(`\n📋 Corrections made:`);
        console.log('-'.repeat(80));
        corrections.slice(0, 10).forEach(correction => {
            console.log(`  [${correction.index}] ${correction.name}`);
            console.log(`      Old: ${correction.oldCoords[0].toFixed(6)}, ${correction.oldCoords[1].toFixed(6)}`);
            console.log(`      New: ${correction.newCoords[0].toFixed(6)}, ${correction.newCoords[1].toFixed(6)}`);
            console.log(`      Distance: ${correction.distanceKm.toFixed(2)} km`);
        });
        if (corrections.length > 10) {
            console.log(`  ... and ${corrections.length - 10} more corrections`);
        }
    } else {
        console.log('\n✅ No corrections needed - all coordinates are accurate!');
    }
    
    console.log('='.repeat(80));
    console.log(`\n💡 Next steps:`);
    console.log(`   1. Review the corrected data in: ${CORRECTED_FILE}`);
    console.log(`   2. If satisfied, the original file has been updated`);
    console.log(`   3. Run fix_spots_mapping_v2.py to regenerate spots-simple.json`);
    console.log('='.repeat(80));
}

// Run the script
if (require.main === module) {
    correctCoordinates().catch(console.error);
}

module.exports = { correctCoordinates, scrapeGoogleMapsCoords };

