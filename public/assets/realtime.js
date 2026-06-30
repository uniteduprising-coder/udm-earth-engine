(function () {
  const $ = (id) => document.getElementById(id);
  const imgs = {
    composite: $("rt-composite"),
    base: $("rt-base"),
    geocolor: $("rt-geocolor"),
    central: null,
    unwrapped: null,
  };

  function setView(mode) {
    ["composite", "base", "geocolor"].forEach((k) => {
      if (imgs[k]) imgs[k].classList.toggle("hidden", k !== mode);
    });
    const wrap = document.querySelector(".rt-canvas-wrap");
    let el = wrap.querySelector(".rt-dynamic");
    if (el) el.remove();
    if (mode === "central" || mode === "unwrapped") {
      const img = document.createElement("img");
      img.className = "rt-dynamic";
      img.src = mode === "central" ? "/data/realtime/central_zoom.jpg" : "/data/realtime/unwrapped.png";
      img.alt = mode;
      wrap.appendChild(img);
      imgs.composite.classList.add("hidden");
      imgs.base.classList.add("hidden");
      imgs.geocolor.classList.add("hidden");
    }
  }

  document.querySelectorAll('input[name="view"]').forEach((r) => {
    r.addEventListener("change", () => { if (r.checked) setView(r.value); });
  });

  async function loadJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  async function refreshPanel() {
    $("rt-status").textContent = "Loading…";
    try {
      const [disk, sw, report, manifest] = await Promise.all([
        loadJson("/data/realtime/disk.json"),
        loadJson("/data/realtime/spaceweather.json"),
        loadJson("/data/realtime/report.json"),
        loadJson("/data/realtime/manifest.json").catch(() => ({})),
      ]);

      $("rt-disk").textContent = [
        `plate_lock: ${disk.plate_lock}`,
        `center: ${JSON.stringify(disk.center_px_refined)}`,
        `radius: ${disk.outer_radius_px_refined} px`,
        `size: ${disk.width_px}×${disk.height_px}`,
      ].join("\n");

      const mag = sw.files?.mag?.normalized;
      $("rt-swpc").textContent = mag
        ? `Bz: ${mag.bz_gsm_nT} nT\n@ ${mag.time_tag}`
        : JSON.stringify(sw.files || sw, null, 2).slice(0, 400);

      $("rt-report").textContent = [
        `control: ${report.derived?.control_grade} (${report.derived?.mesh_nodes} mesh nodes)`,
        `validation: ${report.validation?.passed}/${report.validation?.total}`,
        `edges: ${report.derived?.feature_edges ? "ok" : "—"}`,
        `warp: ${report.warp?.layers?.geocolor?.ok ? "geocolor ok" : "pending"}`,
      ].join("\n");

      const src = report.source_status_summary || {};
      $("rt-sources").textContent = Object.entries(src)
        .map(([k, v]) => `${k}: ${v}`)
        .join("\n") || "—";

      const ts = Date.now();
      ["composite", "base", "geocolor"].forEach((k) => {
        if (imgs[k]?.src) imgs[k].src = imgs[k].src.split("?")[0] + `?t=${ts}`;
      });

      $("rt-status").textContent = `Live · ${report.finished_at || "ok"}`;
    } catch (e) {
      $("rt-status").textContent = `Error: ${e.message}`;
    }
  }

  $("btn-refresh").addEventListener("click", async () => {
    $("btn-refresh").disabled = true;
    $("rt-status").textContent = "Running pipeline…";
    try {
      const r = await fetch("/api/realtime/run", { method: "POST" });
      await r.json();
      await refreshPanel();
    } catch (e) {
      $("rt-status").textContent = `Pipeline error: ${e.message}`;
    }
    $("btn-refresh").disabled = false;
  });

  refreshPanel();
})();