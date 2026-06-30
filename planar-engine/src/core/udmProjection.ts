/**
 * UDM coordinate engine — the ONLY gateway for lat/lon → planar disk.
 * Mirrors earth.cosmology.coordinates (v5 cylindrical bijection).
 * No haversine, no EPSG, no Web Mercator, no globe wrapping.
 */

import type { SourceLatLon, SourcePixel, UDMPoint2D, UDMPoint3D } from "./coordinateTypes";

export const R_DISK_MI = 12500;
export const DISK_RADIUS_UNITS = 1.0;

/** Geographic WGS84 → UDM cylindrical (r_mi, θ_rad). */
export function geoToCylindrical(lat: number, lon: number, R_disk = R_DISK_MI) {
  const colatRad = ((90 - lat) * Math.PI) / 180;
  const rMi = ((2 * colatRad) / Math.PI) * R_disk;
  const thetaRad = (lon * Math.PI) / 180;
  return { rMi, thetaRad, colatDeg: (colatRad * 180) / Math.PI };
}

/** Cylindrical miles → normalized disk Cartesian (x,y ∈ disk, r≤1). */
export function cylindricalToPlanarXY(rMi: number, thetaRad: number, R_disk = R_DISK_MI): UDMPoint2D {
  const r = Math.min(rMi / R_disk, 1.0);
  const x = r * Math.cos(thetaRad) * DISK_RADIUS_UNITS;
  const y = r * Math.sin(thetaRad) * DISK_RADIUS_UNITS;
  return { x, y, r, theta: thetaRad };
}

/** Sole allowed lat/lon entry point for rendering. */
export function sourceLatLonToUDM(p: SourceLatLon, R_disk = R_DISK_MI): UDMPoint2D {
  const { rMi, thetaRad } = geoToCylindrical(p.lat, p.lon, R_disk);
  return cylindricalToPlanarXY(rMi, thetaRad, R_disk);
}

export function sourceLatLonToUDM3(p: SourceLatLon, z = 0, R_disk = R_DISK_MI): UDMPoint3D {
  const xy = sourceLatLonToUDM(p, R_disk);
  return { ...xy, z };
}

/** Plate-locked pixel → planar (uses outer radius = rim). */
export function sourcePixelToUDM(
  p: SourcePixel,
  center: [number, number],
  outerRadiusPx: number,
  R_disk = R_DISK_MI
): UDMPoint2D {
  const dx = p.px - center[0];
  const dy = p.py - center[1];
  const rho = Math.min(Math.hypot(dx, dy) / outerRadiusPx, 1);
  const theta = Math.atan2(dx, -dy);
  const rMi = rho * R_disk;
  return cylindricalToPlanarXY(rMi, theta, R_disk);
}

/** Polar (r, θ) on disk → Three.js scene XY (disk lies in XY plane). */
export function udmToSceneXY(p: UDMPoint2D, sceneRadius = 5): [number, number, number] {
  const scale = sceneRadius / DISK_RADIUS_UNITS;
  return [p.x * scale, p.y * scale, 0];
}

export function udmToSceneXYZ(p: UDMPoint3D, sceneRadius = 5, zScale = 0.02): [number, number, number] {
  const [x, y] = udmToSceneXY(p, sceneRadius);
  return [x, y, p.z * zScale];
}