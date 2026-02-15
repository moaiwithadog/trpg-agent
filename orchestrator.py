"""オーケストレーター：ゲーム進行を管理"""
import re
import os
from datetime import datetime
from agents import call_gm, call_pl, call_pl_scenario_gen, call_pl_next_hook, call_gm_session_feedback, call_pl_session_feedback, load_file
import config


def check_pl_response(response: str) -> tuple[bool, str]:
    """PLの応答が正常か確認"""
    if "【行動宣言】" not in response:
        return False, "行動宣言がありません"
    
    gm_patterns = [
        r"Turn:",
        r"HP:",
        r"SP:",
        r"Tension:",
        r"【状況】",
        r"【判定】",
        r"【裁定】",
        r"行動候補",
        r"あなたはどうしますか",
        r"選択してください",
    ]
    for pattern in gm_patterns:
        if re.search(pattern, response):
            return False, f"GM的な振る舞いを検出: {pattern}"
    
    return True, "OK"


class CampaignLogger:
    """キャンペーン全体のログをMarkdown形式で保存"""
    
    def __init__(self, scenario_template: str):
        os.makedirs("logs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = f"logs/campaign_{timestamp}.md"
        self.session_count = 0
        self.total_turns = 0
        
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("# Campaign Log\n\n")
            f.write("## キャンペーン情報\n\n")
            f.write(f"- 開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- GM: {config.GM_PROVIDER} / {config.GM_MODEL}\n")
            f.write(f"- PL: {config.PL_PROVIDER} / {config.PL_MODEL}\n")
            f.write("## シナリオテンプレート\n\n")
            f.write(f"{scenario_template}\n\n")
        
        print(f"📄 ログファイル: {self.filepath}")
    
    def log_scenario_generation(self, pl_scenario: str):
        """PLによるシナリオ生成を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("## PLによるシナリオ生成\n\n")
            f.write(f"{pl_scenario}\n\n")
    
    def start_session(self, session_num: int, additional_instruction: str = ""):
        """セッション開始を記録"""
        self.session_count = session_num
        
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("---\n\n")
            f.write(f"# Session {session_num}\n\n")
            f.write(f"- 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if additional_instruction:
                f.write("## 【オーケストレーター介入】追加指示\n\n")
                f.write(f"{additional_instruction}\n\n")
    
    def log_turn_start(self, turn: int):
        """ターン開始を記録"""
        self.total_turns += 1
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"## Turn {turn}\n\n")
    
    def log_gm(self, response: str, is_retry: bool = False):
        """GM応答を記録"""
        label = "【GM 再試行】" if is_retry else "【GM】"
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"### {label}\n\n")
            f.write(f"{response}\n\n")
    
    def log_pl(self, response: str, is_retry: bool = False):
        """PL応答を記録"""
        label = "【PL 再試行】" if is_retry else "【PL】"
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"### {label}\n\n")
            f.write(f"{response}\n\n")
    
    def log_anomaly(self, anomaly_type: str, reason: str):
        """異常検知を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"### ⚠️ 異常検知 ({anomaly_type})\n\n")
            f.write(f"{reason}\n\n")
    
    def log_human_input(self, input_text: str):
        """人間の介入を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"### 【オーケストレーター介入】\n\n")
            f.write(f"{input_text}\n\n")
    
    def log_pl_next_hook(self, response: str):
        """PLの次回フック選択を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("### 【PL 次回への希望】\n\n")
            f.write(f"{response}\n\n")
    
    def log_gm_feedback(self, response: str):
        """GMのセッション振り返りを記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("### 【GM セッション振り返り】\n\n")
            f.write(f"{response}\n\n")

    def log_pl_feedback(self, response: str):
        """PLのセッション振り返りを記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("### 【PL セッション振り返り】\n\n")
            f.write(f"{response}\n\n")

    def log_session_end(self, reason: str, session_turns: int):
        """セッション終了を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("## セッション終了\n\n")
            f.write(f"- 終了理由: {reason}\n")
            f.write(f"- セッションターン数: {session_turns}\n")
            f.write(f"- 終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def log_campaign_end(self, reason: str):
        """キャンペーン終了を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("---\n\n")
            f.write("# Campaign End\n\n")
            f.write(f"- 終了理由: {reason}\n")
            f.write(f"- 総セッション数: {self.session_count}\n")
            f.write(f"- 総ターン数: {self.total_turns}\n")
            f.write(f"- 終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def _run_session_feedback(logger, gm_history, pl_history):
    """キャンペーン終了時にGM/PLのフィードバックを生成・ログ"""
    if not config.ENABLE_SESSION_FEEDBACK:
        return
    print("\n【セッション振り返り生成中...】\n")
    gm_feedback = call_gm_session_feedback(gm_history)
    print(f"【GM セッション振り返り】\n{gm_feedback}")
    logger.log_gm_feedback(gm_feedback)
    pl_feedback = call_pl_session_feedback(pl_history)
    print(f"\n【PL セッション振り返り】\n{pl_feedback}")
    logger.log_pl_feedback(pl_feedback)


def run_session(scenario_template_path: str):
    """キャンペーンを実行（複数セッション対応）"""
    
    # シナリオテンプレート読み込み
    scenario_template = load_file(scenario_template_path)
    
    logger = CampaignLogger(scenario_template)
    
    print("=" * 50)
    print("キャンペーン開始")
    print("=" * 50)
    
    # PLによるシナリオ生成
    print("\n【PLによるシナリオ生成中...】\n")
    pl_scenario = call_pl_scenario_gen(scenario_template)
    print(f"【PL シナリオ生成】\n{pl_scenario}")
    logger.log_scenario_generation(pl_scenario)
    
    # 人間の確認
    confirm = input("\n[Enter: このシナリオで開始 / r: 再生成 / q: 終了] > ")
    if confirm.lower() == "q":
        print("\nキャンペーン終了")
        logger.log_campaign_end("人間による中断（シナリオ生成後）")
        return
    elif confirm.lower() == "r":
        print("\n【シナリオ再生成中...】\n")
        pl_scenario = call_pl_scenario_gen(scenario_template)
        print(f"【PL シナリオ生成】\n{pl_scenario}")
        logger.log_scenario_generation(pl_scenario)
    
    session_num = 0
    gm_history = []
    
    # 最初のGMへの指示
    initial_prompt = f"""以下のシナリオテンプレートとPLが作成した設定でセッションを開始してください。

【シナリオテンプレート】
{scenario_template}

【PLが作成した設定】
{pl_scenario}
"""
    gm_history.append({"role": "user", "content": initial_prompt})
    
    next_session_instruction = ""  # 次セッションへの指示を保持

    while True:
        session_num += 1
        turn = 0
        pl_history = []
        
        # セッション開始
        logger.start_session(session_num, next_session_instruction)
        next_session_instruction = ""  # 指示をリセット
        
        print(f"\n{'='*50}")
        print(f"セッション {session_num} 開始")
        print("=" * 50)
        
        # GMの最初の描写
        gm_response = call_gm(gm_history)
        gm_history.append({"role": "assistant", "content": gm_response})
        
        print(f"\n【GM】\n{gm_response}")
        logger.log_turn_start(0)
        logger.log_gm(gm_response)
        
        # ターンループ
        session_ended_by_gm = False
        
        while turn < config.MAX_TURNS:
            turn += 1
            print(f"\n{'='*50}")
            print(f"セッション {session_num} - ターン {turn}")
            print("=" * 50)
            
            logger.log_turn_start(turn)
            
            # PLに状況を伝える
            pl_history.append({"role": "user", "content": f"GMからの描写：\n{gm_response}"})
            
            # PLの行動
            pl_response = call_pl(pl_history)
            pl_history.append({"role": "assistant", "content": pl_response})
            
            print(f"\n【PL】\n{pl_response}")
            logger.log_pl(pl_response)
            
            # 異常検知
            is_valid, reason = check_pl_response(pl_response)
            if not is_valid:
                print(f"\n⚠️ 異常検知: {reason}")
                logger.log_anomaly("PL", reason)
                
                pl_history.append({"role": "user", "content": "あなたはPLです。GMの役割は行わず、【行動宣言】を含めて応答してください。"})
                pl_response = call_pl(pl_history)
                pl_history.append({"role": "assistant", "content": pl_response})
                print(f"\n【PL 再試行】\n{pl_response}")
                logger.log_pl(pl_response, is_retry=True)
            
            # 人間の介入ポイント（ターン終了後）
            user_input = input("\n[Enter: 続行 / q: キャンペーン終了 / 任意の文字: GMへの指示追加] > ")
            
            if user_input.lower() == "q":
                print("\nキャンペーン終了（人間による中断）")
                logger.log_session_end("人間による中断", turn)
                _run_session_feedback(logger, gm_history, pl_history)
                logger.log_campaign_end("人間による中断")
                print(f"\nログ保存先: {logger.filepath}")
                return
            
            # GMへの指示追加
            gm_input = f"PLの行動：\n{pl_response}"
            if user_input:
                gm_input += f"\n\n【オーケストレーターからの指示】{user_input}"
                logger.log_human_input(user_input)
            
            gm_history.append({"role": "user", "content": gm_input})
            
            # GMの応答
            gm_response = call_gm(gm_history)
            gm_history.append({"role": "assistant", "content": gm_response})
            
            print(f"\n【GM】\n{gm_response}")
            logger.log_gm(gm_response)
            
            # セッション終了判定（GMが【セッション終了】を出力した場合）
            if "【セッション終了】" in gm_response:
                print("\nセッション終了（GM判断）")
                logger.log_session_end("GM判断", turn)
                session_ended_by_gm = True
                break
        
        # 最大ターン到達の場合
        if not session_ended_by_gm:
            print("\nセッション終了（最大ターン到達）")
            logger.log_session_end("最大ターン到達", turn)
        
        # PLに次回フック選択を依頼
        print("\n【PLによる次回フック選択中...】\n")
        pl_next_hook = call_pl_next_hook(gm_response)
        print(f"【PL 次回への希望】\n{pl_next_hook}")
        logger.log_pl_next_hook(pl_next_hook)
        
        # セッション終了後の選択
        print(f"\n{'='*50}")
        print("セッション終了")
        print("=" * 50)
        
        next_input = input("\n[Enter/y: 新セッション開始 / q: キャンペーン終了 / 任意の文字: 次セッションへの指示] > ")
        
        if next_input.lower() == "q":
            print("\nキャンペーン終了")
            _run_session_feedback(logger, gm_history, pl_history)
            logger.log_campaign_end("人間による終了")
            break
        elif next_input.lower() in ["", "y"]:
            # 新セッション開始（PLの希望を反映）
            gm_history.append({"role": "user", "content": f"新しいセッションを開始してください。\n\n【PLの次回への希望】\n{pl_next_hook}"})
        else:
            # 追加指示付きで新セッション開始
            next_session_instruction = next_input  # ログ記録用に保存
            gm_history.append({"role": "user", "content": f"新しいセッションを開始してください。\n\n【PLの次回への希望】\n{pl_next_hook}\n\n【オーケストレーターからの追加指示】\n{next_input}"})
    
    print("\n" + "=" * 50)
    print(f"キャンペーン完了")
    print(f"総セッション数: {session_num}")
    print(f"総ターン数: {logger.total_turns}")
    print(f"ログ保存先: {logger.filepath}")
    print("=" * 50)