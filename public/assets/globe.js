(function () {
  const CESIUM_VER = "1.118.2";
  window.CESIUM_BASE_URL = `https://cdn.jsdelivr.net/npm/cesium@${CESIUM_VER}/Build/Cesium/`;

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

  function isoDay(offsetDays = 0) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - offsetDays);
    return d.toISOString().split("T")[0];
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
  let baseKey = "geocolor";
  let baseDay = isoDay(1);
  const active = { base: null, overlays: {} };

  function addLayer(def, day, alpha = 1) {
    const layer = viewer.imageryLayers.addImageryProvider(gibsProvider(def, day));
    layer.alpha = alpha;
    return layer;
  }

  function replaceBase(key, dayOffset = 1) {
    const def = LAYERS[key];
    if (!def) return;
    baseKey = key;
    baseDay = isoDay(dayOffset);
    if (active.base) viewer.imageryLayers.remove(active.base, false);
    active.base = addLayer(def, baseDay, 1);
    setStatus(`Base: ${def.label} · ${baseDay} · NASA GIBS (cloud)`);
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
      active.overlays[key] = addLayer(def, baseDay, opacity);
    } else {
      active.overlays[key].alpha = opacity;
    }
  }

  function flyNorthPole() {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, 89.5, 2_200_000),
      duration: 1.4,
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
        `UDM scale: ${km ? km.toFixed(4) : "?"} km/px`,
        islands ? `Four-island ring: ${islands.px_from_center} px from center` : "",
        "Auto-view: North aperture (Rupes Nigra region)",
      ]
        .filter(Boolean)
        .join("\n");
    } catch {
      metaEl.textContent = "UDM scale metadata loading…";
    }
  }

  window.addEventListener("load", () => {
    try {
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
        creditContainer: document.createElement("div"),
      });

      viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0a0f18");
      viewer.scene.skyAtmosphere.show = true;
      viewer.scene.globe.enableLighting = true;

      replaceBase("geocolor", 1);

      viewer.entities.add({
        name: "UDM North Axis",
        position: Cesium.Cartesian3.fromDegrees(0, 90),
        point: {
          pixelSize: 12,
          color: Cesium.Color.CYAN.withAlpha(0.95),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
        label: {
          text: "North aperture",
          font: "13px Segoe UI",
          fillColor: Cesium.Color.WHITE,
          pixelOffset: new Cesium.Cartesian2(0, -20),
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.6),
        },
      });

      $("gb-base")?.addEventListener("change", (e) => replaceBase(e.target.value, 1));
      document.querySelectorAll("[data-overlay]").forEach((el) => {
        const key = el.dataset.overlay;
        const op = document.querySelector(`[data-opacity='${key}']`);
        const sync = () => toggleOverlay(key, el.checked, (Number(op?.value || 60) || 60) / 100);
        el.addEventListener("change", sync);
        op?.addEventListener("input", sync);
      });
      $("gb-pole")?.addEventListener("click", flyNorthPole);
      $("gb-refresh")?.addEventListener("click", () => replaceBase($("gb-base").value, 0));

      loadUdmMeta();
      setTimeout(flyNorthPole, 800);
      setStatus("Cloud globe ready — drag to orbit, scroll to zoom");
    } catch (err) {
      setStatus(`Globe error: ${err.message}`);
      console.error(err);
    }
  });
})();