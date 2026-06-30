import { PLANAR_DIAGNOSTICS } from "@/core/coordinateTypes";
import type { NormalizedPoint } from "@/data/normalize/toUDM";

type Props = {
  points: NormalizedPoint[];
  activeLayer: string;
  selectedIndex: number;
  onSelect: (i: number) => void;
};

export function DiagnosticPanel({ points, activeLayer, selectedIndex, onSelect }: Props) {
  const sel = points[selectedIndex];
  return (
    <aside className="diag-panel">
      <h2>Diagnostics</h2>
      <div className="diag-flags">
        <span className="flag ok">PLANAR DISK MODE: TRUE</span>
        <span className="flag ok">PLANAR MODE: TRUE</span>
        <span className="flag no">SPHERICAL MODE: FALSE</span>
        <span className="flag no">GLOBE MODE: FALSE</span>
        <span className="flag no">RECTANGULAR WORLD: FALSE</span>
      </div>
      <p className="diag-meta">Authority: {PLANAR_DIAGNOSTICS.coordinateAuthority}</p>
      <p className="diag-meta">Active layer: {activeLayer}</p>
      <h3>Test points (lat/lon → UDM before render)</h3>
      <ul className="diag-points">
        {points.map((p, i) => (
          <li key={i}>
            <button
              type="button"
              className={i === selectedIndex ? "active" : ""}
              onClick={() => onSelect(i)}
            >
              {p.source.label ?? `Point ${i}`}
            </button>
          </li>
        ))}
      </ul>
      {sel && (
        <pre className="diag-readout">
          {`source: lat=${sel.source.lat} lon=${sel.source.lon}
UDM: x=${sel.udm.x.toFixed(4)} y=${sel.udm.y.toFixed(4)}
     r=${sel.udm.r.toFixed(4)} θ=${sel.udm.theta.toFixed(4)} rad`}
        </pre>
      )}
    </aside>
  );
}