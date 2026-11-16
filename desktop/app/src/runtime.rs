//! Linux desktop integration, using the same GTK runtime as the WebViews.
use gtk::prelude::*;
use serde::{Deserialize, Serialize};
use std::{
    collections::hash_map::DefaultHasher,
    fs::{self, File, OpenOptions},
    hash::{Hash, Hasher},
    io::{Read, Write},
    os::{
        fd::{AsRawFd, FromRawFd},
        linux::net::SocketAddrExt,
        unix::{
            fs::OpenOptionsExt,
            net::{SocketAddr, UnixDatagram, UnixStream},
        },
    },
    path::Path,
};
use tauri::Manager;

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct WindowState {
    pub width: i32,
    pub height: i32,
    pub maximized: bool,
    pub fullscreen: bool,
}

impl Default for WindowState {
    fn default() -> Self {
        Self {
            width: 1200,
            height: 800,
            maximized: false,
            fullscreen: false,
        }
    }
}

impl WindowState {
    pub fn load(path: &Path) -> Self {
        match fs::read(path) {
            Ok(bytes) => match serde_json::from_slice::<Self>(&bytes) {
                Ok(state) if state.width > 0 && state.height > 0 => state,
                _ => {
                    eprintln!("Ignoring invalid window state: {}", path.display());
                    Self::default()
                }
            },
            Err(error) => {
                if error.kind() != std::io::ErrorKind::NotFound {
                    eprintln!("Cannot read window state: {error}");
                }
                Self::default()
            }
        }
    }
}

// GTK sizes are logical pixels. Keep normal geometry separate from maximized/fullscreen geometry.
pub fn remember_window(
    window: &tauri::WebviewWindow,
    saved: WindowState,
    path: std::path::PathBuf,
) -> tauri::Result<()> {
    use gtk::gdk::WindowState as Flags;
    use std::{cell::RefCell, rc::Rc};
    let native = window.gtk_window()?;
    // Handle F11 before GTK forwards the key to whichever WebView has focus.
    let handle = window.clone();
    native.connect_key_press_event(move |window, event| {
        if event.keyval() != gtk::gdk::keys::constants::F11
            || event
                .state()
                .intersects(gtk::accelerator_get_default_mod_mask())
        {
            return gtk::glib::Propagation::Proceed;
        }
        let fullscreen = window
            .window()
            .is_some_and(|w| w.state().contains(Flags::FULLSCREEN));
        if let Err(error) = handle.set_fullscreen(!fullscreen) {
            eprintln!("Cannot toggle fullscreen: {error}");
        }
        gtk::glib::Propagation::Stop
    });
    let state = Rc::new(RefCell::new(saved));
    let resized = state.clone();
    native.connect_configure_event(move |window, _| {
        let flags = window
            .window()
            .map(|w| w.state())
            .unwrap_or_else(Flags::empty);
        if !flags.intersects(Flags::MAXIMIZED | Flags::FULLSCREEN | Flags::ICONIFIED) {
            let (width, height) = window.size();
            if width > 0 && height > 0 {
                let mut state = resized.borrow_mut();
                state.width = width;
                state.height = height;
            }
        }
        false
    });
    let changed = state.clone();
    native.connect_window_state_event(move |window, event| {
        let flags = event.new_window_state();
        let mut state = changed.borrow_mut();
        let fullscreen = flags.contains(Flags::FULLSCREEN);
        let restore_maximized = state.fullscreen && !fullscreen && state.maximized;
        state.fullscreen = fullscreen;
        // Fullscreen must remember whether it was entered from a maximized window.
        if !state.fullscreen {
            state.maximized = restore_maximized || flags.contains(Flags::MAXIMIZED);
        }
        drop(state);
        // Wayland may discard a maximize request made before the initial fullscreen map.
        if restore_maximized && !flags.contains(Flags::MAXIMIZED) {
            window.maximize();
        }
        gtk::glib::Propagation::Proceed
    });
    native.connect_destroy(move |_| {
        let save = || -> Result<(), Box<dyn std::error::Error>> {
            fs::create_dir_all(path.parent().unwrap())?;
            let temporary = path.with_extension("json.tmp");
            fs::write(&temporary, serde_json::to_vec(&*state.borrow())?)?;
            fs::rename(temporary, &path)?;
            Ok(())
        };
        if let Err(error) = save() {
            eprintln!("Cannot save window state: {error}");
        }
    });
    Ok(())
}

// A second launch can only focus the existing window; this socket exposes no commands or data.
pub fn instance(root: &Path) -> std::io::Result<Option<UnixDatagram>> {
    let mut hash = DefaultHasher::new();
    root.hash(&mut hash);
    let address = SocketAddr::from_abstract_name(format!(
        "inference-{}-{:x}",
        unsafe { libc::getuid() },
        hash.finish()
    ))?;
    match UnixDatagram::bind_addr(&address) {
        Ok(socket) => Ok(Some(socket)),
        Err(error) if error.kind() == std::io::ErrorKind::AddrInUse => {
            UnixDatagram::unbound()?.send_to_addr(b"focus", &address)?;
            eprintln!("Inference is already running. Focused its window. For inspection, close it and run --inspect.");
            Ok(None)
        }
        Err(error) => Err(error),
    }
}

pub fn focus_listener(socket: UnixDatagram, app: tauri::AppHandle) {
    std::thread::spawn(move || {
        let mut data = [0; 16];
        while let Ok(size) = socket.recv(&mut data) {
            if &data[..size] == b"focus" {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.unminimize();
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        }
    });
}

// Capture native WebKit/GStreamer stderr as well as Rust output, with no logging service.
pub fn logs(root: &Path) -> std::io::Result<()> {
    let path = root.join("cache/desktop/app.log");
    fs::create_dir_all(path.parent().unwrap())?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .mode(0o600)
        .open(&path)?;
    let mut size = file.metadata()?.len();
    let (mut reader, writer) = UnixStream::pair()?;
    let terminal_fd = unsafe { libc::dup(libc::STDOUT_FILENO) };
    if terminal_fd < 0 {
        return Err(std::io::Error::last_os_error());
    }
    let mut terminal = unsafe { File::from_raw_fd(terminal_fd) };
    for fd in [libc::STDOUT_FILENO, libc::STDERR_FILENO] {
        if unsafe { libc::dup2(writer.as_raw_fd(), fd) } < 0 {
            return Err(std::io::Error::last_os_error());
        }
    }
    std::thread::spawn(move || {
        let mut buffer = [0; 8192];
        while let Ok(count) = reader.read(&mut buffer) {
            if count == 0 {
                break;
            }
            if size + count as u64 > 2 * 1024 * 1024 {
                let _ = fs::rename(&path, path.with_extension("log.1"));
                match OpenOptions::new()
                    .create(true)
                    .truncate(true)
                    .write(true)
                    .mode(0o600)
                    .open(&path)
                {
                    Ok(new_file) => {
                        file = new_file;
                        size = 0;
                    }
                    Err(_) => break,
                }
            }
            let _ = file.write_all(&buffer[..count]);
            size += count as u64;
            let _ = terminal.write_all(&buffer[..count]);
        }
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn second_launch_only_requests_focus() {
        let root =
            std::env::temp_dir().join(format!("inference-instance-test-{}", std::process::id()));
        let socket = instance(&root).unwrap().unwrap();
        socket
            .set_read_timeout(Some(std::time::Duration::from_secs(1)))
            .unwrap();
        assert!(instance(&root).unwrap().is_none());
        let mut message = [0; 16];
        let size = socket.recv(&mut message).unwrap();
        assert_eq!(&message[..size], b"focus");
    }
}
