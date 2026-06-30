/** Strict coordinate wall — no renderer may use lat/lon directly. */

export type SourceLatLon = {
  lat: number;
  lon: number;
  label?: string;
};

export type SourcePixel = {
  px: number;
  py: number;
  plateWidth: number;
  plateHeight: number;
};

export type UDMPoint2D = {
  x: number;
  y: number;
  r: number;
  theta: number;
};

export type UDMPoint3D = UDMPoint2D & {
  z: number;
};

export type UDMRasterLayer = {
  id: string;
  url: string;
  opacity: number;
  visible: boolean;
};

export type UDMVectorLayer = {
  id: string;
  points: UDMPoint3D[];
};

export type UDMFieldLayer = {
  id: string;
  field: "flow" | "glow" | "bstat" | "vr";
};

export type ProjectionDiagnostics = {
  planarDiskMode: true;
  sphericalMode: false;
  rectangularWorldMode: false;
  globeMode: false;
  coordinateAuthority: "udmProjection";
};

export const PLANAR_DIAGNOSTICS: ProjectionDiagnostics = {
  planarDiskMode: true,
  sphericalMode: false,
  rectangularWorldMode: false,
  globeMode: false,
  coordinateAuthority: "udmProjection",
};