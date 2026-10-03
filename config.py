"""設定管理"""
import os
from dotenv import load_dotenv

load_dotenv()

# APIキー
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# === GM設定 ===
GM_PROVIDER = "anthropic"  # "anthropic", "openai", "google", "claude_cli", or "codex_cli"
GM_MODEL = "claude-sonnet-4-20250514"

# === PL設定 ===
PL_PROVIDER = "openai"  # "anthropic", "openai", "google", "claude_cli", or "codex_cli"
PL_MODEL = "gpt-4o-mini"

# === サブスクCLI設定（"claude_cli" / "codex_cli" 使用時） ===
# Claude Code (`claude -p`) / Codex CLI (`codex exec`) をログイン済みの定額プラン枠で呼び出します。
# 実行時、子プロセスには ANTHROPIC_API_KEY / OPENAI_API_KEY / CODEX_API_KEY を渡しません（API課金防止）。
CLI_WORK_DIR = ".cli_sessions"  # CLIの作業ディレクトリ（セッション記録・システムプロンプトの置き場）
CLI_TIMEOUT_SEC = 600           # 1回の呼び出しのタイムアウト（秒）

# ゲーム設定
MAX_TURNS = 50  # 1セッションの最大ターン数(安全装置として)
ENABLE_SESSION_FEEDBACK = True  # Trueでキャンペーン終了時にGM/PLの相互フィードバックを生成

# === モデルの選択肢（参考） ===
# "anthropic" : "claude-opus-4-1-20250805","claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"
# "openai"    : "gpt-5.2", "gpt-5-mini", "gpt-4o", "gpt-4o-mini"
# "claude_cli": "opus", "sonnet", "haiku"（Claude Code のモデル指定。"" でCLIの既定）
# "codex_cli" : Codex で選べるモデル名（"" でCLIの既定）
# "google"    : "gemini-3.1-pro-preview", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"
# 
# GMには比較的「強い」モデルが適当のようです。APIのコストと相談しつつ運用ください。
# 
# パターン1: ストーリー重視・APIコスト度外視（Claude GM + ChatGPT PL）
#   GM_PROVIDER = "anthropic", GM_MODEL = "claude-opus-4-1-20250805"
#   PL_PROVIDER = "openai", PL_MODEL = "gpt-5.2"
#
# パターン2: APIコスト抑えめ（Gemini GM + ChatGPT PL）
#   GM_PROVIDER = "google", GM_MODEL = "gemini-3.1-pro-preview"
#   PL_PROVIDER = "openai", PL_MODEL = "gpt-4o-mini"
#
# パターン3: PL応答力の強化（Gemini GM + Claude PL）
#   GM_PROVIDER = "google", GM_MODEL = "gemini-3.1-pro-preview"
#   PL_PROVIDER = "anthropic", PL_MODEL = "claude-sonnet-4-20250514"
# 
# パターン4: サブスク定額枠（Claude Code GM + Codex PL）
#   GM_PROVIDER = "claude_cli", GM_MODEL = "opus"
#   PL_PROVIDER = "codex_cli",  PL_MODEL = ""
# 
# NG例:
# - "claude-haiku-4-5-20251001"はPLさせてもGMをやろうとするケースが多くありました、使えないかも。
# - "gpt-5.2"はGM役させると、細かいことをPLに質問してテンポを崩すケースが多くありました。PL役に限定したほうがよいのかも。