"""サブスク契約のCLI（Claude Code / Codex）をLLMバックエンドとして使う

`claude -p` / `codex exec` をサブプロセスとして呼び出し、CLI側のセッションを
resume しながら会話を続ける。API従量課金ではなく、各CLIのログイン（定額プラン）枠で動く。

オーケストレーターは従来どおり「会話履歴の全体」を call_llm に渡してくる。
ここでは、過去に送った履歴を覚えておき、今回の履歴がその続きであれば
新しく増えた分だけを resume で送る。続きでなければ新しいCLIセッションを始める。
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

import config

WORK_ROOT = os.path.abspath(config.CLI_WORK_DIR)
PROMPT_DIR = os.path.join(WORK_ROOT, "prompts")

# 子プロセスに引き継がせない環境変数。
# .env から読み込まれたAPIキーが残っていると、CLIがサブスクではなくAPI課金で動いてしまう。
_STRIPPED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    # Claude Code のターミナル内から起動した場合に、親セッションのIDを引き継がないように
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_REMOTE_SESSION_ID",
]

# 直前の応答がオーケストレーターに途中で打ち切られた場合（ダイス要求以降を破棄）に添える注記
TRUNCATION_NOTE = (
    "（注：あなたの直前の応答は【ダイス要求】の位置で打ち切られました。"
    "それより後ろに書いた内容は無効として扱ってください。）"
)


class CliError(RuntimeError):
    pass


class _Conversation:
    """1つのCLIセッションと、そこへ送信済みの履歴"""

    def __init__(self, session_id: str, messages: list):
        self.session_id = session_id
        self.messages = messages  # role/content の辞書のリスト（assistant は CLI の生の応答）


# (provider, model, system_prompt) ごとの会話一覧
_conversations: dict = {}


def _clean_env() -> dict:
    env = os.environ.copy()
    for key in _STRIPPED_ENV_VARS:
        env.pop(key, None)
    return env


def _workdir(provider: str) -> str:
    path = os.path.join(WORK_ROOT, provider)
    os.makedirs(path, exist_ok=True)
    return path


def _prompt_file(system_prompt: str) -> str:
    """システムプロンプトをファイルに書き出してパスを返す（コマンドライン長の制限を避けるため）"""
    os.makedirs(PROMPT_DIR, exist_ok=True)
    digest = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(PROMPT_DIR, f"system_{digest}.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(system_prompt)
    return path


def _executable(name: str) -> str:
    # Windows の npm 版 (claude.cmd 等) も解決できるよう shutil.which を使う
    path = shutil.which(name)
    if not path:
        raise CliError(f"`{name}` コマンドが見つかりません。インストールしてログインしてください。")
    return path


def _run(cmd: list, stdin_text: str, cwd: str) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            env=_clean_env(),
            timeout=config.CLI_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"CLIが {config.CLI_TIMEOUT_SEC} 秒以内に応答しませんでした: {cmd[0]}")
    return result


def _call_claude(model: str, system_prompt: str, prompt: str, session_id: str | None) -> tuple[str, str]:
    """Claude Code (`claude -p`) を呼び出し、(応答テキスト, セッションID) を返す"""
    cmd = [
        _executable("claude"), "-p",
        "--output-format", "json",
        "--system-prompt-file", _prompt_file(system_prompt),  # 既定のコーディング用プロンプトを置き換える
        "--tools", "",            # ファイル操作・コマンド実行などのツールを無効化
        "--setting-sources", "",  # ユーザー/プロジェクトの設定を読み込まない
    ]
    if model:
        cmd += ["--model", model]
    if session_id:
        cmd += ["--resume", session_id]

    result = _run(cmd, prompt, _workdir("claude"))
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise CliError(f"claude の出力を解釈できませんでした (exit {result.returncode}):\n{result.stdout}\n{result.stderr}")
    if data.get("is_error") or result.returncode != 0:
        raise CliError(f"claude がエラーを返しました: {data.get('result') or result.stderr}")
    return data.get("result", ""), data["session_id"]


def _call_codex(model: str, system_prompt: str, prompt: str, session_id: str | None) -> tuple[str, str]:
    """Codex CLI (`codex exec`) を呼び出し、(応答テキスト, セッションID) を返す"""
    exe = _executable("codex")
    common = [
        "--json",
        "--skip-git-repo-check",
        # 既定のコーディング用ベースプロンプトを置き換える
        "-c", f"model_instructions_file={json.dumps(_prompt_file(system_prompt))}",
        # コマンドを実行させない前提だが、念のため読み取り専用に
        "-c", 'sandbox_mode="read-only"',
    ]
    if model:
        common += ["-m", model]

    fd, out_path = tempfile.mkstemp(prefix="codex_last_", suffix=".txt")
    os.close(fd)
    try:
        if session_id:
            cmd = [exe, "exec", "resume", *common, "-o", out_path, session_id, "-"]
        else:
            cmd = [exe, "exec", *common, "-o", out_path, "-"]
        result = _run(cmd, prompt, _workdir("codex"))

        thread_id = session_id
        error_message = ""
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id", thread_id)
            elif event.get("type") in ("turn.failed", "error"):
                error_message = json.dumps(event, ensure_ascii=False)

        with open(out_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    finally:
        os.remove(out_path)

    if result.returncode != 0 or error_message or not thread_id:
        raise CliError(f"codex がエラーを返しました (exit {result.returncode}): {error_message}\n{result.stderr}")
    return text, thread_id


_CALLERS = {
    "claude_cli": _call_claude,
    "codex_cli": _call_codex,
}


def _render_transcript(messages: list) -> str:
    """新規セッションに既存の履歴を渡すとき、1つのテキストにまとめる"""
    if len(messages) == 1:
        return messages[0]["content"]
    parts = ["これまでのやり取りは以下のとおりです。\n"]
    for m in messages[:-1]:
        label = "あなた（直前までの応答）" if m["role"] == "assistant" else "相手"
        parts.append(f"<{label}>\n{m['content']}\n</{label}>")
    parts.append(f"\n上記に続く最新のメッセージです。これに応答してください。\n\n{messages[-1]['content']}")
    return "\n\n".join(parts)


def _matched_prefix(conv: _Conversation, messages: list) -> tuple[int, bool]:
    """conv の送信済み履歴が messages の先頭と一致すれば (一致した件数, 直前応答が打ち切られたか) を返す。
    一致しなければ (-1, False)。"""
    sent = conv.messages
    if len(sent) >= len(messages):
        return -1, False
    truncated = False
    for i, (s, m) in enumerate(zip(sent, messages)):
        if s["role"] != m["role"]:
            return -1, False
        if s["content"] == m["content"]:
            continue
        # オーケストレーターがダイス要求以降を切り詰めた assistant 応答は一致とみなす
        if s["role"] == "assistant" and s["content"].startswith(m["content"]):
            truncated = i == len(sent) - 1
            continue
        return -1, False
    return len(sent), truncated


def call_cli_llm(provider: str, model: str, system_prompt: str, messages: list) -> str:
    if provider not in _CALLERS:
        raise ValueError(f"Unknown CLI provider: {provider}")
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("messages の末尾は user である必要があります")

    key = (provider, model, system_prompt)
    conversations = _conversations.setdefault(key, [])

    # 今回の履歴が続きになっている会話のうち、最も長いものを選ぶ
    best, best_len, best_truncated = None, -1, False
    for conv in conversations:
        n, truncated = _matched_prefix(conv, messages)
        if n > best_len:
            best, best_len, best_truncated = conv, n, truncated

    new_messages = messages[best_len:] if best else messages
    if best and all(m["role"] == "user" for m in new_messages):
        prompt = "\n\n".join(m["content"] for m in new_messages)
        if best_truncated:
            prompt = f"{TRUNCATION_NOTE}\n\n{prompt}"
        text, session_id = _CALLERS[provider](model, system_prompt, prompt, best.session_id)
        best.session_id = session_id
        best.messages = list(messages) + [{"role": "assistant", "content": text}]
    else:
        text, session_id = _CALLERS[provider](model, system_prompt, _render_transcript(messages), None)
        conversations.append(
            _Conversation(session_id, list(messages) + [{"role": "assistant", "content": text}])
        )
    return text
