### Local Setup Guide for DroneMY Explorer MVP (Next.js + Supabase + Leaflet)

This guide gets your MVP running **100% locally** on your machine in under 1 hour. No cloud costs, perfect for development and testing before deploying to Vercel.

We'll use:
- **Next.js 14** (App Router) – full-stack React
- **Supabase** (local self-hosted via Docker) – for auth, database, and storage (avoids cloud for now)
- **Leaflet** – interactive map
- Your existing 97 spots + 259MB images

#### Step 1: Prerequisites
Install these on your machine (December 2025):
- **Node.js 20+** (download from nodejs.org)
- **Git**
- **Docker Desktop** (for local Supabase – includes Docker Compose)
- Optional: VS Code + extensions (ESLint, Prettier, Tailwind)

#### Step 2: Clone & Setup Project Structure
```bash
mkdir drone-my-mvp && cd drone-my-mvp
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
# Choose: Yes to all defaults
```

Your folder now:
```
drone-my-mvp/
├── src/
│   ├── app/
│   ├── components/
│   └── lib/
├── public/
├── data/               # We'll add this
└── images/             # We'll add this (your scraped images)
```

#### Step 3: Add Your Existing Data Locally
1. Create folders:
```bash
mkdir public/images/spots
mkdir data
```

2. Copy your existing assets:
- Copy all images from `scraped_data/images/` → `public/images/spots/` (keep folder structure: spot_0/, spot_1/, etc.)
- Copy `enriched_spots.json` → `data/spots.json`

3. Simplify spots.json for MVP (create `data/spots-simple.json`):
```json
[
  {
    "id": 1,
    "name": "Tanah Rata Lookout",
    "lat": 4.4711,
    "lng": 101.3808,
    "description": "Open highland view, great for sunrise drone shots",
    "category": "Mountain",
    "images": ["spot_0/img1.jpg", "spot_0/img2.jpg"],
    "notes": "Windy in afternoons"
  }
  // Add ~97 spots like this (script below helps)
]
```

Quick script to generate (run in Python):
```python
import json
with open('data/enriched_spots.json') as f:
    data = json.load(f)
simple = []
for i, spot in enumerate(data):
    simple.append({
        "id": i+1,
        "name": spot.get("name", f"Spot {i}"),
        "lat": spot["location"]["lat"],
        "lng": spot["location"]["lng"],
        "description": spot.get("description", "Beautiful drone location"),
        "category": spot.get("category", "Nature"),
        "images": [f"spots/spot_{i}/image1.jpg"],  # adjust paths
        "notes": "Check local rules"
    })
json.dump(simple, open('data/spots-simple.json', 'w'), indent=2)
```

#### Step 4: Set Up Local Supabase (Auth + DB + Storage)
Run local Supabase stack:
```bash
# In project root
npx supabase init
npx supabase start
```

It will:
- Start PostgreSQL, Studio (at http://localhost:54323), etc.
- Output connection details like:
  ```
  API URL: http://localhost:54321
  DB URL: postgresql://postgres:postgres@localhost:54322/postgres
  Studio URL: http://localhost:54323
  anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6...
  service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6...
  ```

Save these – we'll use them.

#### Step 5: Install Dependencies
```bash
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs react-leaflet leaflet zustand
```

Add Leaflet CSS in `src/app/layout.tsx`:
```tsx
import 'leaflet/dist/leaflet.css';
```

#### Step 6: Environment Variables
Create `.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6... (from supabase start)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6... (for server actions)
```

#### Step 7: Create Database Tables (via Supabase Studio)
Go to http://localhost:54323 → Table Editor → New Table:
- `profiles` (id uuid PK, full_name text, premium boolean default false)
- `favorites` (id uuid PK, user_id uuid, spot_id int)

Enable Row Level Security if desired.

#### Step 8: Core MVP Code Examples

**lib/supabase.ts**
```ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

**components/Map.tsx** (basic)
```tsx
'use client';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import spots from '@/data/spots-simple.json';

export default function DroneMap() {
  return (
    <MapContainer center={[4.2105, 101.9758]} zoom={6} style={{ height: '100vh' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {spots.map(spot => (
        <Marker key={spot.id} position={[spot.lat, spot.lng]}>
          <Popup>
            <h3>{spot.name}</h3>
            <p>{spot.description}</p>
            {/* Image gallery */}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
```

**app/page.tsx**
```tsx
import DroneMap from '@/components/Map';

export default function Home() {
  return <DroneMap />;
}
```

#### Step 9: Run Locally
```bash
# Terminal 1: Supabase
npx supabase start

# Terminal 2: Next.js
npm run dev
```

Open http://localhost:3000 → Your map with 97 spots!

#### Next: Add Premium, Weather, NFZ
Once base works:
- Add auth (Supabase examples)
- Add Open-Meteo weather fetch
- Add manual NFZ GeoJSON overlay

You now have a **fully local, production-like MVP** using your real data.
@MVP 