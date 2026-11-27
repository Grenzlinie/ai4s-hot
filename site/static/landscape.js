"use strict";
(() => {
  const $ = (id) => document.getElementById(id),
    esc = (v) =>
      String(v ?? "").replace(
        /[&<>"']/g,
        (c) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[c],
      );
  const palette = [
    "#275da6",
    "#187d88",
    "#8954a5",
    "#bc652c",
    "#427b47",
    "#b24974",
    "#6265ac",
    "#867329",
    "#476b86",
    "#a05c6b",
  ];
  let data,
    area = "",
    cluster = "",
    windowDays = 90,
    week = "",
    shown = 30,
    selected = "",
    points = [];
  const dateNumber = (value) =>
    /^\d{4}-\d{2}-\d{2}$/.test(value || "")
      ? Date.parse(value + "T00:00:00Z")
      : NaN;
  const validPoint = (p) =>
    Number.isFinite(p.x) &&
    Number.isFinite(p.y) &&
    p.x >= 0 &&
    p.x <= 1 &&
    p.y >= 0 &&
    p.y <= 1;
  const clusterName = (id) =>
    data.clusters.find((c) => c.id === id)?.label || "未聚类";
  const areaName = (id) =>
    data.areas.find((a) => a.id === id)?.label ||
    (id === "other" ? "领域待定" : id);
  const color = (id) =>
    palette[
      Math.max(
        0,
        data.clusters.findIndex((c) => c.id === id),
      ) % palette.length
    ];
  const safeURL = (value) => {
    try {
      const u = new URL(value);
      return ["http:", "https:"].includes(u.protocol) ? u.href : "#";
    } catch {
      return "#";
    }
  };
  function anchor() {
    return (
      Date.parse(
        (data.as_of_date || (data.generated_at || "").slice(0, 10)) +
          "T00:00:00Z",
      ) || Date.now()
    );
  }
  function matches(p, ignore = "") {
    const t = dateNumber(p.date);
    return (
      (!area || ignore === "area" || p.area === area) &&
      (!cluster ||
        ignore === "cluster" ||
        (cluster === "unclustered" ? !p.cluster : p.cluster === cluster)) &&
      (!windowDays ||
        (Number.isFinite(t) &&
          t >= anchor() - (windowDays - 1) * 86400000 &&
          t <= anchor())) &&
      (!week ||
        ignore === "week" ||
        (Number.isFinite(t) &&
          t >= dateNumber(week) &&
          t < dateNumber(week) + 7 * 86400000))
    );
  }
  function rows(ignore = "") {
    return data.papers.filter((p) => matches(p, ignore));
  }
  function readURL() {
    const q = new URL(location.href).searchParams;
    area =
      data.areas.some((a) => a.id === q.get("area")) ||
      q.get("area") === "other"
        ? q.get("area")
        : "";
    cluster =
      data.clusters.some((c) => c.id === q.get("cluster")) ||
      q.get("cluster") === "unclustered"
        ? q.get("cluster")
        : "";
    windowDays = ["0", "30", "90"].includes(q.get("window"))
      ? Number(q.get("window"))
      : 90;
    week = Number.isFinite(dateNumber(q.get("week"))) ? q.get("week") : "";
    selected = "";
    shown = 30;
  }
  function writeURL() {
    const u = new URL(location.href);
    u.search = "";
    for (const [k, v] of Object.entries({
      area,
      cluster,
      window: String(windowDays),
      week,
    }))
      if (v) u.searchParams.set(k, v);
    history.pushState(null, "", u);
    $("share").href = u.href;
  }
  function change() {
    selected = "";
    shown = 30;
    writeURL();
    render();
  }
  function render() {
    const old = document.activeElement,
      key =
        old?.dataset?.cluster !== undefined
          ? ["cluster", old.dataset.cluster]
          : old?.dataset?.area !== undefined
            ? ["area", old.dataset.area]
            : old?.dataset?.week
              ? ["week", old.dataset.week]
              : null;
    const list = rows(),
      mapped = list.filter(validPoint),
      groups = new Set(list.map((p) => p.cluster).filter(Boolean));
    $("updated").textContent =
      "归档更新于 " + (data.generated_at || "").slice(0, 10);
    $("status").textContent = `${list.length} 篇论文 · ${groups.size} 个研究簇`;
    $("selection").textContent = [
      area ? areaName(area) : "全部领域",
      cluster ? clusterName(cluster) : "全部研究簇",
      windowDays ? "近 " + windowDays + " 天" : "全部归档",
      week ? "周区间 " + week : "",
    ]
      .filter(Boolean)
      .join(" / ");
    document
      .querySelectorAll("[data-window]")
      .forEach((b) =>
        b.setAttribute(
          "aria-pressed",
          String(Number(b.dataset.window) === windowDays),
        ),
      );
    $("map-count").textContent = mapped.length + " 个点";
    $("unmapped").textContent =
      list.length - mapped.length
        ? `${list.length - mapped.length} 篇未绘制在地图上，可在下方列表阅读。`
        : "";
    const crows = rows("cluster"),
      counters = new Map();
    for (const p of crows) {
      const id = p.cluster || "unclustered";
      counters.set(id, (counters.get(id) || 0) + 1);
    }
    $("clusters").innerHTML =
      '<button data-cluster="" aria-pressed="' +
      !cluster +
      '">全部研究簇<small>' +
      crows.length +
      "</small></button>" +
      [
        ...[...data.clusters].sort(
          (a, b) => (counters.get(b.id) || 0) - (counters.get(a.id) || 0),
        ),
        { id: "unclustered", label: "未聚类" },
      ]
        .map(
          (c) =>
            `<button data-cluster="${esc(c.id)}" aria-pressed="${cluster === c.id}" title="${esc((c.terms || []).join(", "))}"><span class="swatch" style="background:${c.id === "unclustered" ? "#8b96a5" : color(c.id)}"></span><span>${esc(c.label)}</span><small>${counters.get(c.id) || 0}</small></button>`,
        )
        .join("");
    const ac = new Map();
    for (const p of rows("area"))
      ac.set(p.area || "other", (ac.get(p.area || "other") || 0) + 1);
    const areas = [...data.areas];
    if (!areas.some((a) => a.id === "other"))
      areas.push({ id: "other", label: "领域待定" });
    areas.sort(
      (a, b) =>
        (ac.get(b.id) || 0) - (ac.get(a.id) || 0) ||
        a.label.localeCompare(b.label),
    );
    const max = Math.max(1, ...ac.values());
    $("areas").innerHTML = areas
      .map(
        (a) =>
          `<button data-area="${esc(a.id)}" aria-pressed="${area === a.id}"><span class="bar-fill" style="width:${(100 * (ac.get(a.id) || 0)) / max}%"></span><span>${esc(a.label)}</span><span>${ac.get(a.id) || 0}</span></button>`,
      )
      .join("");
    const monday = new Date(anchor());
    monday.setUTCDate(monday.getUTCDate() - ((monday.getUTCDay() + 6) % 7));
    const starts = Array.from(
        { length: 12 },
        (_, i) => monday.getTime() - (11 - i) * 7 * 86400000,
      ),
      tr = rows("week"),
      bins = starts.map(
        (start) =>
          tr.filter(
            (p) =>
              dateNumber(p.date) >= start &&
              dateNumber(p.date) < start + 7 * 86400000,
          ).length,
      ),
      peak = Math.max(1, ...bins);
    $("trend").innerHTML = starts
      .map((start, i) => {
        const day = new Date(start).toISOString().slice(0, 10);
        return `<button data-week="${day}" aria-pressed="${week === day}" aria-label="${day} 起的一周：${bins[i]} 篇论文"><span>${bins[i]}</span><span class="week-bar" style="height:${Math.max(2, (110 * bins[i]) / peak)}px"></span><small>${day.slice(5)}</small></button>`;
      })
      .join("");
    const dated = tr.filter((p) => Number.isFinite(dateNumber(p.date))).length;
    $("date-note").textContent =
      `当前领域与研究簇中，${dated} 篇有发表日期，其中 ${bins.reduce((sum, n) => sum + n, 0)} 篇在图示 12 周内。${tr.length - dated} 篇日期待补充。按周一分组，当前周截至归档日期。`;
    $("coverage").textContent =
      `收录 ${data.papers.length} 篇研究论文。时间窗口按发表日期筛选，日期待补充的论文可在“全部归档”查看。期刊相关性待确认 ${data.excluded_pending || 0} 篇，另见阅读站。`;
    $("share").href = location.href;
    renderList();
    draw();
    if (key)
      document
        .querySelector(`[data-${key[0]}="${CSS.escape(key[1])}"]`)
        ?.focus({ preventScroll: true });
  }
  function renderList() {
    const list = rows().sort(
      (a, b) =>
        (dateNumber(b.date) || 0) - (dateNumber(a.date) || 0) ||
        a.id.localeCompare(b.id),
    );
    $("paper-count").textContent = list.length + " 篇";
    $("list").innerHTML = list.length
      ? list
          .slice(0, shown)
          .map(
            (p) =>
              `<article class="paper ${selected === p.id ? "selected" : ""}" id="paper-${esc(p.id)}"><div class="paper-meta"><span>${esc(p.date || "发表日期待补充")}</span><button data-area="${esc(p.area || "other")}">${esc(areaName(p.area || "other"))}</button><button data-cluster="${esc(p.cluster || "unclustered")}">${esc(clusterName(p.cluster))}</button></div><h3><a href="${esc(safeURL(p.url))}" target="_blank" rel="noopener noreferrer">${esc(p.title)}</a></h3><div class="paper-meta"><a href="./#item-${encodeURIComponent(p.id)}">在阅读站查看摘要与分类</a></div></article>`,
          )
          .join("")
      : '<div class="empty">这个组合暂无论文。调整领域、研究簇或时间窗口，或<button data-reset>清除筛选</button>。</div>';
    $("more").hidden = shown >= list.length;
    $("selected-paper").textContent = selected ? "已定位地图中的论文" : "";
  }
  function draw() {
    const canvas = $("map"),
      box = canvas.getBoundingClientRect(),
      ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(box.width * ratio));
    canvas.height = Math.max(1, Math.round(box.height * ratio));
    const c = canvas.getContext("2d");
    if (!c) return;
    c.scale(ratio, ratio);
    points = rows()
      .filter(validPoint)
      .map((p) => ({
        p,
        x: 18 + p.x * (box.width - 36),
        y: 18 + (1 - p.y) * (box.height - 36),
      }));
    c.strokeStyle = "#e7edf5";
    c.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
      c.beginPath();
      c.moveTo((i * box.width) / 5, 0);
      c.lineTo((i * box.width) / 5, box.height);
      c.stroke();
      c.beginPath();
      c.moveTo(0, (i * box.height) / 5);
      c.lineTo(box.width, (i * box.height) / 5);
      c.stroke();
    }
    for (const pt of points) {
      c.beginPath();
      c.fillStyle = pt.p.cluster ? color(pt.p.cluster) : "#8b96a5";
      c.globalAlpha = selected === pt.p.id ? 1 : 0.7;
      c.arc(pt.x, pt.y, selected === pt.p.id ? 6 : 3.5, 0, 2 * Math.PI);
      c.fill();
    }
    c.globalAlpha = 1;
  }
  function closest(event) {
    const b = $("map").getBoundingClientRect(),
      x = event.clientX - b.left,
      y = event.clientY - b.top;
    let near = null,
      distance = 144;
    for (const pt of points) {
      const d = (pt.x - x) ** 2 + (pt.y - y) ** 2;
      if (d < distance) {
        distance = d;
        near = pt.p;
      }
    }
    return near;
  }
  async function load() {
    $("status").textContent = "正在读取研究图谱…";
    try {
      const response = await fetch("./data/landscape.json", {
        cache: "no-cache",
        signal: AbortSignal.timeout(15000),
      });
      if (!response.ok) throw Error("unavailable");
      const next = await response.json();
      if (
        next.schema_version !== 1 ||
        !Array.isArray(next.papers) ||
        !Array.isArray(next.clusters) ||
        !Array.isArray(next.areas)
      )
        throw Error("invalid");
      data = next;
      $("visuals").hidden = false;
      readURL();
      render();
    } catch {
      $("status").innerHTML =
        '图谱暂时无法读取。<button id="retry">重新加载</button> 或 <a href="./">返回阅读站</a>';
      $("retry").onclick = load;
    }
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || !data) return;
    if (b.dataset.window !== undefined) {
      windowDays = Number(b.dataset.window);
      week = "";
      change();
    } else if (b.dataset.cluster !== undefined) {
      cluster = cluster === b.dataset.cluster ? "" : b.dataset.cluster;
      change();
    } else if (b.dataset.area !== undefined) {
      area = area === b.dataset.area ? "" : b.dataset.area;
      change();
    } else if (b.dataset.week) {
      week = week === b.dataset.week ? "" : b.dataset.week;
      change();
    } else if (b.id === "clear" || b.dataset.reset !== undefined) {
      area = "";
      cluster = "";
      week = "";
      windowDays = 0;
      change();
    }
  });
  $("more").onclick = () => {
    shown += 30;
    renderList();
  };
  $("map").addEventListener("pointermove", (e) => {
    const p = closest(e);
    $("hover").hidden = !p;
    if (p) $("hover").textContent = p.title;
    $("map").style.cursor = p ? "pointer" : "default";
  });
  $("map").addEventListener("pointerleave", () => {
    $("hover").hidden = true;
  });
  $("map").addEventListener("click", (e) => {
    const p = closest(e);
    if (!p) return;
    selected = p.id;
    const list = rows().sort(
      (a, b) =>
        (dateNumber(b.date) || 0) - (dateNumber(a.date) || 0) ||
        a.id.localeCompare(b.id),
    );
    shown = Math.max(shown, list.findIndex((x) => x.id === p.id) + 1);
    renderList();
    draw();
    document
      .getElementById("paper-" + p.id)
      ?.scrollIntoView({
        block: "center",
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
  });
  window.addEventListener("popstate", () => {
    if (data) {
      readURL();
      render();
    }
  });
  new ResizeObserver(() => {
    if (data) draw();
  }).observe($("map"));
  load();
})();
