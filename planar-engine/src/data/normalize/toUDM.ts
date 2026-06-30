import type { SourceLatLon, UDMPoint3D } from "@/core/coordinateTypes";
import { sourceLatLonToUDM3 } from "@/core/udmProjection";

export type NormalizedPoint = {
  source: SourceLatLon;
  udm: UDMPoint3D;
};

export function normalizeLatLonBatch(points: SourceLatLon[]): NormalizedPoint[] {
  return points.map((source) => ({
    source,
    udm: sourceLatLonToUDM3(source),
  }));
}