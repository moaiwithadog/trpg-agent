"""GM/PLエージェント"""
import config
from cli_backend import call_cli_llm

# APIクライアントは使うときに初期化する（CLIだけで遊ぶ場合はAPIキーもSDKも不要）
_clients = {}


def _get_client(provider: str):
    if provider not in _clients:
        if provider == "anthropic":
            from anthropic import Anthropic
            _clients[provider] = Anthropic()
        elif provider == "openai":
            from openai import OpenAI
            _clients[provider] = OpenAI()
        elif provider == "google":
            if not config.GOOGLE_API_KEY:
                raise ValueError("Google API Key is not set.")
            from google import genai
            _clients[provider] = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _clients[provider]


def load_file(filepath: str) -> str:
    """ファイルを読み込む"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# ルールブック読み込み
RULEBOOK = load_file("rulebook.md")

# GMのシステムプロンプト
GM_SYSTEM_PROMPT = f"""あなたはテキストTRPGのゲームマスター（GM）です。
以下のルールブックに沿って、ゲームを進行してください。
最優先は「短い入力でテンポよく進むこと」。

{RULEBOOK}

# 開始手順
PC情報とシナリオ設定は最初のメッセージで与えられます。
その情報を元に、スタートシーンを提示してTurn1を開始してください。

# ダイスについて
- ダイスが必要な裁定では、裁定ログ前半の直後に【ダイス要求: 通常】または【ダイス要求: 対抗】を出力して応答を終えてください。
- 出目はオーケストレーターから【ダイス結果】として返されます。出目を自分で決めたり書いたりしないでください。

# GMとしての心得
- 安全な選択肢と危険な選択肢を並べる。
- PLの失敗を許容する。たとえPCが失敗したり死亡したりしても、PLによるPCの選択を活かして、物語としての美しさを優先する。
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
  - ダイスロールや出目の決定（ダイスはオーケストレーターが振ります）
- 判断に迷っても、必ず何らかの行動を宣言してください
- 行動の結果がどうなるかはGMが決めます。あなたは宣言するだけです

# 応答フォーマット（必須）
以下の形式で、400字～700字で応答してください：

【思考】
（PCの内心、状況の分析、迷いなど）

【行動宣言】
（具体的な行動を1つ明記。「〜する」「〜を試みる」の形で）

# PLとしての心得
- 失敗することを許容する。
- 目標の達成よりも、PCの思考や感情をロールプレイして物語としての美しさを表すことを、より優先する。

"""

# PL用：シナリオ生成プロンプト
PL_SCENARIO_GEN_PROMPT = f"""あなたはテキストTRPGのプレイヤー（PL）です。
これからゲームを始めるにあたり、PC（プレイヤーキャラクター）を作成し、最初のセッションの状況を設定してください。

# ルールブック
{RULEBOOK}

# 応答フォーマット（必須）
以下の形式で,700字以内で応答してください：

【PC設定】
- 名前:
- 職業/役割:
- 特徴（外見・性格を1〜2文で）:
- 個人的な目的/動機:
- PLの希望（避けたい展開/希望するシチュエーション等、任意）:

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

# GM用：セッション振り返りプロンプト
GM_SESSION_FEEDBACK_PROMPT = """セッションが終了しました。今回のセッション全体を振り返り、PLの対応について評価してください。

# 応答フォーマット（必須）

【面白さの評価】
（今回のセッション全体の面白さを5段階で評価し、その理由を1〜2文で述べてください）
評価: ★☆☆☆☆〜★★★★★

【PLの良かったところ】
（PLの行動宣言やロールプレイで優れていた点を2〜3点挙げてください）

【改善が望ましいところ】
（PLの対応で改善できそうな点を1〜2点、建設的に述べてください）
"""

# PL用：セッション振り返りプロンプト
PL_SESSION_FEEDBACK_PROMPT = """セッションが終了しました。今回のセッション全体を振り返り、GMの対応について評価してください。

# 応答フォーマット（必須）

【面白さの評価】
（今回のセッション全体の面白さを5段階で評価し、その理由を1〜2文で述べてください）
評価: ★☆☆☆☆〜★★★★★

【GMの良かったところ】
（GMの状況描写、裁定、NPC操作などで優れていた点を2〜3点挙げてください）

【改善が望ましいところ】
（GMの対応で改善できそうな点を1〜2点、建設的に述べてください）
"""


def _with_cache_breakpoint(messages: list) -> list:
    """最後のメッセージに cache_control を付けたコピーを返す（Anthropic のプロンプトキャッシュ用）

    システムプロンプトと、ここまでの履歴全体がキャッシュされ、
    次の呼び出しではキャッシュ済みの先頭部分が割安な料金で読み込まれる。
    呼び出し元の履歴リストは変更しない。
    """
    if not messages:
        return messages
    last = messages[-1]
    content = last["content"]
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    else:
        content = [dict(block) for block in content]
    content[-1]["cache_control"] = {"type": "ephemeral"}
    return messages[:-1] + [{"role": last["role"], "content": content}]


def call_llm(provider: str, model: str, system_prompt: str, messages: list, max_tokens: int = 1000) -> str:
    """汎用LLM呼び出し関数"""
    if provider in ("claude_cli", "codex_cli"):
        # CLIでは max_tokens を指定できないため、文字数はプロンプトの指示に任せる
        return call_cli_llm(provider, model, system_prompt, messages)

    if provider == "anthropic":
        response = _get_client(provider).messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=_with_cache_breakpoint(messages)
        )
        return response.content[0].text
    
    elif provider == "openai":
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)
        
        response = _get_client(provider).chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=openai_messages
        )
        return response.choices[0].message.content
    
    elif provider == "google":
        from google.genai import types
        google_client = _get_client(provider)

        # Googleのメッセージ形式に変換
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
        
        response = google_client.models.generate_content(
            model=model,
            contents=gemini_messages,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            )
        )
        return response.text
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_gm(conversation_history: list) -> str:
    """GMを呼び出す"""
    return call_llm(
        provider=config.GM_PROVIDER,
        model=config.GM_MODEL,
        system_prompt=GM_SYSTEM_PROMPT,
        messages=conversation_history,
        max_tokens=3000
    )


def call_pl(conversation_history: list) -> str:
    """PLを呼び出す"""
    return call_llm(
        provider=config.PL_PROVIDER,
        model=config.PL_MODEL,
        system_prompt=PL_SYSTEM_PROMPT,
        messages=conversation_history,
        max_tokens=2000
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
        max_tokens=2000
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
        max_tokens=3000
    )


def call_gm_session_feedback(conversation_history: list) -> str:
    """GMにセッションの振り返りを依頼"""
    messages = conversation_history + [
        {"role": "user", "content": GM_SESSION_FEEDBACK_PROMPT}
    ]
    return call_llm(
        provider=config.GM_PROVIDER,
        model=config.GM_MODEL,
        system_prompt=GM_SYSTEM_PROMPT,
        messages=messages,
        max_tokens=4000
    )


def call_pl_session_feedback(conversation_history: list) -> str:
    """PLにセッションの振り返りを依頼"""
    messages = conversation_history + [
        {"role": "user", "content": PL_SESSION_FEEDBACK_PROMPT}
    ]
    return call_llm(
        provider=config.PL_PROVIDER,
        model=config.PL_MODEL,
        system_prompt=PL_SYSTEM_PROMPT,
        messages=messages,
        max_tokens=4000
    )