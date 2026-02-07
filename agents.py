"""GM/PLエージェント"""
import os
from anthropic import Anthropic
from openai import OpenAI
import config

# クライアント初期化
claude_client = Anthropic()
openai_client = OpenAI()


def load_file(filepath: str) -> str:
    """ファイルを読み込む"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# ルールブック読み込み
RULEBOOK = load_file("rulebook.md")

# GMのシステムプロンプト
GM_SYSTEM_PROMPT = f"""あなたはテキストTRPGのゲームマスター（GM）です。目的は「短い入力でテンポよく遊べる」こと。
以下のルールを優先し、ルール外の創作は"状況描写"の範囲でのみ行う。

{RULEBOOK}

# 開始手順
PC情報とシナリオ設定は最初のメッセージで与えられます。
その情報を元に、スタートシーンを提示してTurn1を開始してください。
"""

# PLのシステムプロンプト
PL_SYSTEM_PROMPT = f"""あなたはテキストTRPGのプレイヤー（PL）です。

# ルールブック
以下のルールを理解した上でプレイしてください：

{RULEBOOK}

# あなたの役割
- GMの描写を受けて、PCとして行動を宣言する
- PCの思考や感情をロールプレイする
- GMが提示した行動候補から選んでもよいし、独自の行動を宣言してもよい

# 絶対に守るルール
- あなたはPLです。以下のGMの役割は絶対に行わないでください：
  - 状況描写（「〜が起こった」という結果の記述）
  - 判定や裁定
  - NPC の台詞や行動の決定
  - 行動候補の提示
- 判断に迷っても、必ず何らかの行動を宣言してください
- 行動の結果がどうなるかはGMが決めます。あなたは宣言するだけです

# 応答フォーマット（必須）
以下の形式で応答してください：

【思考】
（PCの内心、状況の分析、迷いなど）

【行動宣言】
（具体的な行動を1つ明記。「〜する」「〜を試みる」の形で）
"""

# PL用：シナリオ生成プロンプト
PL_SCENARIO_GEN_PROMPT = f"""あなたはテキストTRPGのプレイヤー（PL）です。
これからゲームを始めるにあたり、PC（プレイヤーキャラクター）を作成し、最初のセッションの状況を設定してください。

# ルールブック
{RULEBOOK}

# 応答フォーマット（必須）
以下の形式で応答してください：

【PC設定】
- 名前:
- 職業/役割:
- 特徴（外見・性格を1〜2文で）:
- 個人的な目的/動機:
- 苦手なもの（任意）:

【初回セッション設定】
- 具体的な依頼/状況:
- 開始地点:
- 初期所持品（3〜5個）:
"""

# PL用：次回フック選択プロンプト
PL_NEXT_HOOK_PROMPT = """セッションが終了しました。
GMから提示された「次回フック」を踏まえて、次のセッションで何をしたいか選択・提案してください。

# 応答フォーマット（必須）
以下の形式で応答してください：

【振り返り】
（今回のセッションで印象的だったこと、PCの心境の変化など）

【次回への希望】
（次のセッションでやりたいこと、追いたい目標、気になる伏線など）
"""


def call_llm(provider: str, model: str, system_prompt: str, messages: list, max_tokens: int = 1000) -> str:
    """汎用LLM呼び出し関数"""
    if provider == "anthropic":
        response = claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    
    elif provider == "openai":
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)
        
        response = openai_client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=openai_messages
        )
        return response.choices[0].message.content
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_gm(conversation_history: list) -> str:
    """GMを呼び出す"""
    return call_llm(
        provider=config.GM_PROVIDER,
        model=config.GM_MODEL,
        system_prompt=GM_SYSTEM_PROMPT,
        messages=conversation_history,
        max_tokens=2000
    )


def call_pl(conversation_history: list) -> str:
    """PLを呼び出す"""
    return call_llm(
        provider=config.PL_PROVIDER,
        model=config.PL_MODEL,
        system_prompt=PL_SYSTEM_PROMPT,
        messages=conversation_history,
        max_tokens=500
    )


def call_pl_scenario_gen(scenario_template: str) -> str:
    """PLにシナリオ生成を依頼"""
    messages = [
        {"role": "user", "content": f"以下のシナリオテンプレートに基づいて、PCと初回セッションを設定してください：\n\n{scenario_template}"}
    ]
    
    return call_llm(
        provider=config.PL_PROVIDER,
        model=config.PL_MODEL,
        system_prompt=PL_SCENARIO_GEN_PROMPT,
        messages=messages,
        max_tokens=800
    )


def call_pl_next_hook(session_end_response: str) -> str:
    """PLに次回フック選択を依頼"""
    messages = [
        {"role": "user", "content": f"GMからのセッション終了描写：\n\n{session_end_response}\n\n{PL_NEXT_HOOK_PROMPT}"}
    ]
    
    return call_llm(
        provider=config.PL_PROVIDER,
        model=config.PL_MODEL,
        system_prompt=PL_SYSTEM_PROMPT,
        messages=messages,
        max_tokens=500
    )