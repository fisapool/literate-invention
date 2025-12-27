'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import spots from '../../data/spots-simple.json';

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);

const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);

const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
);

const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);

interface Spot {
  id: number;
  name: string;
  lat: number;
  lng: number;
  description: string;
  category: string;
  images: string[];
  rating?: number;
  address?: string;
}

export default function DroneMap() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    // Fix for default marker icons in Next.js
    const L = require('leaflet');
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });
  }, []);

  if (!isClient) {
    return <div className="h-screen w-full flex items-center justify-center">Loading map...</div>;
  }

  return (
    <MapContainer 
      center={[4.2105, 101.9758]} 
      zoom={6} 
      style={{ height: '100vh', width: '100%' }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {(spots as Spot[]).map((spot) => (
        <Marker 
          key={spot.id} 
          position={[spot.lat, spot.lng]}
        >
          <Popup>
            <div className="p-2 min-w-[200px] max-w-[300px]">
              <h3 className="font-bold text-lg mb-1">{spot.name}</h3>
              {spot.rating && (
                <p className="text-sm text-gray-600 mb-1">⭐ {spot.rating}/5.0</p>
              )}
              <p className="text-sm text-gray-700 mb-2 line-clamp-3">{spot.description}</p>
              {spot.category && (
                <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mb-2">
                  {spot.category}
                </span>
              )}
              {spot.images && spot.images.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs font-semibold">Images:</p>
                  <div className="grid grid-cols-2 gap-1">
                    {spot.images.slice(0, 4).map((image, idx) => (
                      <div key={idx} className="relative w-full h-20 rounded overflow-hidden bg-gray-100">
                        <img
                          src={`/${image}`}
                          alt={`${spot.name} image ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
