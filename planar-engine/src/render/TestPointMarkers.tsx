import type { NormalizedPoint } from "@/data/normalize/toUDM";
import { udmToSceneXYZ } from "@/core/udmProjection";

const SCENE_R = 5;

export function TestPointMarkers({ points }: { points: NormalizedPoint[] }) {
  return (
    <group>
      {points.map((p, i) => {
        const [x, y, z] = udmToSceneXYZ(p.udm, SCENE_R);
        return (
          <mesh key={i} position={[x, y, z + 0.08]}>
            <sphereGeometry args={[0.08, 12, 12]} />
            <meshBasicMaterial color="#f59e0b" />
          </mesh>
        );
      })}
    </group>
  );
}