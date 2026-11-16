use serde::Serialize;
use std::{
    fs,
    path::{Path, PathBuf},
};
use tauri::Webview;

#[derive(Debug, Serialize, PartialEq)]
pub struct Memory {
    used: u64,
    total: u64,
}

#[derive(Serialize)]
pub struct Metrics {
    gpu_percent: Option<u64>,
    cpu_temperature_c: Option<f64>,
    gpu_temperature_c: Option<f64>,
    power_w: Option<f64>,
    ram: Option<Memory>,
    gtt: Option<Memory>,
    swap: Option<Memory>,
}

fn counter(path: &Path) -> Option<u64> {
    fs::read_to_string(path).ok()?.trim().parse().ok()
}

fn memory(used: Option<u64>, total: Option<u64>) -> Option<Memory> {
    let (used, total) = (used?, total?);
    (used <= total).then_some(Memory { used, total })
}

fn meminfo(text: &str, total_key: &str, free_key: &str) -> Option<Memory> {
    let value = |key: &str| {
        let line = text.lines().find(|line| line.starts_with(key))?;
        let mut parts = line[key.len()..].split_whitespace();
        let value: u64 = parts.next()?.parse().ok()?;
        (parts.next()? == "kB").then_some(())?;
        value.checked_mul(1024)
    };
    let total = value(total_key)?;
    memory(total.checked_sub(value(free_key)?), Some(total))
}

fn gpu_device() -> Option<PathBuf> {
    let mut cards: Vec<_> = fs::read_dir("/sys/class/drm")
        .ok()?
        .filter_map(Result::ok)
        .filter(|entry| {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            name.strip_prefix("card").is_some_and(|suffix| {
                !suffix.is_empty() && suffix.bytes().all(|b| b.is_ascii_digit())
            })
        })
        .map(|entry| entry.path().join("device"))
        .collect();
    cards.sort();
    cards.into_iter().find(|device| {
        fs::read_link(device.join("driver"))
            .ok()
            .is_some_and(|driver| driver.file_name().is_some_and(|name| name == "amdgpu"))
    })
}

fn hwmon_device(root: &Path, name: &str) -> Option<PathBuf> {
    fs::read_dir(root)
        .ok()?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .find(|path| fs::read_to_string(path.join("name")).is_ok_and(|value| value.trim() == name))
}

fn sample() -> Metrics {
    let info = fs::read_to_string("/proc/meminfo").unwrap_or_default();
    let gpu = gpu_device();
    let gpu_counter = |name: &str| counter(&gpu.as_ref()?.join(name));
    let hwmon = gpu
        .as_ref()
        .and_then(|device| hwmon_device(&device.join("hwmon"), "amdgpu"));
    let cpu = hwmon_device(Path::new("/sys/class/hwmon"), "k10temp");
    let sensor = |name: &str| counter(&hwmon.as_ref()?.join(name));
    Metrics {
        gpu_percent: gpu_counter("gpu_busy_percent").filter(|value| *value <= 100),
        cpu_temperature_c: cpu
            .and_then(|path| counter(&path.join("temp1_input")))
            .map(|value| value as f64 / 1000.0),
        gpu_temperature_c: sensor("temp1_input").map(|value| value as f64 / 1000.0),
        power_w: sensor("power1_average")
            .or_else(|| sensor("power1_input"))
            .map(|value| value as f64 / 1_000_000.0),
        ram: meminfo(&info, "MemTotal:", "MemAvailable:"),
        gtt: memory(
            gpu_counter("mem_info_gtt_used"),
            gpu_counter("mem_info_gtt_total"),
        ),
        swap: meminfo(&info, "SwapTotal:", "SwapFree:"),
    }
}

#[tauri::command]
pub async fn system_metrics(webview: Webview) -> Result<Metrics, String> {
    crate::dashboard::authorize(&webview)?;
    tauri::async_runtime::spawn_blocking(sample)
        .await
        .map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ram_uses_available_and_swap_uses_free_in_bytes() {
        let info = "MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 400 kB\nSwapTotal: 200 kB\nSwapFree: 150 kB\n";
        assert_eq!(
            meminfo(info, "MemTotal:", "MemAvailable:"),
            Some(Memory {
                used: 600 * 1024,
                total: 1000 * 1024
            })
        );
        assert_eq!(
            meminfo(info, "SwapTotal:", "SwapFree:"),
            Some(Memory {
                used: 50 * 1024,
                total: 200 * 1024
            })
        );
    }

    #[test]
    fn missing_or_invalid_memory_is_unavailable_not_zero() {
        for info in [
            "",
            "MemTotal: 100 kB",
            "MemTotal: 100 kB\nMemAvailable: 101 kB",
            "MemTotal: broken kB\nMemAvailable: 1 kB",
            "MemTotal: 100 MB\nMemAvailable: 1 kB",
            "MemTotal: 18446744073709551615 kB\nMemAvailable: 1 kB",
        ] {
            assert_eq!(meminfo(info, "MemTotal:", "MemAvailable:"), None);
        }
        assert_eq!(memory(None, Some(100)), None);
        assert_eq!(memory(Some(101), Some(100)), None);
        assert_eq!(memory(Some(0), Some(0)), Some(Memory { used: 0, total: 0 }));
    }
}
