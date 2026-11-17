#!/usr/bin/env python3
"""Send a prompt (plus optional input files) to an external LLM and save the answer.

Providers: gemini (default) and deepseek. API keys are read ONLY from the env vars
GEMINI_API_KEY and DEEPSEEK_API_KEY. They are never printed, logged or written.
Standard library only.

Examples:
  ask_llm.py --prompt "Reply with exactly: OK"
  ask_llm.py --provider deepseek --prompt-file q.txt --input a.py b.py --out answer.md
  ask_llm.py --list-models
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "deepseek": "deepseek-chat"}
KEY_ENV = {"gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
TIMEOUT_SECONDS = 120
RETRY_DELAY_SECONDS = 5
HEX_RUN_RE = re.compile(r"[0-9a-fA-F]{200,}")
BLOCKED_DIR_PAIRS = (("server", "data"), ("server", "logs"))
BLOCKED_BASENAMES = {"player.json"}


class CliError(Exception):
    pass


def get_key(provider):
    key = os.environ.get(KEY_ENV[provider], "").strip()
    if not key:
        raise CliError(f"{KEY_ENV[provider]} is not set. Export it in the environment and retry.")
    return key


def scrub(text, key):
    """Make sure the API key never appears in any message we print."""
    if key:
        text = text.replace(key, "***")
    return text


def api_error_message(raw):
    try:
        obj = json.loads(raw)
    except ValueError:
        return raw[:500]
    err = obj.get("error") if isinstance(obj, dict) else None
    if isinstance(err, dict) and err.get("message"):
        return str(err["message"])
    if isinstance(err, str):
        return err
    return raw[:500]


def http_json(method, url, headers, body=None, key=None):
    """One HTTP call returning parsed JSON. Retries once on 429 / 5xx after 5 s."""
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = dict(headers, **{"Content-Type": "application/json; charset=utf-8"})
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            retryable = e.code == 429 or 500 <= e.code < 600
            if retryable and attempt == 0:
                print(f"note: HTTP {e.code} from API, retrying once in {RETRY_DELAY_SECONDS} s...",
                      file=sys.stderr)
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise CliError(f"HTTP {e.code} from API: {scrub(api_error_message(raw), key)}")
        except urllib.error.URLError as e:
            raise CliError(f"network error: {scrub(str(e.reason), key)}")
        except OSError as e:  # socket timeouts and similar
            raise CliError(f"network error: {scrub(str(e), key)}")
        try:
            return json.loads(raw)
        except ValueError:
            raise CliError("API returned a response that is not JSON")
    raise CliError("request failed")  # not reached


def gemini_list_models(key):
    names, page_token = [], None
    while True:
        url = f"{GEMINI_BASE}/models?pageSize=1000"
        if page_token:
            url += "&pageToken=" + page_token
        data = http_json("GET", url, {"x-goog-api-key": key}, key=key)
        for m in data.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(m["name"].split("/", 1)[-1])
        page_token = data.get("nextPageToken")
        if not page_token:
            return names


def deepseek_list_models(key):
    data = http_json("GET", f"{DEEPSEEK_BASE}/models", {"Authorization": f"Bearer {key}"}, key=key)
    return [m["id"] for m in data.get("data", [])]


def gemini_generate(user_text, system, model, key):
    body = {"contents": [{"role": "user", "parts": [{"text": user_text}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"{GEMINI_BASE}/models/{model}:generateContent"
    data = http_json("POST", url, {"x-goog-api-key": key}, body, key=key)
    cands = data.get("candidates") or []
    if not cands:
        raise CliError(f"no candidates in response (promptFeedback={data.get('promptFeedback')})")
    parts = (cands[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        raise CliError(f"empty answer (finishReason={cands[0].get('finishReason')})")
    usage = data.get("usageMetadata") or {}
    return text, (usage.get("promptTokenCount"), usage.get("candidatesTokenCount"))


def deepseek_generate(user_text, system, model, key):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_text})
    body = {"model": model, "messages": messages, "stream": False}
    data = http_json("POST", f"{DEEPSEEK_BASE}/chat/completions",
                     {"Authorization": f"Bearer {key}"}, body, key=key)
    choices = data.get("choices") or []
    if not choices:
        raise CliError("no choices in response")
    text = (choices[0].get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    return text, (usage.get("prompt_tokens"), usage.get("completion_tokens"))


def read_text_file(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError as e:
        raise CliError(f"cannot read '{path}': {e.strerror or e}")


def check_paths(paths):
    """Refuse input paths under server\\data, server\\logs, or named player.json."""
    for p in paths:
        absp = os.path.normcase(os.path.abspath(p))
        low = [x for x in re.split(r"[\\/]+", absp) if x]
        for i in range(len(low) - 1):
            if (low[i], low[i + 1]) in BLOCKED_DIR_PAIRS:
                raise CliError(f"refused: '{p}' is under server\\{low[i + 1]}\\ "
                               "(game save/log data must not be sent)")
        if low and low[-1] in BLOCKED_BASENAMES:
            raise CliError(f"refused: '{p}' is player.json (player data must not be sent)")


def check_text(text):
    """Refuse text containing a 200+ char hex run (could be a Steam ticket)."""
    m = HEX_RUN_RE.search(text)
    if m:
        raise CliError(f"refused: text contains a {len(m.group(0))}-char hex string "
                       "(looks like a Steam ticket or key material)")


def build_user_text(prompt, inputs):
    parts = [prompt]
    for path, text in inputs:
        name = os.path.basename(path)
        parts.append(f"\n\n===== FILE: {name} =====\n{text}\n===== END FILE: {name} =====")
    return "".join(parts)


def run(args):
    key = get_key(args.provider)

    if args.list_models:
        names = gemini_list_models(key) if args.provider == "gemini" else deepseek_list_models(key)
        for name in names:
            print(name)
        return 0

    if args.prompt is None and args.prompt_file is None:
        raise CliError("give --prompt or --prompt-file (or use --list-models)")
    prompt = args.prompt if args.prompt is not None else read_text_file(args.prompt_file)

    check_paths(args.input)
    inputs = [(p, read_text_file(p)) for p in args.input]
    check_text(args.system + "\n" + prompt + "\n" + "\n".join(t for _, t in inputs))

    user_text = build_user_text(prompt, inputs)
    total = len(args.system) + len(user_text)
    if total > args.max_chars:
        raise CliError(f"refused: text to send is {total} chars, above --max-chars {args.max_chars}. "
                       "Send fewer or smaller inputs, or raise --max-chars.")

    model = args.model or DEFAULT_MODELS[args.provider]
    if args.provider == "gemini":
        text, tokens = gemini_generate(user_text, args.system, model, key)
    else:
        text, tokens = deepseek_generate(user_text, args.system, model, key)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()

    tok = "n/a" if tokens[0] is None and tokens[1] is None else f"{tokens[0]}/{tokens[1]}"
    print(f"[ask_llm] provider={args.provider} model={model} input_chars={total} "
          f"output_chars={len(text)} tokens(prompt/completion)={tok}", file=sys.stderr)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Send a prompt plus optional files to an LLM.")
    ap.add_argument("--provider", choices=["gemini", "deepseek"], default="gemini")
    ap.add_argument("--model", help="override the default model")
    ap.add_argument("--system", default="", help="optional system instruction")
    ap.add_argument("--prompt", help="prompt text")
    ap.add_argument("--prompt-file", help="read the prompt from a UTF-8 text file")
    ap.add_argument("--input", nargs="+", default=[], metavar="FILE",
                    help="input files appended to the prompt")
    ap.add_argument("--out", help="write the answer to this file (UTF-8); default stdout")
    ap.add_argument("--max-chars", type=int, default=400000,
                    help="refuse if the text to send exceeds this (default 400000)")
    ap.add_argument("--list-models", action="store_true", help="print available model names")
    args = ap.parse_args(argv)
    if args.prompt is not None and args.prompt_file is not None:
        ap.error("use only one of --prompt or --prompt-file")

    try:
        return run(args)
    except CliError as e:
        key = os.environ.get(KEY_ENV[args.provider], "")
        print(f"error: {scrub(str(e), key)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
