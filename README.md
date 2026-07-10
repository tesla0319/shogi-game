# shogi-ai

将棋の対局ができるゲームを Claude Code と協働で開発するプロジェクト。
まず CLI で人対人・人対AIの対局を実現し、GUI は後続 Phase で扱う。
将棋ロジック（盤面・合法手・終局判定・AI）は既存の将棋ライブラリを使わず自作する。

## 現在の状態

**SHOGI-4（対局進行・人対人CLI対局）完了（4a〜4m）/ 次は SHOGI-5（AI v1 + 人対AI）**

- SHOGI-0（設計）: 完了 — CLAUDE.md / Skill / 開発計画の土台
- SHOGI-1（データモデル + SFEN入出力）: 完了 — Piece / Board / 平手初期局面 / SFEN盤面部の読み書き
- SHOGI-2（駒の移動生成）: 完了 — 全14駒種の疑似合法手と成り/不成の候補生成
- SHOGI-3（合法手判定・盤上移動）: 完了 — 王手検出と「自玉が王手なら除外」フィルタで王手放置・自殺手・ピンを除外
- SHOGI-4（対局進行）: 完了（4a〜4m）— 持ち駒（Hand）・駒打ち（Move.drop）・駒打ち候補生成・二歩/行き所のない駒/打ち歩詰めの除外・合法手への統合・駒取り時の持ち駒加算。USI指し手表記と Move の相互変換（`move_from_usi` / `move_to_usi`。通常手・成り手・駒打ちに対応、形式変換のみで合法性は判定しない）。局面のテキスト表示（`position_to_text`。盤面・両者持ち駒・手番を可読な文字列にする純関数）。盤面・両者の持ち駒・手番を保持する `Position` を追加し、`apply_move()` で状態を壊さず次局面へ遷移（合法性と終局判定は Position の責務外）。人対人の CLI 対局ループ（`cli.py` の `run_game`。`python -m shogi` で起動、USI入力と `resign` に対応）。合法手0件で自動終局（王手中なら詰み・相手勝ち、そうでなければ合法手なし・手番側の負け）。千日手・持将棋・入玉宣言は対象外
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
- 人対人の CLI 対局: `PYTHONPATH=src python3 -m shogi`（USI形式で指し手を入力、`resign` で投了。自動終局判定は未実装）
