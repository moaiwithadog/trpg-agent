import os
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI
from google import genai

# .envファイルからAPIキーを読み込む
load_dotenv()

# === Claude テスト ===
print("=== Claude API テスト ===")
try:
    claude = Anthropic()
    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": "「接続成功」と一言だけ答えてください。"}]
    )
    print(f"Claude: {response.content[0].text}")
except Exception as e:
    print(f"Claude エラー: {e}")

# === ChatGPT テスト ===
print("\n=== OpenAI API テスト ===")
try:
    openai = OpenAI()
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        messages=[{"role": "user", "content": "「接続成功」と一言だけ答えてください。"}]
    )
    print(f"ChatGPT: {response.choices[0].message.content}")
except Exception as e:
    print(f"OpenAI エラー: {e}")

print("\n=== テスト完了 ===")
