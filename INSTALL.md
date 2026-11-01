# 🛠️ Installation & Setup Guide — COC Attacker Bot

Follow these simple steps to set up and run **COC Attacker Bot** on any Windows computer.

---

## 📋 Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python**: Python 3.10 or newer (download from [python.org](https://www.python.org/downloads/)).
   > ⚠️ **Important**: During Python installation, make sure to check the box: **"Add Python to PATH"**.
3. **Game Client**: **Clash of Clans** running via:
   - **Google Play Games Beta (PC)** (Recommended), or
   - **BlueStacks 5**, **LDPlayer 9**, **NoxPlayer**, or **MuMu Player**.

---

## ⚡ Quick 1-Click Launch (Recommended)

Simply double-click:
```bat
run.bat
```
*The script automatically verifies Python, installs any missing packages from `requirements.txt`, and starts the bot dashboard!*

---

## 📦 Manual Setup (Step-by-Step)

If you prefer using the terminal (PowerShell or Command Prompt):

### Step 1: Open Terminal in the Bot Folder
```powershell
cd "COC ATTACKER BOT"
```
*(Or right-click inside the `COC ATTACKER BOT` folder and choose **"Open in Terminal"**)*

### Step 2: (Optional) Create a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🔑 Gemini AI API Configuration

The bot features a **Tactical AI Advisor** powered by Google Gemini (`gemini-3.1-flash-lite`).

You can configure your API key in **any of the 3 ways below**:

### Option A: Enter via App Startup Dialog (Easiest)
1. Launch the app (`python main.py` or double-click `run.bat`).
2. If no key is saved, the app will automatically ask:
   *"Would you like to configure your Google Gemini API Key now?"*
3. Paste your key and click **OK**.

### Option B: Enter via the GUI Header
- Click the **"🔑 Gemini API"** button at the top right of the dashboard at any time to view or update your key.

### Option C: Edit `config.json`
Open [config.json](file:///C:/Users/dhruv/Desktop/COC%20ATTACKER%20BOT/config.json) in any text editor and update:
```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "gemini_model": "gemini-3.1-flash-lite",
  "cycles": 5,
  "battle_wait_seconds": 105
}
```

> 💡 **Where to get a free API Key?**  
> Visit [Google AI Studio](https://aistudio.google.com/) and click **"Create API key"**.

*(Note: If you do not have a Gemini API key, you can skip it — the bot's visual attack cycles and troop deployment work 100% autonomously without requiring an AI key!)*

---

## 🎮 Game Configuration

1. **Launch Clash of Clans** on Google Play Games PC or your emulator.
2. Ensure your army is trained with **Dragons** and/or **Dragon Duke**.
3. Keep the game window visible (the bot will automatically restore and focus it when attack cycles start).

---

## 🚀 Running the Bot

Run the dashboard:
```powershell
python main.py
```

### Operating Controls:
- **▶ START ATTACK CYCLE**: Begins the autonomous 10-step verified attack cycle.
- **⏹ STOP ATTACK CYCLE**: Halts the sequence safely at any time.
- **💰 Collect Loot**: One-click sweep to harvest all Gold & Elixir collectors in your village.
- **📸 Snip Icon**: Capture custom in-game icons directly from your screen.
- **🤖 AI Advisor**: Click "Analyze Live Base Screenshot" to get instant tactical advice on loot and troop placement.
- **🛡️ Safety Emergency Failsafe**: Slam your mouse cursor to the top-left corner `(0, 0)` of your screen to abort instantly.

---

## ❓ Troubleshooting

| Issue | Solution |
|---|---|
| `No module named 'cv2'` or `win32gui` | Run `pip install -r requirements.txt`. |
| "Game window not found" | Make sure Clash of Clans is running and visible in your taskbar. |
| Inactivity disconnect ("Anyone there?") | The bot automatically detects the reload prompt, clicks "RELOAD GAME", and waits for the village to reload. |
| Window minimized off-screen | The bot uses low-level Win32 focus restoration to automatically bring the game to the foreground. |
