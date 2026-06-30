import { useEffect, useMemo, useState } from "react";
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
  const [texture, setTexture] = useState<THREE.Texture | null>(null);

  useEffect(() => {
    let alive = true;
    const loader = new THREE.TextureLoader();
    loader.load(
      textureUrl,
      (tex) => {
        if (!alive) return;
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
        setTexture(tex);
      },
      undefined,
      () => {
        if (alive) setTexture(null);
      }
    );
    return () => {
      alive = false;
    };
  }, [textureUrl]);

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

  return (
    <mesh geometry={geometry} rotation={[0, 0, 0]}>
      <meshStandardMaterial
        map={texture ?? undefined}
        color={texture ? "#ffffff" : "#1a2844"}
        side={THREE.DoubleSide}
        roughness={0.85}
        metalness={0.05}
      />
    </mesh>
  );
}