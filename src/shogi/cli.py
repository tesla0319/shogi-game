"""人対人の CLI 対局ループ（SHOGI-4l・自動終局判定 SHOGI-4m）。

平手初期局面から始め、手番側に USI 形式の合法手（または投了 `resign`）を入力させ、
局面表示 → 入力 → 着手適用 を繰り返す。状態遷移・表示・合法手生成・指し手解釈は
すべて既存モジュール（position / display / rules / usi）に委譲し、この層は
「入出力と繰り返しの制御」だけを担う（新しいゲームロジックは持たない）。

自動終局判定（SHOGI-4m）: 各手番の入力を求める前に手番側の合法手を生成し、0件なら
終局とする。王手されていれば詰み（相手の勝ち）、王手されていなければ「合法手なし」で
手番側の負け。判定は既存の generate_legal_moves と is_in_check の組み合わせだけで行い、
新しい終局判定モジュールや列挙型は導入しない。千日手・持将棋・入玉宣言は扱わない。
本ループは詰み／合法手なし／投了 `resign` ／入力終了（EOF）のいずれかで終了する。

入出力は `input_fn` / `output_fn` として差し替え可能にする。既定は組み込みの
input / print だが、テストでは行のキューと収集リストを渡して対局を自動再現する
（対局ロジックを標準入出力から切り離してテスト可能にするため）。
"""

from shogi.display import position_to_text
from shogi.piece import Color
from shogi.position import Position, create_hirate_position
from shogi.rules import generate_legal_moves, is_in_check
from shogi.usi import move_from_usi

# 投了として受け付ける入力（完全一致のみ）。表記ゆれは受け付けない
_RESIGN_INPUT = "resign"

# 手番の表示ラベル
_SIDE_LABELS = {Color.BLACK: "先手", Color.WHITE: "後手"}

# 画面に出すメッセージ（文言を1か所に集約し、テストからも参照しやすくする）
_MSG_PROMPT = "{side}の手を入力してください（USI形式、投了は resign）:"
_MSG_BAD_USI = "USI形式として解釈できません。もう一度入力してください。"
_MSG_ILLEGAL = "非合法手です。もう一度入力してください。"
_MSG_RESIGN = "{loser}が投了しました。{winner}の勝ちです。"
_MSG_EOF = "入力が終了したため、対局を終了します。"
_MSG_CHECKMATE = "{loser}は詰みです。{winner}の勝ちです。"
_MSG_NO_MOVES = "{loser}に合法手がありません。{winner}の勝ちです。"


def _opponent(color: Color) -> Color:
    """手番の相手を返す。"""
    return Color.WHITE if color is Color.BLACK else Color.BLACK


def _current_hand(position: Position):
    """手番側の持ち駒を返す（合法手生成に渡して駒打ちも候補に含めるため）。"""
    return (
        position.black_hand
        if position.side_to_move is Color.BLACK
        else position.white_hand
    )


def _render(position: Position) -> str:
    """現局面を表示用の文字列にする（display に委譲）。"""
    return position_to_text(
        position.board,
        position.black_hand,
        position.white_hand,
        position.side_to_move,
    )


def run_game(input_fn=input, output_fn=print, start_position: Position | None = None) -> None:
    """人対人の CLI 対局を1局進める。

    既定では平手初期局面から開始する（start_position を渡すとその局面から始める。
    詰み・行き詰まりなど任意局面から動作を確かめるためのフックで、既定は None）。
    各手番では、入力を求める前に手番側の合法手を生成し、0件なら自動終局する
    （王手中なら詰みで相手の勝ち、そうでなければ合法手なしで手番側の負け）。
    合法手があれば手番側に1手入力させる。`resign` で投了、入力終了（input_fn が
    EOFError を送出）で中断する。USI 形式として解釈できない入力・非合法手はメッセージを
    出して同じ手番のまま再入力を求める（局面・手番は変えない）。

    input_fn は1行を返す呼び出し可能オブジェクト（EOF では EOFError を送出する）。
    output_fn は1行を受け取る呼び出し可能オブジェクト。既定は組み込みの input / print。
    """
    position = (
        start_position if start_position is not None else create_hirate_position()
    )
    output_fn(_render(position))

    while True:
        side = position.side_to_move

        # 入力を求める前に終局判定する。手番側に合法手が1つも無ければ対局終了。
        # 王手中なら詰み（相手の勝ち）、王手でなければ「指し手なし」で手番側の負け。
        legal_moves = generate_legal_moves(position.board, side, _current_hand(position))
        if not legal_moves:
            winner = _opponent(side)
            template = (
                _MSG_CHECKMATE
                if is_in_check(position.board, side)
                else _MSG_NO_MOVES
            )
            output_fn(
                template.format(
                    loser=_SIDE_LABELS[side], winner=_SIDE_LABELS[winner]
                )
            )
            return

        output_fn(_MSG_PROMPT.format(side=_SIDE_LABELS[side]))

        try:
            raw = input_fn()
        except EOFError:
            # Ctrl-D などの入力終了。例外トレースを出さず穏やかに終える
            output_fn(_MSG_EOF)
            return

        move_text = raw.strip()

        if move_text == _RESIGN_INPUT:
            winner = _opponent(side)
            output_fn(
                _MSG_RESIGN.format(
                    loser=_SIDE_LABELS[side], winner=_SIDE_LABELS[winner]
                )
            )
            return

        try:
            move = move_from_usi(move_text)
        except ValueError:
            # USI として形が不正。局面は変えずに再入力
            output_fn(_MSG_BAD_USI)
            continue

        # 上で生成済みの合法手（駒打ち含む）と突き合わせる。合法手判定・王手放置の除外は
        # generate_legal_moves に委ねており、この層では判定しない
        if move not in legal_moves:
            output_fn(_MSG_ILLEGAL)
            continue

        position = position.apply_move(move)
        output_fn(_render(position))
