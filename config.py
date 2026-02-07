"""設定管理"""
import os
from dotenv import load_dotenv

load_dotenv()

# APIキー
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === GM設定 ===
GM_PROVIDER = "openai"  # "anthropic" or "openai"
GM_MODEL = "gpt-4o"

# === PL設定 ===
PL_PROVIDER = "anthropic"  # "anthropic" or "openai"
PL_MODEL = "claude-sonnet-4-20250514"

# ゲーム設定
MAX_TURNS = 50

# === プリセット（参考用） ===
# "anthropic" : "claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"
# "openai"    : "gpt-5.2", "gpt-5-mini", "gpt-4o", "gpt-4o-mini"
# 
# 
# パターン1: 現状（Claude GM + ChatGPT PL）
#   GM_PROVIDER = "anthropic", GM_MODEL = "claude-sonnet-4-20250514"
#   PL_PROVIDER = "openai", PL_MODEL = "gpt-4o-mini"
#
# パターン2: 入れ替え（ChatGPT GM + Claude PL）
#   GM_PROVIDER = "openai", GM_MODEL = "gpt-4o"
#   PL_PROVIDER = "anthropic", PL_MODEL = "claude-haiku-4-5-20251001"
#
# パターン3: Claude同士
#   GM_PROVIDER = "anthropic", GM_MODEL = "claude-sonnet-4-20250514"
#   PL_PROVIDER = "anthropic", PL_MODEL = "claude-haiku-4-5-20251001"
#
# パターン4: OpenAI同士
#   GM_PROVIDER = "openai", GM_MODEL = "gpt-4o"
#   PL_PROVIDER = "openai", PL_MODEL = "gpt-4o-mini"