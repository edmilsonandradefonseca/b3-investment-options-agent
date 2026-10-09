const FOREIGN_FLOW_URL: &str = "https://fluxos.investfy.com/?tab=chart&period=ytd&investor=foreigners&chart=column&ma=28";

#[tauri::command]
fn open_foreign_flow() -> Result<(), String> {
    #[cfg(target_os = "windows")]
    let status = std::process::Command::new("rundll32.exe")
        .args(["url.dll,FileProtocolHandler", FOREIGN_FLOW_URL]).status();
    #[cfg(target_os = "macos")]
    let status = std::process::Command::new("open").arg(FOREIGN_FLOW_URL).status();
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    let status = std::process::Command::new("xdg-open").arg(FOREIGN_FLOW_URL).status();
    match status {
        Ok(value) if value.success() => Ok(()),
        _ => Err("Não foi possível abrir o navegador".into()),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_foreign_flow])
        .run(tauri::generate_context!())
        .expect("error while running B3 Investment Copilot");
}
