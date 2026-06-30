import { useMemo } from "react";
import { useLoader } from "@react-three/fiber";
import * as THREE from "three";
import { createUDMDiskGeometry, displaceDiskZ } from "./createUDMDiskGeometry";
import { flowMagnitude, DEFAULT_SIM } from "@/simulation/fieldSample";

const DISK_SCENE_RADIUS = 5;
const RADIAL_SEGMENTS = 64;
const RING_SEGMENTS = 48;

type Props = {
  textureUrl: string;
  showFlowDisplacement: boolean;
};

export function ThreeUDMPlane({ textureUrl, showFlowDisplacement }: Props) {
  const texture = useLoader(THREE.TextureLoader, textureUrl);

  const geometry = useMemo(() => {
    const geo = createUDMDiskGeometry(DISK_SCENE_RADIUS, RADIAL_SEGMENTS, RING_SEGMENTS);
    if (showFlowDisplacement) {
      displaceDiskZ(geo, (x, y) => {
        const rho = Math.hypot(x, y) / DISK_SCENE_RADIUS;
        const theta = Math.atan2(y, x);
        return flowMagnitude(rho, theta, DEFAULT_SIM) * 8;
      });
    }
    return geo;
  }, [showFlowDisplacement]);

  useMemo(() => {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
  }, [texture]);

  return (
    <mesh geometry={geometry} rotation={[0, 0, 0]}>
      <meshStandardMaterial map={texture} side={THREE.DoubleSide} roughness={0.85} metalness={0.05} />
    </mesh>
  );
}