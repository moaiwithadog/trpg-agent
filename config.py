"""設定管理"""
import os
from dotenv import load_dotenv

load_dotenv()

# APIキー
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# モデル設定
GM_MODEL = "claude-haiku-4-5-20251001"  # GM役：Claude
PL_MODEL = "gpt-4o-mini"               # PL役：ChatGPT

# ゲーム設定
MAX_TURNS = 20  # 最大ターン数（安全装置）