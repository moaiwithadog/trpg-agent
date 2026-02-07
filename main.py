"""TRPG Agent - メインエントリポイント"""
from orchestrator import run_session

# シナリオテンプレートのパス
SCENARIO_TEMPLATE_PATH = "scenarios/template_fantasy.md"

if __name__ == "__main__":
    run_session(SCENARIO_TEMPLATE_PATH)