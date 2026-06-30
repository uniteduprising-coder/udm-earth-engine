import { MapContainer, ImageOverlay } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/** Leaflet CRS.Simple only — square grid, no EPSG:4326. */
const bounds: L.LatLngBoundsExpression = [
  [0, 0],
  [1000, 1000],
];

export function LeafletSimpleMap({ textureUrl }: { textureUrl: string }) {
  return (
    <div className="leaflet-panel">
      <div className="leaflet-panel-title">CRS.Simple control (planar)</div>
      <MapContainer
        crs={L.CRS.Simple}
        bounds={bounds}
        maxBounds={bounds}
        style={{ height: 180, width: "100%" }}
        zoom={0}
        minZoom={-1}
        maxZoom={2}
        attributionControl={false}
      >
        <ImageOverlay url={textureUrl} bounds={bounds} opacity={0.85} />
      </MapContainer>
    </div>
  );
}