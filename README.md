# Tiger Knight Revival（虎豹騎 復活計畫）

> **⏸ 專案已暫停（2026-11）— 歡迎接手。** 原作者目前不再開發，也可能不會回覆 issue。歡迎 fork 繼續研究；從 `notes/START_HERE.md` 開始讀。
>
> **⏸ Paused (Nov 2026) — anyone is welcome to pick it up.** The original author is no longer developing it and may not answer issues. Feel free to fork it and continue; start with `notes/START_HERE.md`.

[繁體中文](#繁體中文) | [English](#english)

---

## 繁體中文

### 這是什麼
《Tiger Knight（虎豹騎）》已經停服。這個專案用一個「假的 Pomelo 大廳伺服器」加一個「假的戰鬥伺服器」，讓你自己電腦上的 Steam 遊戲客戶端可以登入、捏角色、進戰場，做單人遊玩與研究。

- `server/lobby.py`：假大廳（通訊埠 3010-3019，TLS 憑證首次啟動時自動產生，需要 Git for Windows 內建的 openssl 或系統 openssl）。
- `server/battle_server.py`：假戰鬥伺服器（TCP 7777）。
- `tools/`：逆向與解密小工具（Python），以及遊戲內腳本修改工具。
- `notes/`：完整的分析筆記（協定格式、位址、測試紀錄）。

### 重要聲明
- 這是非官方的愛好者專案，與遊戲的發行商、開發商無任何關係。
- **本專案不包含任何遊戲檔案或資產。** 你必須自己在 Steam 上擁有《Tiger Knight》（App 415660）並安裝，所有工具都只讀你自己的遊戲副本。
- 目的僅為保存與互通性研究。遊戲名稱、商標與著作權屬於各自的擁有者。

### 這個專案是怎麼做出來的
本專案由一位**沒有程式背景的玩家**主導：決定方向，並在真正的遊戲裡逐版測試（戰鬥伺服器前後試了 50 多個版本），回報看到的結果。程式、逆向分析與筆記則是由 AI（Anthropic 的 Claude）協助撰寫。

所以請這樣看待這份專案：
- 「目前狀態」裡寫的「可以用」，都是實際在遊戲裡測過的。
- 筆記裡標示 **hypothesis（推測）** 的內容只是靜態分析得到的猜測，尚未驗證，接手時請自行確認。
- 程式碼以「能動、方便實驗」為優先，不是精心設計的成品，歡迎重構。
- 授權：MIT（見 `LICENSE`），僅適用於本專案自己撰寫的程式與筆記。

### 目前狀態（截至 2026-11-08）
可以運作：
- 大廳登入、進入、初始化流程
- 建立角色
- 戰前視窗（選部隊等）
- 戰鬥載入
- 搭配「走路輔助」可在戰場自由走動
- 衝刺（連按兩下 W）與連擊

尚未完成：
- 部隊（士兵沒有出現）
- 敵方 AI／敵人
- 切換武器
- 戰鬥結束與結算畫面
- 衝刺攻擊、語音、HUD 計時器（顯示 00:00）

### 快速開始（Windows）
1. 在 Steam 安裝 Tiger Knight。腳本預設遊戲路徑為 `C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight`，不同請自行修改。
2. **hosts 重導**：用系統管理員身分編輯 `C:\Windows\System32\drivers\etc\hosts`，加入：
   ```
   127.0.0.1 front1-hk.tk.99.com
   ```
   詳見 `notes/使用說明_假伺服器.md`。
3. 建立 Python 環境（Python 3.10 以上）：
   ```
   python -m venv tools\.venv
   tools\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   （兩個假伺服器只用標準函式庫；`requirements.txt` 是給 `tools/` 內的逆向工具用的。）
4. 啟動：雙擊 `一鍵測試.bat`（同時啟動大廳與戰鬥伺服器），再從 Steam 啟動遊戲。第一次啟動會自動建立 `server/data/player.json`（存檔）與 `server/certs/`（自簽憑證）。
5. 其他啟動器：`3_啟動假伺服器.bat`（只開大廳）、`6_啟動戰鬥伺服器.bat`、`一鍵測試_捏角色.bat`、`一鍵測試_選版本.bat`（指定戰鬥變體）、`走路輔助.bat`（戰鬥中走路修正）、`英雄速度檢查.bat`、`一鍵關閉.bat`。
6. `套用走路修改.bat` 需要 `server/mods/KingdomGame_*.u`，這是從你自己的遊戲檔修改而來，**不隨專案發布**。產生方式見 `notes/battle/walk_gate_script_mod.md` 與 `tools/upatch.py`（先用 `tools/updec.py` 解出你自己的遊戲檔）。
7. 部分解密工具需要 `tools/uecfg_key.bin`（從你自己的遊戲 exe 取出的 761 位元組表，說明見 `notes/re/kingdom_exe_findings.md`）。解密後的內容（`notes/decrypted/`、`tools/work/`）請在本機自行產生，不要上傳。

### 資料夾地圖
| 路徑 | 內容 |
|---|---|
| `server/` | 假大廳、假戰鬥伺服器、Pomelo 協定、文字訊息（`text/`） |
| `tools/` | 解密、反編譯、封包分析、自測腳本（`selftest_*.py`） |
| `notes/` | 分析筆記；`START_HERE.md` 是入口 |
| `notes/reports/` | 每次實驗的詳細報告 |
| 根目錄 `.bat` | 給一般使用者的啟動器 |

### 從哪裡開始讀
1. `notes/START_HERE.md`（規則、現況、依任務查哪份筆記的對照表）
2. `notes/HISTORY.md`（時間軸，看最後幾行即可）
3. `notes/INDEX.md`（報告索引）

### 給接手者的下一步
- **V52 計分板欄位**：自己那一列與敵方列的 DataSet 欄位意義尚未確認（V52 嘗試了軍隊 ID、疑似欄位歸零、敵方速度欄位，尚未測試）。
- **部隊數量**：部隊訊息已送出但客戶端沒有反應；懷疑時機（與英雄 pawn 首次回報同一秒）、距離，或大廳的士兵清單為空。
- **敵方 pawn**：敵人沒有出現，需要找出客戶端產生敵方單位的條件。
- **切換武器**：請求 `0x272d` 應回應 `0x4e25`，內容格式尚未正確。
- **衝刺攻擊**：衝刺本身已可用，衝刺中攻擊沒有回應。
- 其他：戰鬥結束與結算、語音、HUD 計時器、地圖 11 出生點、1440p 解析度。

---

## English

### What this is
Tiger Knight (Chinese: 虎豹騎) has been shut down. This project provides a **fake Pomelo lobby server** and a **fake battle server** so the Steam client on your own PC can log in, create a character and enter a battle, for solo play and research.

- `server/lobby.py`: fake lobby (ports 3010-3019; the TLS certificate is generated on first start and needs openssl, e.g. the one bundled with Git for Windows).
- `server/battle_server.py`: fake battle server (TCP 7777).
- `tools/`: reverse-engineering / decryption helpers (Python) and a game-script patcher.
- `notes/`: the full analysis notes (protocol formats, addresses, test logs).

### Disclaimer
- Unofficial fan project. Not affiliated with, endorsed by, or connected to the game's publishers or developers.
- **No game files or assets are included.** You must own Tiger Knight (Steam App 415660) and have it installed; all tools only read your own copy.
- Provided for preservation and interoperability research. Game names, trademarks and copyrights belong to their respective owners.
- Licensed under MIT (see `LICENSE`), covering only the code and notes written for this project.

### How this project was made
The project was led by a **player with no programming background**. They set the direction, tested build after build in the real game (more than 50 battle-server variants), and reported what they saw. The code, the reverse engineering and the notes were written with the help of an AI, Anthropic's Claude.

What this means for you:
- Everything listed as working under "Status" was tested in the actual game.
- Claims marked **hypothesis** in the notes come from static analysis and are not verified, so check them yourself.
- The code favours "works and is easy to experiment with" over clean design. Refactoring is welcome.

### Status (as of 2026-11-08)
Works:
- lobby login, entry and init chain
- character creation
- the pre-battle window
- battle loading
- free walking in battle with the walk helper (`走路輔助.bat`)
- sprint (double W) and combo

Does not work yet:
- troops (soldiers never appear)
- enemy AI / enemy units
- weapon switching
- battle end and the results screen
- sprint attack, voice, HUD timer (shows 00:00)

### Quick start (Windows)
1. Install Tiger Knight via Steam. Scripts assume `C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight`; edit them if yours differs.
2. **hosts redirect**: as Administrator add this line to `C:\Windows\System32\drivers\etc\hosts`:
   ```
   127.0.0.1 front1-hk.tk.99.com
   ```
   See `notes/使用說明_假伺服器.md`.
3. Python environment (Python 3.10+):
   ```
   python -m venv tools\.venv
   tools\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   (The two servers use only the standard library; `requirements.txt` is for the tools in `tools/`.)
4. Run `一鍵測試.bat` (starts lobby + battle server), then launch the game from Steam. The first run creates `server/data/player.json` (save data) and `server/certs/` (self-signed certificate) automatically.
5. Other launchers: `3_啟動假伺服器.bat` (lobby only), `6_啟動戰鬥伺服器.bat`, `一鍵測試_捏角色.bat`, `一鍵測試_選版本.bat` (choose a battle variant), `走路輔助.bat` (walk helper), `英雄速度檢查.bat`, `一鍵關閉.bat` (stop everything).
6. `套用走路修改.bat` needs `server/mods/KingdomGame_*.u`, a patched copy of your own game file that is **not distributed**. See `notes/battle/walk_gate_script_mod.md` and `tools/upatch.py` (first decode your own file with `tools/updec.py`).
7. Some decryption tools need `tools/uecfg_key.bin` (a 761-byte table extracted from your own game exe; see `notes/re/kingdom_exe_findings.md`). Decrypted output (`notes/decrypted/`, `tools/work/`) must be generated locally and never committed.

### Folder map
| Path | Contents |
|---|---|
| `server/` | fake lobby, fake battle server, Pomelo protocol, UI strings (`text/`) |
| `tools/` | decryption, decompiler glue, packet analysis, self-tests (`selftest_*.py`) |
| `notes/` | analysis notes; `START_HERE.md` is the entry point |
| `notes/reports/` | detailed per-experiment reports |
| root `.bat` | launchers for end users |

### Where to start reading
1. `notes/START_HERE.md` (rules, current state, a task-to-note lookup table)
2. `notes/HISTORY.md` (timeline; read the tail)
3. `notes/INDEX.md` (report index)

### Next steps for whoever continues
- **V52 scoreboard slot**: the meaning of the DataSet slots for the own row and the enemy row is not settled (V52 tries the army id, zeroed suspect slots and enemy speed slots; untested).
- **Troop count**: troop messages are sent but the client does not react; suspects are timing (same second as the hero pawn's first report), distance, or the empty soldier list from the lobby.
- **Enemy pawn**: no enemies appear; find what makes the client spawn enemy units.
- **Weapon switch**: request `0x272d` should be answered by `0x4e25`; the payload format is still wrong.
- **Sprint attack**: sprinting works, attacking while sprinting gets no response.
- Also open: battle end and results, voice, HUD timer, map 11 spawn, 1440p resolution.

Notes are partly in English and partly in Traditional Chinese; claims are marked **verified** (real test or log) or **hypothesis** (static analysis only).
