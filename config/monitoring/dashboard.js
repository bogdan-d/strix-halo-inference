// @ts-check
/** @typedef {"percent"|"ratio"|"bytes"|"bytes/s"|"tokens/s"|"per-second"|"count"|"seconds"|"watts"|"celsius"|"flag"} Unit */
/** @typedef {{label: string, expr: string, of?: string, gate?: string}} Series */
/** @typedef {{title: string, sub?: string, note?: string, unit: Unit, gate?: string, window?: string, series: Series[]}} Panel */
/** @typedef {{name: string, job: string, note: string, gates: Record<string, string>, status: Panel[], tiles: Panel[], charts: Panel[], extras: Panel[]}} Section */
/** @typedef {{metric: Record<string, string>, value: [number, string], values: [number, string][]}} Sample */
/** @typedef {{start: number, end: number, step: number, instantWindow: string, rangeWindow: string}} Context */
/** @typedef {{el: HTMLElement, refresh: (context: Context) => Promise<unknown>}} Mounted */
/** @typedef {{state: "stopped"|"starting"|"ready"|"stopping"|"clearing", since: number, weights: string|null}} Engine */
/** @typedef {{monitoring: "off"|"on"|"partial"|"starting"|"stopping", engines: Record<string, Engine>, logs: string[], npu_models: string, caches: Record<string, number>, weights: Record<string, {id: string, label: string, available: boolean}[]>}} State */

// True when bin/dashboard.py serves this page. It also runs the commands behind the buttons; opened as a file, the page only reads.
const HELPER = location.protocol !== "file:";
const native = window.inferenceTransport;
const PROMETHEUS = "http://127.0.0.1:9090";
const SCRAPE = 2; // Seconds. Keep equal to scrape_interval in prometheus.yml.
const REFRESH = [1, 2, 5, 10, 15, 30];
const RANGES = /** @type {Record<string, number>} */ ({"15 min": 900, "1 h": 3600, "6 h": 21600});
const POINTS = 300;
const COLORS = ["#5ad1c5", "#f2a65a", "#8fa8ff", "#e879a6", "#b5d86b", "#c9a0ff"];
const WIDTH = 600, HEIGHT = 110;

/** @type {{host: Section, npu: Section, engines: Section[]}} */
const config = JSON.parse(/** @type {HTMLElement} */ (document.getElementById("panels")).textContent ?? "");

/** @param {string} id */
const byId = id => /** @type {HTMLElement} */ (document.getElementById(id));

/**
 * @param {string} tag
 * @param {string} className
 * @param {...(Node|string|undefined|false)} children
 */
function h(tag, className, ...children) {
  const el = document.createElement(tag);
  el.className = className;
  el.append(...children.filter(child => child !== undefined && child !== false));
  return el;
}

/** Wait for every request, even on failure, before another refresh can begin.
 * @template T
 * @param {Iterable<T|PromiseLike<T>>} values
 * @returns {Promise<Awaited<T>[]>}
 */
async function together(values) {
  const results = await Promise.allSettled(values);
  for (const result of results) if (result.status === "rejected") throw result.reason;
  return results.map(result => /** @type {PromiseFulfilledResult<Awaited<T>>} */ (result).value);
}

/**
 * @param {string} path
 * @param {Record<string, string>} params
 * @returns {Promise<Sample[]>}
 */
async function query(path, params) {
  const response = await fetch(`${PROMETHEUS}/api/v1/${path}?${new URLSearchParams(params)}`, {signal: AbortSignal.timeout(5000)});
  const body = await response.json();
  if (body.status !== "success") throw new Error(body.error);
  return body.data.result;
}

/**
 * Apply the rate window and the availability gate, so a stopped target never leaves its last reading looking current.
 * @param {Section} section @param {Panel} panel @param {Series} series @param {string} expr @param {string} window
 */
function compose(section, panel, series, expr, window) {
  const name = series.gate ?? panel.gate ?? "live";
  const gate = name === "none" ? "" : section.gates[name];
  if (gate === undefined) throw new Error(`Unknown gate ${name} in ${section.name} / ${panel.title}`);
  const body = expr.replaceAll("$__rate_interval", panel.window ?? window);
  return gate ? `(${body}) ${gate}` : body;
}

/** @param {string} template @param {Record<string, string>} metric */
const label = (template, metric) => template.replace(/\{\{(\w+)\}\}/g, (_, key) => metric[key] ?? "");

/** @param {number} value */
const digits = value => String(Math.abs(value) >= 1000 ? Math.round(value) : Number(value.toPrecision(3)));

/** @param {number} value @param {number} base @param {string[]} units @returns {[string, string]} */
function scaled(value, base, units) {
  let index = 0;
  while (Math.abs(value) >= base && index < units.length - 1) { value /= base; index++; }
  return [digits(value), units[index]];
}

/**
 * @param {number|undefined} value @param {Unit} unit
 * @returns {[string, string]} Number and unit suffix.
 */
function format(value, unit) {
  if (value === undefined || !Number.isFinite(value)) return ["—", ""];
  switch (unit) {
    case "percent": return [digits(value), "%"];
    case "ratio": return [digits(value * 100), "%"];
    case "bytes": return scaled(value, 1024, ["B", "KiB", "MiB", "GiB", "TiB"]);
    case "bytes/s": return scaled(value, 1024, ["B/s", "KiB/s", "MiB/s", "GiB/s"]);
    case "tokens/s": return [digits(value), "t/s"];
    case "per-second": return [digits(value), "/s"];
    case "count": return scaled(value, 1000, ["", "k", "M", "G"]);
    case "seconds": return value < 120 ? [digits(value), "s"] : [digits(value / 60), "min"];
    case "watts": return [digits(value), "W"];
    case "celsius": return [digits(value), "°C"];
    case "flag": return [value ? "yes" : "no", ""];
  }
}

/** @param {Section} section @param {Panel} panel @returns {Mounted} */
function chip(section, panel) {
  const el = h("span", "chip", panel.title);
  if (panel.note) el.title = panel.note;
  return {el, async refresh(context) {
    const series = panel.series[0];
    const samples = await query("query", {query: compose(section, panel, series, series.expr, context.instantWindow)});
    const failing = samples.filter(sample => Number(sample.value[1]) !== 1).map(sample => label(series.label, sample.metric));
    el.className = `chip ${samples.length === 0 ? "" : failing.length ? "bad" : "ok"}`;
    el.textContent = [panel.title, samples.length === 0 ? "unavailable" : failing.filter(Boolean).join(", ")].filter(Boolean).join(": ");
  }};
}

/** @param {Section} section @param {Panel} panel @param {boolean} small @returns {Mounted} */
function tile(section, panel, small) {
  const values = h("div", "values");
  const el = h("div", `card tile${small ? " small" : ""}`, h("div", "title", panel.title, panel.sub && h("span", "sub", panel.sub)), values);
  if (panel.note) el.title = panel.note;
  /** @param {Series} series @param {string} expr @param {Context} context */
  const instant = (series, expr, context) => query("query", {query: compose(section, panel, series, expr, context.instantWindow)});
  return {el, async refresh(context) {
    const rows = (await together(panel.series.map(async series => {
      const [samples, totals] = await together([instant(series, series.expr, context), series.of ? instant(series, series.of, context) : []]);
      return samples.map((sample, index) => ({
        label: label(series.label, sample.metric), value: Number(sample.value[1]),
        of: totals[index] && Number(totals[index].value[1]),
      }));
    }))).flat();
    const labelled = rows.length > 1;
    values.className = `values${labelled ? " multi" : ""}`;
    values.replaceChildren(...(rows.length ? rows : [{label: "", value: NaN, of: undefined}]).map(row => {
      const [number, suffix] = format(row.value, panel.unit);
      const total = row.of ? format(row.of, panel.unit).join(" ") : "";
      return h("div", "value", h("span", "num", number), h("span", "unit", suffix),
        (labelled || total) && h("span", "label", [labelled && row.label, total && `of ${total}`].filter(Boolean).join(" ")),
        !!row.of && h("div", "bar", Object.assign(h("i", ""), {style: `width:${Math.min(100, 100 * row.value / row.of)}%`})));
    }));
  }};
}

/** @param {string} tag @param {Record<string, string|number>} attributes */
function svg(tag, attributes) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [name, value] of Object.entries(attributes)) el.setAttribute(name, String(value));
  return el;
}

/** @param {Section} section @param {Panel} panel @returns {Mounted} */
function chart(section, panel) {
  const plot = svg("svg", {viewBox: `0 0 ${WIDTH} ${HEIGHT}`, preserveAspectRatio: "none"});
  const max = h("span", "max"), at = h("span", "at"), cursor = h("div", "cursor"), legend = h("div", "legend");
  const frame = h("div", "plot", plot, max, at, cursor);
  const el = h("div", "card chart", h("div", "title", panel.title), frame, legend);
  if (panel.note) el.title = panel.note;
  /** @type {{label: string, points: [number, number][]}[]} */
  let lines = [];
  /** @type {Context|undefined} */
  let shown;
  /** @type {number|undefined} */
  let hover;

  // Legend values follow the cursor, falling back to each line's newest point.
  function readout() {
    legend.replaceChildren(...lines.map((line, index) => {
      const point = hover === undefined ? line.points.at(-1)
        : line.points.reduce((best, candidate) => Math.abs(candidate[0] - /** @type {number} */ (hover)) < Math.abs(best[0] - /** @type {number} */ (hover)) ? candidate : best);
      const near = point && (hover === undefined || Math.abs(point[0] - hover) <= /** @type {Context} */ (shown).step);
      return h("span", "", Object.assign(h("i", ""), {style: `background:${COLORS[index % COLORS.length]}`}),
        line.label, h("b", "", format(near ? point[1] : undefined, panel.unit).join(" ")));
    }));
    at.textContent = hover === undefined ? "" : new Date(hover * 1000).toLocaleTimeString();
  }
  frame.addEventListener("mousemove", event => {
    if (!shown) return;
    const box = frame.getBoundingClientRect(), fraction = (event.clientX - box.left) / box.width;
    hover = shown.start + fraction * (shown.end - shown.start);
    cursor.style.cssText = `display:block;left:${event.clientX - box.left}px`;
    readout();
  });
  frame.addEventListener("mouseleave", () => { hover = undefined; cursor.style.display = "none"; readout(); });

  return {el, async refresh(context) {
    const results = await together(panel.series.map(series => query("query_range", {
      query: compose(section, panel, series, series.expr, context.rangeWindow),
      start: String(context.start), end: String(context.end), step: String(context.step),
    })));
    lines = results.flatMap((samples, index) => samples.map(sample => ({
      label: label(panel.series[index].label, sample.metric),
      points: sample.values.map(([time, value]) => /** @type {[number, number]} */ ([time, Number(value)])).filter(point => Number.isFinite(point[1])),
    })));
    shown = context;
    const top = Math.max(...lines.flatMap(line => line.points.map(point => point[1])), 0) || 1;
    /** @param {number} time */
    const x = time => ((time - context.start) / (context.end - context.start) * WIDTH).toFixed(1);
    /** @param {number} value */
    const y = value => (HEIGHT - value / top * (HEIGHT - 12)).toFixed(1);
    plot.replaceChildren(
      ...[0, 0.5, 1].map(level => svg("line", {x1: 0, x2: WIDTH, y1: y(top * level), y2: y(top * level)})),
      ...lines.map((line, index) => {
        // Break the line where samples are missing instead of interpolating across a stopped target.
        let path = "", previous = -Infinity;
        for (const [time, value] of line.points) {
          path += time - previous > context.step * 1.5 ? `M${x(time)} ${y(value)}h0` : `L${x(time)} ${y(value)}`;
          previous = time;
        }
        return svg("path", {d: path, stroke: COLORS[index % COLORS.length]});
      }));
    max.textContent = lines.length ? format(top, panel.unit).join(" ") : "no data";
    readout();
  }};
}

/** @param {Section} section @returns {Mounted} */
function mount(section) {
  const chips = section.status.map(panel => chip(section, panel));
  const tiles = section.tiles.map(panel => tile(section, panel, false));
  const charts = section.charts.map(panel => chart(section, panel));
  const extras = section.extras.map(panel => tile(section, panel, true));
  /** @param {string} className @param {Mounted[]} mounted */
  const grid = (className, mounted) => mounted.length > 0 && h("div", `grid ${className}`, ...mounted.map(item => item.el));
  const el = h("section", "", h("div", "head", h("h2", "", section.name), ...chips.map(item => item.el)), h("p", "note", section.note),
    grid("tiles", tiles), grid("charts", charts),
    extras.length > 0 && h("details", "metric-details", h("summary", "", "Additional metrics"), grid("extras", extras)));
  return {el, refresh: context => together([...chips, ...tiles, ...charts, ...extras].map(item => item.refresh(context)))};
}

/**
 * @param {string} id @param {string} key @param {string[]} options @param {string} fallback
 * @param {(value: string) => string} text @param {() => void} changed
 */
function control(id, key, options, fallback, text, changed) {
  const select = /** @type {HTMLSelectElement} */ (byId(id));
  select.append(...options.map(option => Object.assign(document.createElement("option"), {value: option, textContent: text(option)})));
  const stored = localStorage.getItem(key);
  select.value = stored !== null && options.includes(stored) ? stored : fallback;
  select.addEventListener("change", () => { localStorage.setItem(key, select.value); changed(); });
  return select;
}

const host = mount(config.host);
const idle = HELPER ? h("div", "idle", "No engine running. Start one above.")
  : h("div", "idle", "No engine running. Start one with ", h("code", "", "bin/run.sh halogen|gufo|strixite start --wait"), ".");
/** @type {Map<string, Mounted>} */
const engines = new Map();
byId("main").append(host.el, idle);

async function refresh() {
  const span = RANGES[range.value], step = Math.max(SCRAPE, Math.ceil(span / POINTS));
  // Align to the step so chart samples do not shift between polls.
  const end = Math.floor(Date.now() / 1000 / step) * step;
  /** @type {Context} */
  const context = {start: end - span, end, step, instantWindow: `${4 * SCRAPE}s`, rangeWindow: `${Math.max(4 * SCRAPE, step + SCRAPE)}s`};
  // The NPU section follows the engines; its scrape is up only while Halogen serves NPU models.
  const sections = [...config.engines, config.npu];
  const up = await query("query", {query: `up{job=~"${sections.map(section => section.job).join("|")}"} == 1`});
  const active = new Set(up.map(sample => sample.metric.job));
  for (const engine of sections) {
    const mounted = engines.get(engine.job);
    if (active.has(engine.job) && !mounted) {
      const created = mount(engine);
      engines.set(engine.job, created);
      byId("main").append(created.el);
    } else if (!active.has(engine.job) && mounted) {
      mounted.el.remove();
      engines.delete(engine.job);
    }
  }
  idle.hidden = config.engines.some(engine => engines.has(engine.job));
  await together([host, ...engines.values()].map(section => section.refresh(context)));
}

/** @type {number|undefined} */
let timer;
let polling = false;
async function poll() {
  if (polling) return;
  polling = true;
  clearTimeout(timer);
  if (!document.hidden && !offline()) {
    try {
      await refresh();
      byId("error").textContent = "";
      byId("updated").textContent = new Date().toLocaleTimeString();
    } catch (error) {
      byId("error").textContent = `Prometheus query failed: ${error instanceof Error ? error.message : error}. Is bin/monitor.sh started?`;
    }
    document.body.classList.toggle("stale", byId("error").textContent !== "");
  }
  clearTimeout(timer);
  polling = false;
  timer = setTimeout(poll, Number(interval.value) * 1000);
}

const range = control("range", "strix.range", Object.keys(RANGES), "15 min", value => value, poll);
const interval = control("refresh", "strix.refresh", REFRESH.map(String), "2", value => `${value} s`, poll);
document.addEventListener("visibilitychange", poll);

/** @type {State|undefined} */
let state;
let failure = "";
/** @type {string|undefined} */
let tab;
/** @type {AbortController|undefined} */
let stream;
/** The cache button waiting for its confirming click, if any. @type {string|undefined} */
let confirming;
/** @type {number|undefined} */
let unconfirm;
const SOURCES = [...config.engines.map(engine => ({id: engine.job, name: engine.name})),
  {id: "prometheus", name: "Prometheus"}, {id: "exporter", name: "Exporter"}, {id: "probe", name: "Probe"}];
const follow = /** @type {HTMLInputElement} */ (byId("follow"));

// Monitoring is known to be down, so its absence is a state to show rather than a query error.
const offline = () => state !== undefined && state.monitoring !== "on" && state.monitoring !== "partial";
const active = () => Object.entries(state?.engines ?? {}).find(([, engine]) => engine.state !== "stopped");

/** @param {string} id @param {string} text @param {() => void} clicked */
function button(id, text, clicked) {
  const el = /** @type {HTMLButtonElement} */ (h("button", "", text));
  el.dataset.id = id;
  el.addEventListener("click", clicked);
  return el;
}

function render() {
  const monitoring = state?.monitoring, running = active();
  byId("monitoring").className = `chip ${monitoring === "on" ? "ok" : monitoring === "partial" ? "bad" : ""}`;
  byId("monitoring").textContent = monitoring ?? "unknown";
  const monitor = /** @type {HTMLButtonElement} */ (byId("monitor"));
  monitor.textContent = monitoring === "off" ? "Start" : "Stop";
  monitor.disabled = !state || monitoring === "starting" || monitoring === "stopping";
  for (const el of /** @type {NodeListOf<HTMLButtonElement>} */ (byId("engines").querySelectorAll(".engine-start"))) {
    const engine = state?.engines[el.dataset.id ?? ""], name = SOURCES.find(source => source.id === el.dataset.id)?.name;
    const shown = engine?.state === "starting" && engine.since ? `loading ${Math.max(0, Math.round(Date.now() / 1000 - engine.since))} s` : engine?.state;
    const status = byId(`status-${el.dataset.id}`), profile = byId(`profile-${el.dataset.id}`);
    status.textContent = shown ?? "unknown";
    status.className = `chip ${engine?.state === "ready" ? "ok" : ""}`;
    profile.hidden = !engine || engine.state === "stopped";
    profile.textContent = `Running weights: ${engine?.weights ?? "unknown"}`;
    el.textContent = "Start";
    el.setAttribute("aria-label", `Start ${name}`);
    // One engine at a time: starting another needs an explicit stop first.
    el.disabled = !state || !!running;
  }
  for (const engine of config.engines) {
    const select = /** @type {HTMLSelectElement} */ (byId(`weights-${engine.job}`));
    const entries = state?.weights[engine.job] ?? [];
    const signature = JSON.stringify(entries);
    if (select.dataset.entries !== signature) {
      const previous = select.value || localStorage.getItem(`strix.weights.${engine.job}`) || "default";
      select.replaceChildren(...entries.map(entry => {
        const option = new Option(`${entry.label}${entry.available ? "" : " (not installed)"}`, entry.id);
        option.disabled = !entry.available;
        return option;
      }));
      select.value = entries.some(entry => entry.id === previous) ? previous : "default";
      select.dataset.entries = signature;
    }
    select.disabled = !state || !!running;
    const chosen = entries.find(entry => entry.id === select.value);
    const start = /** @type {HTMLButtonElement} */ (byId("engines").querySelector(`.engine-start[data-id="${engine.job}"]`));
    start.disabled ||= !chosen?.available;
  }
  const npu = /** @type {HTMLButtonElement} */ (byId("npu"));
  npu.disabled = !state || !!running || !state.weights.halogen.some(entry => entry.id === selectedWeights("halogen") && entry.available);
  npu.title = state ? `Start Halogen with NPU models ${state.npu_models}` : "";
  for (const el of /** @type {NodeListOf<HTMLButtonElement>} */ (byId("caches").childNodes)) {
    const id = el.dataset.id ?? "", engine = state?.engines[id], size = state ? format(state.caches[id] ?? 0, "bytes").join(" ") : "";
    const name = SOURCES.find(source => source.id === id)?.name;
    el.textContent = engine?.state === "clearing" ? `${name} · clearing` : confirming === id ? `Clear ${name} ${size}?` : `${name} ${size}`;
    el.className = confirming === id ? "on" : "";
    // A running engine has its cache open; bin/cache.sh refuses it too.
    el.disabled = !state || engine?.state !== "stopped" || !state.caches[id];
    el.title = "Delete this engine's prompt cache. Each conversation then processes its whole prompt once.";
  }
  const stop = /** @type {HTMLButtonElement} */ (byId("stop"));
  stop.hidden = !running || running[1].state === "clearing";
  stop.disabled = running?.[1].state === "stopping";
  stop.textContent = running ? `Stop ${SOURCES.find(source => source.id === running[0])?.name ?? "engine"}` : "Stop engine";
  for (const el of /** @type {NodeListOf<HTMLButtonElement>} */ (byId("tabs").childNodes)) {
    el.className = el.dataset.id === tab ? "on" : "";
    el.disabled = el.dataset.id !== tab && !state?.logs.includes(el.dataset.id ?? "");
  }
  byId("notice").textContent = state ? failure : native ? "Native controls unavailable. See cache/desktop/app.log." : "Controls unavailable. Is bin/dashboard.py running?";
  byId("offline").textContent = `Monitoring is ${monitoring}. Historical host and engine charts need it; engines and native header readings run without it.`;
  byId("offline").hidden = !offline();
  byId("main").hidden = offline();
  if (offline()) {
    byId("error").textContent = "";
    document.body.classList.remove("stale");
  }
}

/** @type {number|undefined} */
let watcher;
let watching = false;
async function watch() {
  if (watching) return;
  watching = true;
  clearTimeout(watcher);
  if (!document.hidden) {
    const was = offline();
    try {
      if (native) state = await native.state();
      else {
        const response = await fetch("/state", {signal: AbortSignal.timeout(5000)});
        if (!response.ok) throw new Error(await response.text());
        state = await response.json();
      }
    } catch {
      state = undefined;
    }
    render();
    if (was && !offline()) poll();
  }
  clearTimeout(watcher);
  watching = false;
  watcher = setTimeout(watch, 2000);
}

/**
 * Run one of the helper's fixed start or stop commands. Resolves once it has finished.
 * @param {string} path
 */
async function act(path) {
  failure = "";
  byId("notice").title = "";
  for (const el of /** @type {NodeListOf<HTMLButtonElement>} */ (byId("helper").querySelectorAll("button"))) el.disabled = true;
  try {
    const response = native ? await native.action(path) : await fetch(path, {method: "POST"});
    const output = (await response.text()).trim();
    if (!response.ok) {
      failure = output.split("\n").at(-1) || `Request failed: ${response.status}`;
      byId("notice").title = output;
    }
    return response.ok;
  } catch (error) {
    failure = String(error);
    return false;
  } finally {
    await watch();
  }
}

/**
 * Show one container's log and follow it until another tab opens, the drawer closes or the container exits.
 * @param {string} id
 */
async function tail(id) {
  stream?.abort();
  const controller = stream = new AbortController(), log = byId("log");
  tab = id;
  log.replaceChildren();
  byId("drawer").hidden = false;
  document.body.classList.add("logs");
  follow.checked = true;
  render();
  /** @param {string} text */
  const write = text => {
    if (controller.signal.aborted) return;
    log.append(text.replace(/\x1b\[[0-9;]*m/g, ""));
    while (log.childNodes.length > 2000 || (log.textContent?.length ?? 0) > 1_000_000) log.firstChild?.remove();
    if (follow.checked) log.scrollTop = log.scrollHeight;
  };
  try {
    if (native) { await native.logs(id, controller.signal, write); return; }
    const response = await fetch(`/logs/${id}`, {signal: controller.signal});
    if (!response.ok) throw new Error(await response.text());
    const reader = /** @type {ReadableStream<BufferSource>} */ (response.body).pipeThrough(new TextDecoderStream()).getReader();
    for (let part = await reader.read(); !part.done; part = await reader.read()) write(part.value);
    write("\n[log ended]\n");
  } catch (error) {
    if (!controller.signal.aborted) write(`\n[${error}]\n`);
  }
}

function closeLogs() {
  stream?.abort();
  byId("drawer").hidden = true;
  document.body.classList.remove("logs");
}

/** @param {string} engine */
function selectedWeights(engine) {
  return /** @type {HTMLSelectElement} */ (byId(`weights-${engine}`)).value;
}

if (HELPER) {
  for (const engine of config.engines) {
    const label = h("label", "weight-label", "Weights");
    const select = document.createElement("select");
    select.id = `weights-${engine.job}`;
    select.setAttribute("aria-label", `${engine.name} weights`);
    select.addEventListener("change", () => { localStorage.setItem(`strix.weights.${engine.job}`, select.value); render(); });
    label.append(select);
    const status = h("span", "chip", "unknown");
    status.id = `status-${engine.job}`;
    const profile = h("p", "running-profile");
    profile.id = `profile-${engine.job}`;
    profile.hidden = true;
    const start = button(engine.job, "Start", async () => {
      // Open the log at once, so a failed start is visible.
      if (await act(`/engine/${engine.job}/start/${selectedWeights(engine.job)}`)) tail(engine.job);
    });
    start.className = "engine-start";
    const actions = h("div", "engine-actions", start);
    if (engine.job === "halogen") {
      const npu = button("halogen-npu", "Start with NPU", async () => {
        if (await act(`/engine/halogen/start-npu/${selectedWeights("halogen")}`)) tail("halogen");
      });
      npu.id = "npu";
      actions.append(npu);
    }
    byId("engines").append(h("div", "engine-control",
      h("div", "engine-heading", h("h3", "", engine.name), status), label, actions, profile));
  }
  byId("helper").hidden = byId("logs").hidden = false;
  // Clearing deletes, so the first click only asks; a second click within five seconds clears.
  byId("caches").append(...config.engines.map(engine => button(engine.job, engine.name, () => {
    clearTimeout(unconfirm);
    if (confirming === engine.job) {
      confirming = undefined;
      act(`/cache/${engine.job}/clear`);
    } else {
      confirming = engine.job;
      unconfirm = setTimeout(() => { confirming = undefined; render(); }, 5000);
      render();
    }
  })));
  byId("tabs").append(...SOURCES.map(source => button(source.id, source.name, () => tail(source.id))));
  byId("monitor").addEventListener("click", () => act(`/monitoring/${state?.monitoring === "off" ? "start" : "stop"}`));
  byId("stop").addEventListener("click", () => { const running = active(); if (running) act(`/engine/${running[0]}/stop`); });
  byId("logs").addEventListener("click", () => {
    const available = state?.logs ?? [];
    if (byId("drawer").hidden) tail(tab && available.includes(tab) ? tab : available[0] ?? tab ?? "prometheus"); else closeLogs();
  });
  byId("close").addEventListener("click", closeLogs);
  // Scrolling up pauses following; returning to the end resumes it.
  byId("log").addEventListener("scroll", () => { const log = byId("log"); follow.checked = log.scrollHeight - log.scrollTop - log.clientHeight < 8; });
  follow.addEventListener("change", () => { if (follow.checked) byId("log").scrollTop = byId("log").scrollHeight; });
  document.addEventListener("visibilitychange", watch);
  watch().then(poll);
} else {
  poll();
}
