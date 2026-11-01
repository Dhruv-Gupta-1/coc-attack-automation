import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_DIR / "main.py"
ICON_PATH = APP_DIR / "assets" / "coc_logo.ico"

def create_coc_desktop_shortcut() -> str:
    """
    Creates a Windows desktop shortcut for COC Attacker Bot with the custom CoC logo.
    """
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
    shortcut_path = desktop / "COC Attacker Bot.lnk"

    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    # PowerShell script to create Windows shell shortcut
    ps_command = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{pythonw}"
    $Shortcut.Arguments = '"{MAIN_SCRIPT}"'
    $Shortcut.WorkingDirectory = "{APP_DIR}"
    $Shortcut.Description = "COC Attacker Bot — Autonomous Visual Bot for Clash of Clans"
    $Shortcut.IconLocation = "{ICON_PATH},0"
    $Shortcut.Save()
    """

    import subprocess
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True)
    if result.returncode == 0 and shortcut_path.exists():
        print(f"Created CoC desktop shortcut: {shortcut_path}")
        return str(shortcut_path)
    else:
        print(f"Error creating shortcut: {result.stderr}")
        return ""

def create_launchers():
    """Creates launch.bat and launch_coc.vbs for silent launching."""
    vbs_path = APP_DIR / "launch_coc.vbs"
    bat_path = APP_DIR / "launch_coc.bat"

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{APP_DIR}"
WshShell.Run "pythonw.exe ""{MAIN_SCRIPT}""", 0, False
'''
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    bat_content = f'''@echo off
cd /d "{APP_DIR}"
start pythonw.exe main.py
exit
'''
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

if __name__ == "__main__":
    create_launchers()
    create_coc_desktop_shortcut()
