fn main() {
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "dashboard_state",
            "dashboard_action",
            "logs_start",
            "logs_stop",
            "system_metrics",
        ]),
    ))
    .expect("Tauri build failed");
}
