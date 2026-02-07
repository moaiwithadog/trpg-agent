"""オーケストレーター：ゲーム進行を管理"""
import re
import os
from datetime import datetime
from agents import call_gm, call_pl
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


class SessionLogger:
    """セッションログをMarkdown形式で保存"""
    
    def __init__(self, scenario: str):
        # logsフォルダがなければ作成
        os.makedirs("logs", exist_ok=True)
        
        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = f"logs/session_{timestamp}.md"
        
        # ヘッダーを書き込み
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("# TRPG Session Log\n\n")
            f.write("## セッション情報\n\n")
            f.write(f"- 日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- GMモデル: {config.GM_MODEL}\n")
            f.write(f"- PLモデル: {config.PL_MODEL}\n\n")
            f.write("## シナリオ\n\n")
            f.write(f"{scenario}\n\n")
            f.write("---\n\n")
        
        print(f"📄 ログファイル: {self.filepath}")
    
    def log_turn_start(self, turn: int):
        """ターン開始を記録"""
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
        if input_text and input_text.lower() != "q":
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(f"### 【オーケストレーター介入】\n\n")
                f.write(f"{input_text}\n\n")
    
    def log_session_end(self, reason: str, total_turns: int):
        """セッション終了を記録"""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write("---\n\n")
            f.write("## セッション終了\n\n")
            f.write(f"- 終了理由: {reason}\n")
            f.write(f"- 総ターン数: {total_turns}\n")
            f.write(f"- 終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def run_session(scenario_start: str):
    """セッションを実行"""
    gm_history = []
    pl_history = []
    
    turn = 0
    end_reason = "最大ターン到達"
    
    # ロガー初期化
    logger = SessionLogger(scenario_start)
    
    print("=" * 50)
    print("セッション開始")
    print("=" * 50)
    
    # 最初のGM描写
    gm_history.append({"role": "user", "content": f"以下の設定でセッションを開始してください：\n{scenario_start}"})
    gm_response = call_gm(gm_history)
    gm_history.append({"role": "assistant", "content": gm_response})
    
    print(f"\n【GM】\n{gm_response}")
    logger.log_turn_start(0)
    logger.log_gm(gm_response)
    
    while turn < config.MAX_TURNS:
        turn += 1
        print(f"\n{'='*50}")
        print(f"ターン {turn}")
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
            
            # 再試行
            pl_history.append({"role": "user", "content": "あなたはPLです。GMの役割は行わず、【行動宣言】を含めて応答してください。"})
            pl_response = call_pl(pl_history)
            pl_history.append({"role": "assistant", "content": pl_response})
            print(f"\n【PL 再試行】\n{pl_response}")
            logger.log_pl(pl_response, is_retry=True)
        
        # 人間の介入ポイント
        user_input = input("\n[Enter: 続行 / q: 終了 / 任意の文字: GMへの指示追加] > ")
        if user_input.lower() == "q":
            print("\nセッション終了（人間による中断）")
            end_reason = "人間による中断"
            break
        
        logger.log_human_input(user_input)
        
        # GMにPLの行動を伝える
        gm_input = f"PLの行動：\n{pl_response}"
        if user_input and user_input.lower() != "q":
            gm_input += f"\n\n【オーケストレーターからの指示】{user_input}"
        
        gm_history.append({"role": "user", "content": gm_input})
        
        # GMの応答
        gm_response = call_gm(gm_history)
        gm_history.append({"role": "assistant", "content": gm_response})
        
        print(f"\n【GM】\n{gm_response}")
        logger.log_gm(gm_response)
        
        # セッション終了判定
        if "【セッション終了】" in gm_response:
            print("\nセッション終了（GM判断）")
            end_reason = "GM判断"
            break
    
    logger.log_session_end(end_reason, turn)
    
    print("\n" + "=" * 50)
    print(f"セッション完了：全{turn}ターン")
    print(f"ログ保存先: {logger.filepath}")
    print("=" * 50)