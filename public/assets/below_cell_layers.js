/**
 * UDM v5.2β — below-cell vortex, island roots, exterior void layers
 */
(function () {
  class BelowCellLayerManager {
    constructor(scene) {
      this.scene = scene;
      this.layers = {
        mirrorHydroVortex: null,
        belowAetherGlow: null,
        islandRoots: [],
        bottomBoundary: null,
        upwellingColumn: null,
        domainWireframe: null,
        voidShell: null,
      };
      this._init();
    }

    _init() {
      const hydroMat = new THREE.PointsMaterial({
        color: 0x1a5276,
        size: 0.02,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        transparent: true,
        opacity: 0.7,
      });
      const aetherMat = new THREE.PointsMaterial({
        color: 0x2ecc71,
        size: 0.03,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        transparent: true,
        opacity: 0.4,
      });
      const hydroGeo = new THREE.BufferGeometry();
      const aetherGeo = new THREE.BufferGeometry();
      const pts = [];
      for (let i = 0; i < 200; i++) {
        const th = (i / 200) * Math.PI * 2;
        const r = 0.3 + 0.5 * Math.random();
        pts.push(r * Math.cos(th), r * Math.sin(th), -0.2 - 0.6 * Math.random());
      }
      hydroGeo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
      aetherGeo.setAttribute('position', new THREE.Float32BufferAttribute(pts.map((v, i) => (i % 3 === 2 ? v * 1.2 : v)), 3));
      this.layers.mirrorHydroVortex = new THREE.Points(hydroGeo, hydroMat);
      this.layers.belowAetherGlow = new THREE.Points(aetherGeo, aetherMat);

      const angles = [Math.PI / 4, (3 * Math.PI) / 4, (5 * Math.PI) / 4, (7 * Math.PI) / 4];
      const rIso = 0.35;
      angles.forEach((th) => {
        const root = new THREE.Mesh(
          new THREE.CylinderGeometry(0.008, 0.008, 0.25, 16),
          new THREE.MeshPhongMaterial({
            color: 0x8b4513,
            emissive: 0x1a0a00,
            emissiveIntensity: 0.3,
            transparent: true,
            opacity: 0.85,
          })
        );
        root.position.set(rIso * Math.cos(th), -0.12, rIso * Math.sin(th));
        root.rotation.x = Math.PI / 2;
        this.layers.islandRoots.push(root);
        this.scene.add(root);
      });

      const bottom = new THREE.Mesh(
        new THREE.CircleGeometry(1.2, 64),
        new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide, transparent: true, opacity: 0.95 })
      );
      bottom.rotation.x = Math.PI / 2;
      bottom.position.y = -1.1;
      this.layers.bottomBoundary = bottom;

      const column = new THREE.Mesh(
        new THREE.CylinderGeometry(0.01, 0.01, 1.0, 16),
        new THREE.MeshBasicMaterial({ color: 0x3498db, transparent: true, opacity: 0.3 })
      );
      column.position.y = -0.55;
      this.layers.upwellingColumn = column;

      const dome = new THREE.Mesh(
        new THREE.SphereGeometry(1.15, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2),
        new THREE.MeshBasicMaterial({ color: 0x111820, wireframe: true, transparent: true, opacity: 0.25 })
      );
      this.layers.domainWireframe = dome;

      const voidGeo = new THREE.SphereGeometry(1.5, 24, 12);
      this.layers.voidShell = new THREE.Mesh(
        voidGeo,
        new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide })
      );

      [this.layers.mirrorHydroVortex, this.layers.belowAetherGlow, bottom, column, dome, this.layers.voidShell].forEach((l) => {
        if (l) {
          l.visible = false;
          this.scene.add(l);
        }
      });
    }

    update(telemetry) {
      const bc = telemetry?.belowCell;
      if (!bc) return;
      this.layers.islandRoots.forEach((root, i) => {
        const d = (bc.islandCurrent && bc.islandCurrent[i]) || 0.3;
        root.material.emissiveIntensity = 0.1 + 0.4 * d;
      });
    }

    setLayerVisibility(which, visible) {
      if (which === 'upper') {
        if (this.layers.domainWireframe) this.layers.domainWireframe.visible = visible;
      }
      if (which === 'below') {
        [this.layers.mirrorHydroVortex, this.layers.belowAetherGlow, this.layers.bottomBoundary, this.layers.upwellingColumn].forEach(
          (l) => { if (l) l.visible = visible; }
        );
        this.layers.islandRoots.forEach((r) => { r.visible = visible; });
      }
      if (which === 'void' && this.layers.voidShell) this.layers.voidShell.visible = visible;
      if (which === 'boundary' && this.layers.domainWireframe) this.layers.domainWireframe.visible = visible;
    }

    setAllVisible(v) {
      Object.values(this.layers).forEach((layer) => {
        if (Array.isArray(layer)) layer.forEach((l) => { l.visible = v; });
        else if (layer) layer.visible = v;
      });
    }
  }

  window.UDM_BELOW_CELL = { BelowCellLayerManager };
})();