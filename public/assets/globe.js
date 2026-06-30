(function () {
  const $ = (id) => document.getElementById(id);
  const diskEl = $("gb-disk");
  const ringsCanvas = $("gb-rings");
  const statusEl = $("gb-status");
  const metaEl = $("gb-meta");

  const layerImgs = {};
  diskEl?.querySelectorAll("img[data-src]").forEach((img) => {
    layerImgs[img.dataset.src] = img;
  });

  let diskMeta = { center: [1024, 1022], outer_radius_px: 1012, width_px: 2048 };
  let features = [];

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function bust(url) {
    return `${url.split("?")[0]}?t=${Date.now()}`;
  }

  function resizeRings() {
    if (!ringsCanvas || !diskEl) return;
    const rect = diskEl.getBoundingClientRect();
    const size = Math.round(rect.width);
    ringsCanvas.width = size;
    ringsCanvas.height = size;
    drawRings();
  }

  function pxToNorm(px) {
    return px / (diskMeta.outer_radius_px || 1012);
  }

  function drawRings() {
    const ctx = ringsCanvas?.getContext("2d");
    if (!ctx || !ringsCanvas.width) return;
    ctx.clearRect(0, 0, ringsCanvas.width, ringsCanvas.height);
    const cx = ringsCanvas.width / 2;
    const cy = ringsCanvas.height / 2;
    const R = ringsCanvas.width / 2;

    const showRings = $("ly-rings")?.checked !== false;
    const showIslands = $("ly-islands")?.checked !== false;

    if (showRings) {
      const ringFeatures = features.filter((f) =>
        /rupes|island_outer|equator|arctic|rim/.test(f.name)
      );
      ringFeatures.forEach((f) => {
        const r = pxToNorm(f.px_from_center) * R;
        if (r <= 0 || r > R) return;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle =
          f.name.includes("rupes") ? "rgba(180, 80, 255, 0.9)"
          : f.name.includes("island") ? "rgba(100, 220, 255, 0.85)"
          : f.name.includes("equator") ? "rgba(255, 200, 80, 0.7)"
          : "rgba(120, 160, 220, 0.45)";
        ctx.lineWidth = f.name.includes("rupes") ? 2 : 1;
        ctx.setLineDash(f.name.includes("rim") ? [6, 4] : []);
        ctx.stroke();
      });
    }

    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(0, 255, 220, 0.95)";
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.font = "11px Segoe UI, system-ui, sans-serif";
    ctx.fillText("North aperture", cx + 8, cy - 8);

    if (showIslands) {
      const bearings = [45, 135, 225, 315];
      const island = features.find((f) => f.name === "island_outer_termination");
      const rho = island ? pxToNorm(island.px_from_center) : 0.0146;
      bearings.forEach((deg) => {
        const rad = (deg * Math.PI) / 180;
        const x = cx + Math.sin(rad) * rho * R;
        const y = cy - Math.cos(rad) * rho * R;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(160, 190, 220, 0.95)";
        ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,0.6)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });
    }
  }

  function bindLayers() {
    $("ly-procedural")?.addEventListener("change", (e) => {
      if (layerImgs.procedural) layerImgs.procedural.style.opacity = e.target.checked ? "1" : "0";
    });
    $("ly-geocolor")?.addEventListener("change", (e) => {
      if (layerImgs.geocolor) layerImgs.geocolor.style.opacity = e.target.checked ? "0.92" : "0";
    });
    $("ly-rings")?.addEventListener("change", drawRings);
    $("ly-islands")?.addEventListener("change", drawRings);

    document.querySelectorAll("[data-layer]").forEach((cb) => {
      const id = cb.dataset.layer;
      const img = layerImgs[id];
      const slider = document.querySelector(`[data-opacity='${id}']`);
      const sync = () => {
        if (!img) return;
        const on = cb.checked;
        img.classList.toggle("hidden", !on);
        img.style.opacity = on ? String((Number(slider?.value || 50) || 50) / 100) : "0";
      };
      cb.addEventListener("change", sync);
      slider?.addEventListener("input", sync);
    });
  }

  async function loadMeta() {
    try {
      const [manifest, terms] = await Promise.all([
        fetch("/api/procedural/status").then((r) => r.json()),
        fetch("/api/procedural/terminations").then((r) => r.json()),
      ]);
      diskMeta = manifest?.terminations?.disk || terms?.disk || diskMeta;
      features = manifest?.terminations?.features || terms?.features || [];
      const a = manifest?.terminations?.anchors || terms?.anchors || {};
      metaEl.textContent = [
        `km/px: ${a.km_per_px ?? "—"}`,
        `center: ${JSON.stringify(diskMeta.center)}`,
        `R: ${diskMeta.outer_radius_px} px`,
        `NOT spherical — flat polar Frame-U`,
      ].join("\n");
      resizeRings();
      setStatus("Flat polar disk ready — scroll overlays, not a globe");
    } catch (e) {
      metaEl.textContent = `Scale metadata: ${e}`;
    }
  }

  function refreshImages() {
    Object.values(layerImgs).forEach((img) => {
      if (img.src) img.src = bust(img.src);
    });
  }

  window.addEventListener("resize", resizeRings);
  window.addEventListener("load", () => {
    bindLayers();
    loadMeta();
    refreshImages();
    if (layerImgs.geocolor) layerImgs.geocolor.style.opacity = "0.92";
  });
})();