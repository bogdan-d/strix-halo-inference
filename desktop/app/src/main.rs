mod dashboard;
mod metrics;
mod runtime;
#[cfg(feature = "agent-debug")]
mod window_check;

use std::{env, fs, path::PathBuf, time::Duration};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use webkit2gtk::WebViewExt;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = env::var_os("INFERENCE_ROOT")
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?)
        .canonicalize()?;
    if !root.join("bin/run.sh").is_file() || !root.join("bin/weights.py").is_file() {
        return Err("Run from the inference checkout".into());
    }
    let Some(instance) = runtime::instance(&root)? else {
        return Ok(());
    };
    runtime::logs(&root)?;
    let inspect = env::var_os("WEBKIT_INSPECTOR_HTTP_SERVER").is_some();
    let record = root.join("cache/desktop/inspector");
    if let Ok(address) = env::var("WEBKIT_INSPECTOR_HTTP_SERVER") {
        use std::{io::Write, os::unix::fs::OpenOptionsExt};
        let mut file = fs::OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .mode(0o600)
            .open(&record)?;
        writeln!(file, "{address}")?;
    } else {
        let _ = fs::remove_file(&record);
    }
    let state_path = root.join("cache/desktop/window-state.json");
    let profile = root.join("cache/desktop/profile");
    let context = tauri::generate_context!();
    gtk::glib::set_prgname(Some(&context.config().identifier));
    let builder = tauri::Builder::default()
        .manage(dashboard::Backend::new(root))
        .invoke_handler(tauri::generate_handler![
            dashboard::dashboard_state,
            dashboard::dashboard_action,
            dashboard::logs_start,
            dashboard::logs_stop,
            metrics::system_metrics
        ]);
    let app = builder.setup(move |app| {
        let saved = runtime::WindowState::load(&state_path);
        let window = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
            .title("Strix Halo Inference")
            .visible(false)
            .inner_size(saved.width as f64, saved.height as f64)
            .data_directory(profile)
            .devtools(inspect)
            .on_navigation(|url| url.scheme() == "tauri"
                || (url.scheme() == "http" && url.host_str() == Some("tauri.localhost")))
            .on_page_load(|view, _| view.state::<dashboard::Backend>().stop_logs(None))
            .build()?;
        runtime::remember_window(&window, saved.clone(), state_path)?;
        if saved.maximized { window.maximize()?; }
        if saved.fullscreen { window.set_fullscreen(true)?; }
        window.show()?;

        let handle = app.handle().clone();
        window.with_webview(move |native| {
            native.inner().connect_web_process_terminated(move |_, reason| {
                eprintln!("Renderer terminated: {reason:?}");
                handle.state::<dashboard::Backend>().stop_logs(None);
            });
        })?;
        let handle = app.handle().clone();
        window.on_window_event(move |event| match event {
            tauri::WindowEvent::CloseRequested { api, .. }
                if handle.state::<dashboard::Backend>().is_busy() => {
                    api.prevent_close();
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.eval("document.getElementById('notice').textContent='An operation is running. Wait for it to finish before closing.'");
                    }
                }
            tauri::WindowEvent::Destroyed => handle.state::<dashboard::Backend>().stop_logs(None),
            _ => {}
        });
        runtime::focus_listener(instance, app.handle().clone());
        #[cfg(feature = "agent-debug")]
        if let Ok(stage) = env::var("INFERENCE_WINDOW_CHECK") {
            window_check::start(app.handle().clone(), stage);
        }
        Ok(())
    }).build(context)?;
    app.run(|handle, event| {
        if let tauri::RunEvent::ExitRequested { api, .. } = event {
            let backend = handle.state::<dashboard::Backend>();
            if backend.has_viewers() {
                // Reap viewers before the async runtime exits; engine monitors are not owned here.
                api.prevent_exit();
                backend.stop_logs(None);
                let handle = handle.clone();
                tauri::async_runtime::spawn(async move {
                    while handle.state::<dashboard::Backend>().has_viewers() {
                        tokio::time::sleep(Duration::from_millis(20)).await;
                    }
                    handle.exit(0);
                });
            }
        }
    });
    Ok(())
}
