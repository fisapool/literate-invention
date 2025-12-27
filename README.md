# DroneMY Explorer MVP

A Next.js 14 application for discovering and exploring drone photography locations in Malaysia. Built with local Supabase, Leaflet maps, and your existing scraped data.

## Features

- Interactive map with 15+ drone spots across Malaysia
- Spot details with images, ratings, and descriptions
- Local Supabase setup for authentication and favorites (future)
- Fully local development environment

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js 20+** ([download](https://nodejs.org/))
- **Git**
- **Docker Desktop** (for local Supabase)
- **Python 3** (for data transformation script)

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Set Up Local Supabase

Start the local Supabase stack:

```bash
npx supabase start
```

This will:
- Start PostgreSQL, Supabase Studio, and other services
- Output connection details including:
  - API URL: `http://localhost:54321`
  - DB URL: `postgresql://postgres:postgres@localhost:54322/postgres`
  - Studio URL: `http://localhost:54323`
  - Anon key and service_role key

### 3. Configure Environment Variables

Create a `.env.local` file in the project root:

```env
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key_from_supabase_start
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_from_supabase_start
```

Replace the placeholder values with the actual keys from step 2.

### 4. Set Up Database Tables

The database migrations are already created in `supabase/migrations/`. They will run automatically when you start Supabase, or you can apply them manually:

```bash
npx supabase db reset
```

This creates:
- `profiles` table (user profiles with premium status)
- `favorites` table (user favorite spots)

### 5. Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to see the map with all drone spots.

## Project Structure

```
MVP/
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Root layout with Leaflet CSS
│   │   └── page.tsx         # Home page with map
│   ├── components/
│   │   └── Map.tsx          # Leaflet map component
│   └── lib/
│       └── supabase.ts      # Supabase client
├── public/
│   └── images/
│       └── spots/          # Drone spot images
├── data/
│   ├── spots.json          # Original enriched spots data
│   └── spots-simple.json   # Transformed simplified format
├── supabase/
│   ├── config.toml         # Supabase configuration
│   └── migrations/         # Database migrations
└── transform_data.py       # Data transformation script
```

## Data Management

### Transforming Data

If you need to regenerate `spots-simple.json` from the original data:

```bash
python3 transform_data.py
```

This script:
- Reads `../scraped_data/enriched_spots.json`
- Transforms it to the simplified format
- Normalizes image paths
- Outputs to `data/spots-simple.json`

## Running Supabase

### Start Supabase

```bash
npx supabase start
```

### Stop Supabase

```bash
npx supabase stop
```

### Access Supabase Studio

After starting Supabase, open [http://localhost:54323](http://localhost:54323) to access the Supabase Studio dashboard.

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Next Steps

Once the base MVP is working, you can add:

- User authentication (Supabase Auth)
- Favorite spots functionality
- Weather integration (Open-Meteo API)
- No-fly zone (NFZ) overlays
- Premium features
- Advanced filtering and search

## Troubleshooting

### Map not loading

- Ensure Leaflet CSS is imported in `layout.tsx`
- Check browser console for errors
- Verify that `spots-simple.json` exists in `data/`

### Supabase connection issues

- Make sure Docker Desktop is running
- Run `npx supabase start` and check for errors
- Verify `.env.local` has correct values from `supabase start` output

### Images not displaying

- Check that images are copied to `public/images/spots/`
- Verify image paths in `spots-simple.json` match the file structure
- Ensure image paths start with `images/spots/`

## License

This project is part of the DronesScouting application.
