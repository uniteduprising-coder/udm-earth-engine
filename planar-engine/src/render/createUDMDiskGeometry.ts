import * as THREE from "three";

/**
 * Flat circular disk — concentric rings + radial segments.
 * NOT SphereGeometry. NOT rectangular PlaneGeometry as world body.
 */
export function createUDMDiskGeometry(
  radius: number,
  radialSegments: number,
  ringSegments: number
): THREE.BufferGeometry {
  const vertices: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let ring = 0; ring <= ringSegments; ring++) {
    const r = (ring / ringSegments) * radius;
    for (let seg = 0; seg <= radialSegments; seg++) {
      const theta = (seg / radialSegments) * Math.PI * 2;
      const x = r * Math.cos(theta);
      const y = r * Math.sin(theta);
      vertices.push(x, y, 0);
      const u = 0.5 + x / (2 * radius);
      const v = 0.5 + y / (2 * radius);
      uvs.push(u, v);
    }
  }

  const row = radialSegments + 1;
  for (let ring = 0; ring < ringSegments; ring++) {
    for (let seg = 0; seg < radialSegments; seg++) {
      const a = ring * row + seg;
      const b = a + 1;
      const c = a + row;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

/** Apply bathymetry / field height to disk vertices (Z only — domain stays planar). */
export function displaceDiskZ(
  geometry: THREE.BufferGeometry,
  sampler: (x: number, y: number) => number,
  zScale = 0.15
) {
  const pos = geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    pos.setZ(i, sampler(x, y) * zScale);
  }
  pos.needsUpdate = true;
  geometry.computeVertexNormals();
}