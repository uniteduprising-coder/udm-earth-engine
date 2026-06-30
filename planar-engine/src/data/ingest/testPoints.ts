import type { SourceLatLon } from "@/core/coordinateTypes";

/** Calibration points — converted via sourceLatLonToUDM only. */
export const TEST_POINTS: SourceLatLon[] = [
  { lat: 90, lon: 0, label: "North aperture" },
  { lat: 0, lon: 0, label: "Equator / prime" },
  { lat: 45, lon: 90, label: "NE quadrant" },
  { lat: -45, lon: -120, label: "SW test" },
  { lat: 70, lon: 45, label: "Arctic band" },
];