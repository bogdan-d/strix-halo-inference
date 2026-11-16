(() => {
const metrics = document.querySelector<HTMLElement>("#metrics")!;
const metricNames = ["gpu", "ram", "cpu_temperature", "gpu_temperature", "power"] as const;
type MetricName = typeof metricNames[number];
const history: {time: number; values: Record<MetricName, number|null>}[] = [];
const historyWindow = 120_000;
function setGraphMode(graphs: boolean) {
    metrics.classList.toggle("graphs", graphs);
    metrics.setAttribute("aria-pressed", String(graphs));
    metrics.setAttribute("aria-label", graphs ? "Show numeric metrics" : "Show metric history graphs");
}
try { setGraphMode(localStorage.getItem("metrics-view") === "graphs"); }
catch (error) { console.warn("Cannot restore metrics view", error); }
metrics.addEventListener("click", () => {
    const graphs = !metrics.classList.contains("graphs");
    setGraphMode(graphs);
    try { localStorage.setItem("metrics-view", graphs ? "graphs" : "numbers"); }
    catch (error) { console.warn("Cannot save metrics view", error); }
});
function recordMetrics(value: SystemMetrics|null) {
    const now = performance.now();
    history.push({time: now, values: {
        gpu: value?.gpu_percent ?? null,
        ram: value?.ram && value.ram.total > 0 ? value.ram.used / value.ram.total * 100 : null,
        cpu_temperature: value?.cpu_temperature_c ?? null,
        gpu_temperature: value?.gpu_temperature_c ?? null,
        power: value?.power_w ?? null,
    }});
    while (history.length && history[0].time < now - historyWindow) history.shift();
    for (const name of metricNames) {
        const temperature = name === "cpu_temperature" || name === "gpu_temperature";
        const peak = Math.max(0, ...history.map(sample => temperature
            ? Math.max(sample.values.cpu_temperature ?? 0, sample.values.gpu_temperature ?? 0)
            : sample.values[name] ?? 0));
        const ceiling = name === "power" ? Math.max(10, Math.ceil(peak / 10) * 10)
            : temperature ? Math.max(100, Math.ceil(peak / 10) * 10) : 100;
        let path = "";
        let previousTime: number|null = null;
        for (const sample of history) {
            const reading = sample.values[name];
            if (reading === null) { previousTime = null; continue; }
            const x = ((sample.time - (now - historyWindow)) / historyWindow * 100).toFixed(2);
            const y = (17 - Math.min(1, Math.max(0, reading / ceiling)) * 16).toFixed(2);
            // Leave gaps for failed reads and periods when the window was hidden.
            const connected = previousTime !== null && sample.time - previousTime < 5000;
            path += connected ? ` L${x} ${y}` : ` M${x} ${y} L${x} ${y}`;
            previousTime = sample.time;
        }
        const line = document.querySelector(`[data-metric="${name}"]`)!;
        line.setAttribute("d", path.trim());
        line.closest("svg")!.setAttribute("data-scale-max", String(ceiling));
    }
}
const gib = (bytes: number) => (bytes / 1024 ** 3).toFixed(1);
const degrees = (value: number|null|undefined) => value != null ? `${Math.round(value)}°C` : "—";
const memoryText = (value: MemoryUsage|null) => value ? `${gib(value.used)} / ${gib(value.total)} GiB` : "—";
function showMetrics(value: SystemMetrics|null) {
    recordMetrics(value);
    const show = (name: string, text: string) => {
        document.querySelector(`#metric-${name} b`)!.textContent = text;
    };
    show("gpu", value?.gpu_percent != null ? `${value.gpu_percent}%` : "—");
    show("ram", memoryText(value?.ram ?? null));
    show("temperature", `${degrees(value?.cpu_temperature_c)} / ${degrees(value?.gpu_temperature_c)}`);
    show("power", value?.power_w != null ? `${value.power_w.toFixed(1)} W` : "—");
    document.querySelector<HTMLElement>("#metric-ram")!.title = value
        ? `Kernel-accounted RAM: total minus MemAvailable.
GTT (all GPU users): ${memoryText(value.gtt)}
Swap: ${memoryText(value.swap)}
RAM and GTT overlap; do not add them.${document.getElementById("status-halogen")?.textContent !== "stopped" ? "\nHalogen pinned weights may still appear reclaimable in MemAvailable." : ""}`
        : "System memory unavailable";
    const powerScale = document.querySelector("#metric-power svg")!.getAttribute("data-scale-max");
    document.querySelector<HTMLElement>("#metric-power")!.title = `APU package power, including CPU; not wall power. Graph: 0–${powerScale} W, last 2 minutes.`;
}
async function refreshMetrics() {
    if (!document.hidden) {
        try {
            showMetrics(await window.__TAURI__!.core.invoke<SystemMetrics>("system_metrics"));
            metrics.title = "Click to toggle graphs · last 2 minutes · GPU/RAM: 0–100%; temperature: 0–100°C (expands if needed); power: auto-scaled";
        } catch (error) {
            showMetrics(null);
            metrics.title = `System metrics unavailable: ${String(error)}`;
        }
    }
    // Schedule after completion so slow sensor reads never overlap.
    window.setTimeout(refreshMetrics, 2000);
}
void refreshMetrics();

})();
