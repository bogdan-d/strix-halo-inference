//! Native GTK probes compiled only for explicit agent-debug builds.
use gtk::prelude::*;
use serde_json::{json, Value};
use std::time::Duration;
use tauri::{AppHandle, LogicalSize, Manager, Webview};
use webkit2gtk::WebViewExt;
async fn evaluate(view: &Webview, script: &str) -> Result<String, String> {
    let (tx, rx) = tokio::sync::oneshot::channel();
    let script = script.to_string();
    view.with_webview(move |native| {
        let page = native.inner().clone();
        webkit2gtk::glib::MainContext::default().spawn_local(async move {
            let result = page
                .evaluate_javascript_future(&script, None, None)
                .await
                .map(|value| value.to_string())
                .map_err(|e| e.to_string());
            let _ = tx.send(result);
        });
    })
    .map_err(|e| e.to_string())?;
    tokio::time::timeout(Duration::from_secs(3), rx)
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())?
}

// Send a native key through GTK's normal dispatch, not a DOM KeyboardEvent.
async fn press_f11(view: &Webview) -> Result<(), String> {
    let (tx, rx) = tokio::sync::oneshot::channel();
    view.with_webview(move |native| {
        use gtk::{gdk, glib::translate::*};
        let widget = native.inner();
        widget.grab_focus();
        let window = widget.toplevel().unwrap().window().unwrap();
        let mut event = gdk::Event::new(gdk::EventType::KeyPress)
            .downcast::<gdk::EventKey>()
            .unwrap();
        event.as_mut().keyval = gdk::keys::constants::F11.into_glib();
        event.as_mut().window = window.to_glib_full();
        event.as_mut().send_event = 1;
        event.set_device(
            window
                .display()
                .default_seat()
                .and_then(|seat| seat.keyboard())
                .as_ref(),
        );
        gtk::main_do_event(&mut event);
        let _ = tx.send(());
    })
    .map_err(|e| e.to_string())?;
    rx.await.map_err(|e| e.to_string())
}

async fn window_state_run(app: &AppHandle, stage: &str) -> Result<Value, String> {
    let window = app.get_webview_window("main").ok_or("Missing window")?;
    let dashboard = app.get_webview_window("main").ok_or("Missing dashboard")?;
    let expect = async |maximized: Option<bool>, fullscreen: bool, size: Option<(u32, u32)>| {
        for _ in 0..100 {
            let actual_size = window
                .inner_size()
                .map_err(|e| e.to_string())?
                .to_logical::<u32>(window.scale_factor().map_err(|e| e.to_string())?);
            if maximized.is_none_or(|expected| window.is_maximized().ok() == Some(expected))
                && window.is_fullscreen().map_err(|e| e.to_string())? == fullscreen
                && size.is_none_or(|(width, height)| {
                    actual_size.width == width && actual_size.height == height
                })
            {
                // Let GTK finish the corresponding state/configure events before closing.
                tokio::time::sleep(Duration::from_millis(200)).await;
                return Ok::<(), String>(());
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        Err(format!("Window state did not settle: stage={stage}, maximized={maximized:?}, fullscreen={fullscreen}, size={size:?}"))
    };
    match stage {
        "resize" => {
            expect(Some(false), false, Some((1200, 800))).await?;
            window
                .set_size(LogicalSize::new(1000, 700))
                .map_err(|e| e.to_string())?;
            expect(Some(false), false, Some((1000, 700))).await?;
        }
        "maximize" => {
            expect(Some(false), false, Some((1000, 700))).await?;
            window.maximize().map_err(|e| e.to_string())?;
            expect(Some(true), false, None).await?;
        }
        "fullscreen" => {
            expect(Some(true), false, None).await?;
            window.unmaximize().map_err(|e| e.to_string())?;
            expect(Some(false), false, Some((1000, 700))).await?;
            press_f11(dashboard.as_ref()).await?;
            expect(None, true, None).await?;
        }
        "maximized-fullscreen" => {
            expect(None, true, None).await?;
            press_f11(dashboard.as_ref()).await?;
            expect(Some(false), false, Some((1000, 700))).await?;
            window.maximize().map_err(|e| e.to_string())?;
            expect(Some(true), false, None).await?;
            press_f11(dashboard.as_ref()).await?;
            expect(None, true, None).await?;
        }
        "unfullscreen" => {
            expect(None, true, None).await?;
            press_f11(dashboard.as_ref()).await?;
            expect(Some(true), false, None).await?;
            window.unmaximize().map_err(|e| e.to_string())?;
            expect(Some(false), false, Some((1000, 700))).await?;
        }
        "normal" => expect(Some(false), false, Some((1000, 700))).await?,
        _ => return Err(format!("Unknown window-state test stage: {stage}")),
    }
    Ok(json!({"ok":true,"stage":stage}))
}
pub fn start(app: AppHandle, stage: String) {
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(Duration::from_secs(1)).await;
        if stage == "measure" {
            let window = app.get_webview_window("main").unwrap();
            let _ = window.eval("if(document.querySelector('#metrics').classList.contains('graphs'))document.querySelector('#metrics').click()");
            tokio::time::sleep(Duration::from_secs(5)).await;
            for label in ["charts", "charts-logs", "minimize-requested", "hidden"] {
                if label == "charts-logs" {
                    let _ = window
                        .eval("tail('prometheus'); if(!document.querySelector('#metrics').classList.contains('graphs'))document.querySelector('#metrics').click()");
                }
                if label == "minimize-requested" {
                    let _ = window.minimize();
                }
                if label == "hidden" {
                    let _ = window.hide();
                }
                tokio::time::sleep(Duration::from_secs(2)).await;
                eprintln!(
                    "METRIC_STAGE {}",
                    json!({"name":label,"minimized":window.is_minimized().ok(),"visible":window.is_visible().ok(),"document_hidden":evaluate(window.as_ref(),"String(document.hidden)").await.ok()})
                );
                tokio::time::sleep(Duration::from_secs(8)).await;
            }
            let _ = window.close();
            return;
        }
        let result = window_state_run(&app, &stage).await;
        eprintln!(
            "WINDOW_CHECK {}",
            match result {
                Ok(value) => value,
                Err(error) => json!({"ok":false,"error":error}),
            }
        );
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.close();
        }
    });
}
