import { useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { OrthographicView } from "@deck.gl/core";
import { ScatterplotLayer } from "@deck.gl/layers";
import type { NormalizedPoint } from "@/data/normalize/toUDM";

const SCENE_R = 5;

type Props = {
  points: NormalizedPoint[];
  width: number;
  height: number;
};

/** Cartesian orthographic overlay — NOT geospatial. */
export function DeckOverlay({ points, width, height }: Props) {
  const layerData = useMemo(
    () =>
      points.map((p) => ({
        position: [p.udm.x * SCENE_R, p.udm.y * SCENE_R] as [number, number],
        label: p.source.label ?? "",
        r: p.udm.r,
        theta: p.udm.theta,
      })),
    [points]
  );

  const layers = [
    new ScatterplotLayer({
      id: "udm-test-points",
      data: layerData,
      getPosition: (d) => d.position,
      getRadius: 12000,
      getFillColor: [245, 158, 11, 200],
      pickable: true,
      coordinateSystem: 1, // COORDINATE_SYSTEM.CARTESIAN
    }),
  ];

  return (
    <DeckGL
      views={new OrthographicView({ id: "ortho" })}
      viewState={{
        target: [0, 0, 0],
        zoom: 1.8,
        width,
        height,
      }}
      layers={layers}
      controller={false}
      style={{ pointerEvents: "none", position: "absolute", inset: 0 }}
    />
  );
}