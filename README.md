# shogi-ai

将棋の対局ができるゲームを Claude Code と協働で開発するプロジェクト。
まず CLI で人対人・人対AIの対局を実現し、GUI は後続 Phase で扱う。
将棋ロジック（盤面・合法手・終局判定・AI）は既存の将棋ライブラリを使わず自作する。

## 現在の状態

**SHOGI-4 駒打ち基盤（4a〜4h）完了 / 次は SHOGI-4 の対局進行本体（CLI対局・終局判定）**

- SHOGI-0（設計）: 完了 — CLAUDE.md / Skill / 開発計画の土台
- SHOGI-1（データモデル + SFEN入出力）: 完了 — Piece / Board / 平手初期局面 / SFEN盤面部の読み書き
- SHOGI-2（駒の移動生成）: 完了 — 全14駒種の疑似合法手と成り/不成の候補生成
- SHOGI-3（合法手判定・盤上移動）: 完了 — 王手検出と「自玉が王手なら除外」フィルタで王手放置・自殺手・ピンを除外
- SHOGI-4（対局進行）: 駒打ち基盤（4a〜4h）完了 — 持ち駒（Hand）・駒打ち（Move.drop）・駒打ち候補生成・二歩/行き所のない駒/打ち歩詰めの除外・合法手への統合・駒取り時の持ち駒加算。対局進行本体（CLI対局ループ・終局判定）は未着手
- 詳細と制限事項は [docs/development-plan.md](docs/development-plan.md) の「SHOGI-4 の実施内訳」を参照

## ドキュメント構成

| ファイル | 役割 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Claude Code 向けのプロジェクト設定（技術スタック・将棋ドメインの取り決め・開発方針） |
| [docs/development-plan.md](docs/development-plan.md) | Phase分割・テスト方針・リスク・未決事項 |
| `.claude/skills/phase-implementation/` | Phase実装時の手順スキル |
| `.claude/skills/bug-fix/` | 不具合修正時の手順スキル |
| `templates/` | AI-Templates 由来のテンプレート原本（編集しない） |

## 開発の進め方

- [docs/development-plan.md](docs/development-plan.md) の Phase を上から順に、1 Phase ずつ実装する
- 各 Phase の着手前に完了条件と未決事項（（要確認）マーク）を人間が確認する
- テストは pytest。ロジック層のみを対象とし、GUI は手動確認

## セットアップ / 実行方法

- 必要環境: Python 3.12 / pytest（いずれもローカルに導入済みであること）
- テスト全実行: `python3 -m pytest`
- 対局の起動コマンドは対局進行の Phase（SHOGI-4）で追記予定
