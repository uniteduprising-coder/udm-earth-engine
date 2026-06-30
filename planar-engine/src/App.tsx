import { Suspense, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { ThreeUDMPlane } from "@/render/ThreeUDMPlane";
import { DiskGuides } from "@/render/DiskGuides";
import { TestPointMarkers } from "@/render/TestPointMarkers";
import { DiagnosticPanel } from "@/render/DiagnosticPanel";
import { LeafletSimpleMap } from "@/render/LeafletSimpleMap";
import { TEST_POINTS } from "@/data/ingest/testPoints";
import { normalizeLatLonBatch } from "@/data/normalize/toUDM";
import "./app.css";

const TEXTURE = "/data/procedural/composite.png";

export default function App() {
  const [flowDisp, setFlowDisp] = useState(false);
  const [selected, setSelected] = useState(0);
  const normalized = useMemo(() => normalizeLatLonBatch(TEST_POINTS), []);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>UDM Planar Simulation Engine</h1>
          <p>
            Flat circular disk · custom Cartesian · lat/lon converted once via udmProjection · not a globe
          </p>
        </div>
        <nav>
          <a href="/">Atlas</a>
          <a href="/realtime">Realtime</a>
          <a href="/toroid">Toroid</a>
        </nav>
      </header>

      <div className="app-body">
        <div className="viewport">
          <Canvas orthographic camera={{ position: [0, 0, 12], zoom: 55 }} gl={{ antialias: true }}>
            <color attach="background" args={["#060a10"]} />
            <ambientLight intensity={0.65} />
            <directionalLight position={[4, 6, 8]} intensity={1.1} />
            <Suspense fallback={null}>
              <ThreeUDMPlane textureUrl={TEXTURE} showFlowDisplacement={flowDisp} />
              <DiskGuides />
              <TestPointMarkers points={normalized} />
            </Suspense>
            <OrbitControls enableRotate={false} minZoom={40} maxZoom={120} />
          </Canvas>
        </div>

        <DiagnosticPanel
          points={normalized}
          activeLayer={flowDisp ? "flow displacement (Z)" : "procedural composite"}
          selectedIndex={selected}
          onSelect={setSelected}
        />
      </div>

      <div className="app-footer-row">
        <label className="toggle">
          <input type="checkbox" checked={flowDisp} onChange={(e) => setFlowDisp(e.target.checked)} />
          Hydro flow Z displacement (planar domain, not spherical)
        </label>
        <LeafletSimpleMap textureUrl={TEXTURE} />
      </div>
    </div>
  );
}