import { useMemo } from "react";
import * as THREE from "three";

const RADIUS = 5;
const RING_COUNT = 8;
const MERIDIAN_COUNT = 12;

export function DiskGuides() {
  const { ringLines, meridianLines } = useMemo(() => {
    const ringLines: THREE.BufferGeometry[] = [];
    for (let i = 1; i <= RING_COUNT; i++) {
      const r = (i / RING_COUNT) * RADIUS;
      const pts: THREE.Vector3[] = [];
      for (let s = 0; s <= 64; s++) {
        const t = (s / 64) * Math.PI * 2;
        pts.push(new THREE.Vector3(r * Math.cos(t), r * Math.sin(t), 0.02));
      }
      ringLines.push(new THREE.BufferGeometry().setFromPoints(pts));
    }
    const meridianLines: THREE.BufferGeometry[] = [];
    for (let m = 0; m < MERIDIAN_COUNT; m++) {
      const t = (m / MERIDIAN_COUNT) * Math.PI * 2;
      meridianLines.push(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0.02),
          new THREE.Vector3(RADIUS * Math.cos(t), RADIUS * Math.sin(t), 0.02),
        ])
      );
    }
    return { ringLines, meridianLines };
  }, []);

  return (
    <group>
      {ringLines.map((g, i) => (
        <lineLoop key={`ring-${i}`} geometry={g}>
          <lineBasicMaterial color="#3b82f6" transparent opacity={0.25} />
        </lineLoop>
      ))}
      {meridianLines.map((g, i) => (
        <lineSegments key={`mer-${i}`} geometry={g}>
          <lineBasicMaterial color="#60a5fa" transparent opacity={0.35} />
        </lineSegments>
      ))}
      <mesh position={[0, 0, 0.05]}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshBasicMaterial color="#00ffd5" />
      </mesh>
    </group>
  );
}