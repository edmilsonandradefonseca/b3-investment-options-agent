use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

struct OrchestratorProcess(Mutex<Option<Child>>);

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

            thread::spawn(|| {
                thread::sleep(Duration::from_millis(250));
            });

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
