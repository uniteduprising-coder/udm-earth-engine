(function () {
  const LAYERS = {
    geocolor: {
      label: "VIIRS true color",
      layer: "VIIRS_SNPP_CorrectedReflectance_TrueColor",
      matrix: "2km",
      maxLevel: 5,
    },
    modis: {
      label: "MODIS Terra color",
      layer: "MODIS_Terra_CorrectedReflectance_TrueColor",
      matrix: "250m",
      maxLevel: 8,
    },
    thermal: {
      label: "Sea surface temp",
      layer: "GHRSST_L4_MUR_Sea_Surface_Temperature",
      matrix: "1km",
      maxLevel: 7,
    },
    weather: {
      label: "IR clouds (MODIS)",
      layer: "MODIS_Terra_CorrectedReflectance_Bands721",
      matrix: "250m",
      maxLevel: 8,
    },
  };

  const $ = (id) => document.getElementById(id);
  const statusEl = $("gb-status");
  const metaEl = $("gb-meta");

  function isoDay(date = new Date()) {
    return date.toISOString().split("T")[0];
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function gibsProvider(def, day) {
    const time = `TIME=${day}`;
    return new Cesium.WebMapTileServiceImageryProvider({
      url: `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?${time}`,
      layer: def.layer,
      style: "",
      format: "image/jpeg",
      tileMatrixSetID: def.matrix,
      maximumLevel: def.maxLevel,
      tileWidth: 256,
      tileHeight: 256,
      tilingScheme: gibs.GeographicTilingScheme(),
    });
  }

  let viewer;
  const active = { base: null, overlays: {} };

  function replaceBase(key) {
    const def = LAYERS[key];
    if (!def) return;
    if (active.base) viewer.imageryLayers.remove(active.base, false);
    const layer = viewer.imageryLayers.addImageryProvider(gibsProvider(def, isoDay()));
    layer.alpha = 1;
    active.base = layer;
    setStatus(`Base: ${def.label} · ${isoDay()} · NASA GIBS (cloud)`);
  }

  function toggleOverlay(key, on, opacity) {
    const def = LAYERS[key];
    if (!def) return;
    if (!on) {
      if (active.overlays[key]) {
        viewer.imageryLayers.remove(active.overlays[key], false);
        delete active.overlays[key];
      }
      return;
    }
    if (!active.overlays[key]) {
      const layer = viewer.imageryLayers.addImageryProvider(gibsProvider(def, isoDay()));
      layer.alpha = opacity;
      active.overlays[key] = layer;
    } else {
      active.overlays[key].alpha = opacity;
    }
  }

  function flyNorthPole() {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, 89.5, 2_500_000),
      duration: 1.2,
    });
  }

  async function loadUdmMeta() {
    try {
      const r = await fetch("/api/procedural/status");
      if (!r.ok) throw new Error(String(r.status));
      const data = await r.json();
      const km = data?.terminations?.anchors?.km_per_px;
      const islands = data?.terminations?.features?.find((f) => f.name === "island_outer_termination");
      metaEl.textContent = [
        `UDM procedural scale: ${km ? km.toFixed(4) : "?"} km/px`,
        islands ? `Island ring: ${islands.px_from_center} px @ center` : "",
        "Pole view → inspect Rupes / four islands region",
      ]
        .filter(Boolean)
        .join("\n");
    } catch {
      metaEl.textContent = "UDM metadata: run procedural build on API for scale table.";
    }
  }

  window.addEventListener("load", () => {
    viewer = new Cesium.Viewer("gb-map", {
      baseLayer: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: true,
      sceneModePicker: true,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: true,
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });

    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0a0f18");
    viewer.scene.skyAtmosphere.show = true;

    replaceBase("geocolor");

    viewer.entities.add({
      name: "UDM North Axis",
      position: Cesium.Cartesian3.fromDegrees(0, 90),
      point: {
        pixelSize: 10,
        color: Cesium.Color.CYAN.withAlpha(0.9),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
      },
      label: {
        text: "North aperture",
        font: "12px Segoe UI",
        fillColor: Cesium.Color.WHITE,
        pixelOffset: new Cesium.Cartesian2(0, -18),
        showBackground: true,
        backgroundColor: Cesium.Color.BLACK.withAlpha(0.55),
      },
    });

    $("gb-base")?.addEventListener("change", (e) => replaceBase(e.target.value));
    document.querySelectorAll("[data-overlay]").forEach((el) => {
      const key = el.dataset.overlay;
      const op = document.querySelector(`[data-opacity='${key}']`);
      const sync = () => toggleOverlay(key, el.checked, (Number(op?.value || 60) || 60) / 100);
      el.addEventListener("change", sync);
      op?.addEventListener("input", sync);
    });
    $("gb-pole")?.addEventListener("click", flyNorthPole);
    $("gb-refresh")?.addEventListener("click", () => replaceBase($("gb-base").value));

    loadUdmMeta();
    setStatus("Cloud globe ready — no local install required");
  });
})();