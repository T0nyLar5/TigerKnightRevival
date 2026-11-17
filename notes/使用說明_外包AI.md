# 外包 AI 呼叫工具使用說明（tools\ask_llm.py）
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

把問題加上指定檔案送給外部 LLM（預設 Gemini，可選 DeepSeek），並把回答存檔或印到畫面。

## 事前準備

- API 金鑰只從環境變數讀取：`GEMINI_API_KEY`、`DEEPSEEK_API_KEY`。程式不會印出、記錄或寫入金鑰。
- 執行方式（不需安裝任何套件）：`tools\.venv\Scripts\python.exe -I tools\ask_llm.py ...`

## 範例

1. 簡單提問，回答印到畫面（預設 Gemini）：
   ```
   tools\.venv\Scripts\python.exe -I tools\ask_llm.py --prompt "用繁體中文解釋什麼是 XOR 加密"
   ```

2. 把程式檔送給 DeepSeek 檢查，回答存成檔案：
   ```
   tools\.venv\Scripts\python.exe -I tools\ask_llm.py --provider deepseek --prompt-file q.txt --input tools\tkcrypt.py --out notes\answer.md
   ```

3. 指定模型並加上系統指令：
   ```
   tools\.venv\Scripts\python.exe -I tools\ask_llm.py --model gemini-3.7-flash --system "你是逆向工程助手" --prompt "分析這個檔案的結構" --input notes\route_table.txt
   ```

4. 列出可用的 Gemini 模型名稱：
   ```
   tools\.venv\Scripts\python.exe -I tools\ask_llm.py --list-models
   ```

## 注意事項

- 安全檢查：若輸入檔位於 `server\data\`、`server\logs\`，或檔名為 `player.json`，或內容含 200 字元以上的十六進位字串（可能是 Steam ticket），程式會拒絕送出並說明原因。
- `--max-chars`（預設 400000）：送出的文字超過此長度時拒絕送出，不會自動截斷。
- 執行完成後，stderr 會印出一行摘要（供應商、模型、輸入字數、輸出字數、token 用量）。
