import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default Leaflet marker icons not displaying properly in React/Webpack/Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

// Hardcoded static/fake shuttle markers around UCSD campus
const FAKE_SHUTTLES = [
  {
    id: 'shuttle-1',
    name: 'Inside Loop Shuttle',
    route: 'Campus Loop',
    lat: 32.8810,
    lng: -117.2360,
    status: 'On Time',
  },
  {
    id: 'shuttle-2',
    name: 'Outside Loop Shuttle',
    route: 'Campus Loop',
    lat: 32.8765,
    lng: -117.2320,
    status: 'Delayed 2 mins',
  },
  {
    id: 'shuttle-3',
    name: 'Regents Shuttle',
    route: 'East Campus / Regents',
    lat: 32.8835,
    lng: -117.2280,
    status: 'On Time',
  },
  {
    id: 'shuttle-4',
    name: 'SIO Shuttle',
    route: 'Scripps Institution of Oceanography',
    lat: 32.8680,
    lng: -117.2500,
    status: 'On Time',
  },
];

// Center coordinates for UCSD Campus (Geisel Library vicinity)
const UCSD_CENTER = [32.8801, -117.2340];
const DEFAULT_ZOOM = 15;

export default function Map() {
  return (
    <div className="map-container">
      <MapContainer
        center={UCSD_CENTER}
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom={true}
        style={{ width: '100%', height: '100%' }}
      >
        {/* OpenStreetMap Tile Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Render Fake Shuttle Markers */}
        {FAKE_SHUTTLES.map((shuttle) => (
          <Marker key={shuttle.id} position={[shuttle.lat, shuttle.lng]}>
            <Popup>
              <div>
                <h3 style={{ margin: '0 0 4px 0' }}>🚌 {shuttle.name}</h3>
                <p style={{ margin: '2px 0' }}><strong>Route:</strong> {shuttle.route}</p>
                <p style={{ margin: '2px 0' }}><strong>Status:</strong> {shuttle.status}</p>
                <p style={{ margin: '2px 0', fontSize: '0.8em', color: '#666' }}>
                  Lat: {shuttle.lat}, Lng: {shuttle.lng}
                </p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}