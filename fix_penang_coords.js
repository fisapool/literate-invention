/**
 * Quick fix script to correct Penang National Park coordinates
 */

const fs = require('fs').promises;
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const ENRICHED_FILE = path.join(PROJECT_ROOT, 'scraped_data', 'enriched_spots.json');

// Correct coordinates for Penang National Park (from official source)
// 5°23'36.8"N, 100°12'22.6"E
const CORRECT_PENANG_COORDS = {
    lat: 5.393556,  // 5°23'36.8"N
    lng: 100.206278 // 100°12'22.6"E
};

async function fixPenangCoords() {
    console.log('='.repeat(80));
    console.log('FIXING PENANG NATIONAL PARK COORDINATES');
    console.log('='.repeat(80));
    
    // Load enriched spots data
    const data = await fs.readFile(ENRICHED_FILE, 'utf-8');
    const enrichedData = JSON.parse(data);
    
    console.log(`\n📂 Loaded ${enrichedData.length} locations`);
    
    // Find and fix Penang National Park
    let found = false;
    for (let i = 0; i < enrichedData.length; i++) {
        const location = enrichedData[i];
        const googleData = location.google_maps_data || {};
        const placeName = googleData.place_name || '';
        
        if (placeName.includes('Penang National Park') || placeName.includes('Taman Negara Pulau Pinang')) {
            const oldLat = location.latitude;
            const oldLng = location.longitude;
            
            console.log(`\n📍 Found: ${placeName}`);
            console.log(`   Old coordinates: ${oldLat}, ${oldLng}`);
            console.log(`   New coordinates: ${CORRECT_PENANG_COORDS.lat}, ${CORRECT_PENANG_COORDS.lng}`);
            
            location.latitude = CORRECT_PENANG_COORDS.lat;
            location.longitude = CORRECT_PENANG_COORDS.lng;
            
            found = true;
            break;
        }
    }
    
    if (found) {
        // Save corrected data
        await fs.writeFile(ENRICHED_FILE, JSON.stringify(enrichedData, null, 2), 'utf-8');
        console.log('\n✅ Coordinates updated!');
        console.log('\n💡 Next step: Run fix_spots_mapping_v2.py to regenerate spots-simple.json');
    } else {
        console.log('\n⚠️  Penang National Park location not found!');
    }
    
    console.log('='.repeat(80));
}

fixPenangCoords().catch(console.error);

