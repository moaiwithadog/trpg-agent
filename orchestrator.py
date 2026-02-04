"""オーケストレーター：ゲーム進行を管理"""
import re
from agents import call_gm, call_pl
import config


def check_pl_response(response: str) -> tuple[bool, str]:
    """PLの応答が正常か確認"""
    # 【行動宣言】が含まれているかチェック
    if "【行動宣言】" not in response:
        return False, "行動宣言がありません"
    
    # GM的な振る舞いの検出
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
        r"についてどうしますか",
    ]
    for pattern in gm_patterns:
        if re.search(pattern, response):
            return False, f"GM的な振る舞いを検出: {pattern}"
    
    return True, "OK"


def run_session(scenario_start: str):
    """セッションを実行"""
    # 履歴管理（GMとPLで別々に管理）
    gm_history = []
    pl_history = []
    
    turn = 0
    
    print("=" * 50)
    print("セッション開始")
    print("=" * 50)
    
    # 最初のGM描写
    gm_history.append({"role": "user", "content": f"以下の設定でセッションを開始してください：\n{scenario_start}"})
    gm_response = call_gm(gm_history)
    gm_history.append({"role": "assistant", "content": gm_response})
    
    print(f"\n【GM】\n{gm_response}")
    
    while turn < config.MAX_TURNS:
        turn += 1
        print(f"\n{'='*50}")
        print(f"ターン {turn}")
        print("=" * 50)
        
        # PLに状況を伝える
        pl_history.append({"role": "user", "content": f"GMからの描写：\n{gm_response}"})
        
        # PLの行動
        pl_response = call_pl(pl_history)
        pl_history.append({"role": "assistant", "content": pl_response})
        
        print(f"\n【PL】\n{pl_response}")
        
        # 異常検知
        is_valid, reason = check_pl_response(pl_response)
        if not is_valid:
            print(f"\n⚠️ 異常検知: {reason}")
            # 再試行
            pl_history.append({"role": "user", "content": "あなたはPLです。GMの役割は行わず、【行動宣言】を含めて応答してください。"})
            pl_response = call_pl(pl_history)
            pl_history.append({"role": "assistant", "content": pl_response})
            print(f"\n【PL 再試行】\n{pl_response}")
        
        # 人間の介入ポイント
        user_input = input("\n[Enter: 続行 / q: 終了 / 任意の文字: GMへの指示追加] > ")
        if user_input.lower() == "q":
            print("\nセッション終了（人間による中断）")
            break
        
        # GMにPLの行動を伝える
        gm_input = f"PLの行動：\n{pl_response}"
        if user_input and user_input.lower() != "q":
            gm_input += f"\n\n【オーケストレーターからの指示】{user_input}"
        
        gm_history.append({"role": "user", "content": gm_input})
        
        # GMの応答
        gm_response = call_gm(gm_history)
        gm_history.append({"role": "assistant", "content": gm_response})
        
        print(f"\n【GM】\n{gm_response}")
        
        # セッション終了判定（GMが終了を宣言したら）
        if "【セッション終了】" in gm_response:
            print("\nセッション終了（GM判断）")
            break
    
    print("\n" + "=" * 50)
    print(f"セッション完了：全{turn}ターン")
    print("=" * 50)