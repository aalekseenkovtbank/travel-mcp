import type { MapPoint } from "@travel-growth-inspiration/contracts";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import { EntityImage } from "./EntityImage";

const colors: Record<MapPoint["type"], string> = {
  hotel: "#ff5a3c",
  restaurant: "#efad35",
  event: "#7557d9",
  poi: "#1f8a70",
};

export function TripMap({ points }: { points: MapPoint[] }) {
  const center = points[0] ?? { latitude: 55.7558, longitude: 37.6176 };
  return (
    <MapContainer
      className="trip-map"
      center={[center.latitude, center.longitude]}
      zoom={13}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((point) => (
        <CircleMarker
          key={point.id}
          center={[point.latitude, point.longitude]}
          radius={point.type === "hotel" ? 10 : 7}
          pathOptions={{ color: "#fff", fillColor: colors[point.type], fillOpacity: 1, weight: 3 }}
        >
          <Popup>
            <EntityImage image={point.image} alt={point.name} className="map-popup-photo" />
            <strong>{point.name}</strong>
            {point.subtitle ? <><br />{point.subtitle}</> : null}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
