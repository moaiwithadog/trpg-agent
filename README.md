# TRPG Agent

## 概要

TRPG Agent は、複数のLLMを使用してTRPGのGM（ゲームマスター）とPL（プレイヤー）を自動で対話させるテストプレイ用システムです。

### 目的

- TRPGルールブックのテストプレイ自動化
- LLMのTRPG能力（GM能力・PL能力）の検証
- TRPGの枠組みを活用したLLMによる物語の自動生成

### 特徴

- GM役とPL役に異なるLLM（Claude、ChatGPT等）を割り当て可能
- コンテキストを共有しない独立したLLM間での対話
- セッションログのMarkdown形式での自動保存
- PLによるシナリオ生成・次回フック選択
- 人間（オーケストレーター）による介入ポイント

---

## 動作要件

- **OS**: Windows（Mac、Linuxでの動作は未確認）
- **Python**: 3.10 以上
- **APIキー**:
  - Anthropic API（Claude使用時）
  - OpenAI API（ChatGPT使用時）

---

## クイックスタート

### 1. 環境構築

```bash
# リポジトリをクローン
git clone https://github.com/moaiwithadog/trpg-agent.git
cd trpg-agent

# 必要なライブラリをインストール
pip install anthropic openai python-dotenv
```

### 2. APIキー設定

プロジェクトルートに `.env` ファイルを作成：

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 実行

```bash
python main.py
```

---

## 概念と用語

| 用語 | 定義 |
|------|------|
| **ターン** | GMの出力とPLの入力の1往復 |
| **セッション** | 複数ターンで構成。GMが【セッション終了】を出力するまで |
| **キャンペーン** | 複数セッションで構成。人間の判断で終了 |
| **GM** | ゲームマスター。状況描写、判定、NPC操作を担当 |
| **PL** | プレイヤー。PCの行動宣言を担当 |
| **オーケストレーター** | 人間。ゲーム進行の監視と介入を担当 |

---

## ファイル構成

```
trpg-agent/
├── .env                 # APIキー（Git管理外）
├── .gitignore
├── config.py            # GM/PL設定
├── agents.py            # LLM呼び出し
├── orchestrator.py      # ゲーム進行管理
├── main.py              # エントリポイント
├── rulebook.md          # TRPGルールブック
├── scenarios/
│   └── template_fantasy.md  # シナリオテンプレート
└── logs/
    └── campaign_*.md    # セッションログ
```

---

## 設定リファレンス

### config.py

```python
# GM設定
GM_PROVIDER = "anthropic"  # "anthropic" or "openai"
GM_MODEL = "claude-sonnet-4-20250514"

# PL設定
PL_PROVIDER = "openai"  # "anthropic" or "openai"
PL_MODEL = "gpt-4o-mini"

# ゲーム設定
MAX_TURNS = 50  # 1セッションの最大ターン数(安全装置として)
```

### ルールブック（rulebook.md）

GMとPLの両方に共有されるゲームルールを定義します。変更することでゲームシステムをカスタマイズできます。

### シナリオテンプレート（scenarios/*.md）

ゲームの舞台・大目的・世界設定を定義します。
プリセットの```scenarios/template_fantasy.md```では、
- 王道ファンタジー的な舞台設定
- PLがPCキャラと初期目的を設定する
と定義しています。

シナリオ変更で、運用目的に応じた調整が可能です。

**固定シナリオ（検証用）の例：**
```markdown
## PC設定（固定）
- 名前: カイト
- 職業: 元傭兵の探索者
...

## PLへの指示
上記のPC設定をそのまま使用してください。
```

**発散シナリオ（創造性テスト）の例：**
```markdown
## PLへの指示
舞台、世界設定、PC設定をすべて自由に作成してください。
```

---

## 運用ガイド

### 操作方法

**ターン終了後：**
| 入力 | 動作 |
|------|------|
| `Enter` | 次ターンへ |
| `q` | キャンペーン終了 |
| 任意の文字 | GMへの指示追加 |

**セッション終了後：**
| 入力 | 動作 |
|------|------|
| `Enter` / `y` | 新セッション開始 |
| `q` | キャンペーン終了 |
| 任意の文字 | 次セッションへの指示 |

### ログ解析

保存されたログ（`logs/campaign_*.md`）をLLMに読ませて分析できます。

**分析プロンプト例：**
```
添付したファイルはTRPGのセッションログです。以下の観点で分析してください。
- ルール遵守（GMの出力フォーマット、状態表示の欠落）
- 役割分担（PLがGMの役割を侵していないか）
- ゲーム品質（物語の一貫性、テンポ）
- 改善提案
```

---

## トラブルシューティング

### GM役のモデル選択

GM役には能力の高いモデルを充てることを推奨します。

- **推奨**: Claude Sonnet、GPT-4o
- **非推奨**: Claude Haiku（出力が不安定になりやすい）

Claude Haikuでのテストでは、10ターン前後でGMの描写が途中で止まる→PLがそれを拾ってGMを補完しようと頑張っちゃう、といった不思議現象が発生してしまいました。(2026年1月時点)

### セッション終了が検知されない

GMが【セッション終了】を正しく出力しない場合があります（特にChatGPT GM）。

**対処法(対処済み)：**
`rulebook.md` の終了ルールを明確化：
```markdown
- 終了時は```【セッション終了】```と明記する。
```

バッククォートで囲むことで、出力形式が守られやすくなりました。
(似たようなことは他にも起きるかもしれません。
 Pythonスクリプトを直すことでも対応可能でしょうが、mdファイルのほうが編集しやすいですよね。)

---

## ライセンス

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 奥付
- 公開用初版 2026/02/08
  - もあいぬ (企画 兼 テスター)
  - Anthropic Claude Opus 4.5 (それ以外のことは、ほとんどこの子がやってくれた)