use std::io::{Read, Write};
use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

struct OrchestratorProcess(Mutex<Option<Child>>);

fn wait_for_orchestrator(timeout: Duration) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", 8000)) {
            let request = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
            if stream.write_all(request).is_ok() {
                let mut response = String::new();
                if stream.read_to_string(&mut response).is_ok()
                    && response.contains("200 OK")
                    && response.contains("b3-orchestrator-server")
                {
                    return Ok(());
                }
            }
        }

        if Instant::now() >= deadline {
            return Err("orchestrator did not become healthy on http://127.0.0.1:8000".to_string());
        }
        thread::sleep(Duration::from_millis(250));
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(OrchestratorProcess(Mutex::new(None)))
        .setup(|app| {
            let resource_dir = app.path().resource_dir()?;
            let orchestrator = resource_dir.join("binaries").join("orchestrator.exe");
            let data_dir = app.path().app_data_dir()?;
            let logs_dir = app.path().app_log_dir()?;
            std::fs::create_dir_all(&data_dir)?;
            std::fs::create_dir_all(&logs_dir)?;

            let child = Command::new(&orchestrator)
                .env("B3_AGENT_ENV", "desktop")
                .env("B3_AGENT_DATA_DIR", &data_dir)
                .env("B3_AGENT_LOGS_DIR", &logs_dir)
                .env("B3_AGENT_LLM_ENABLED", "false")
                .spawn()
                .map_err(|e| format!("failed to start orchestrator {:?}: {}", orchestrator, e))?;

            *app.state::<OrchestratorProcess>().0.lock().unwrap() = Some(child);

            if let Err(error) = wait_for_orchestrator(Duration::from_secs(15)) {
                if let Some(mut child) = app.state::<OrchestratorProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
                return Err(error.into());
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building B3 Investment Copilot")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(mut child) = app.state::<OrchestratorProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        });
}
