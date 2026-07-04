# shogi-ai

将棋の対局ができるゲームを Claude Code と協働で開発するプロジェクト。
まず CLI で人対人・人対AIの対局を実現し、GUI は後続 Phase で扱う。
将棋ロジック（盤面・合法手・終局判定・AI）は既存の将棋ライブラリを使わず自作する。

## 現在の状態

**SHOGI-0（設計フェーズ）** — ゲームロジックの実装は未着手。
Claude Code との連携土台（CLAUDE.md / Skill / 開発計画）の骨子を作成し、人間のレビュー待ち。

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

（SHOGI-1 以降で追記。現時点で実行できるコードはない）
