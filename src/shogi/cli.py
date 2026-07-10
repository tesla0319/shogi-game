"""人対人の CLI 対局ループ（SHOGI-4l）。

平手初期局面から始め、手番側に USI 形式の合法手（または投了 `resign`）を入力させ、
局面表示 → 入力 → 着手適用 を繰り返す。状態遷移・表示・合法手生成・指し手解釈は
すべて既存モジュール（position / display / rules / usi）に委譲し、この層は
「入出力と繰り返しの制御」だけを担う（新しいゲームロジックは持たない）。

自動終局判定（詰み・行き詰まり）はこの Phase では扱わず、SHOGI-4m に分離する。
本ループは投了 `resign` と入力終了（EOF）でのみ終了する。

入出力は `input_fn` / `output_fn` として差し替え可能にする。既定は組み込みの
input / print だが、テストでは行のキューと収集リストを渡して対局を自動再現する
（対局ロジックを標準入出力から切り離してテスト可能にするため）。
"""

from shogi.display import position_to_text
from shogi.piece import Color
from shogi.position import Position, create_hirate_position
from shogi.rules import generate_legal_moves
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


def run_game(input_fn=input, output_fn=print) -> None:
    """人対人の CLI 対局を1局進める。

    平手初期局面から開始し、手番側に1手ずつ入力させる。`resign` で投了、入力終了
    （input_fn が EOFError を送出）で中断する。USI 形式として解釈できない入力・
    非合法手はメッセージを出して同じ手番のまま再入力を求める（局面・手番は変えない）。

    input_fn は1行を返す呼び出し可能オブジェクト（EOF では EOFError を送出する）。
    output_fn は1行を受け取る呼び出し可能オブジェクト。既定は組み込みの input / print。
    """
    position = create_hirate_position()
    output_fn(_render(position))

    while True:
        side = position.side_to_move
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

        # 手番側の持ち駒を渡し、駒打ちも含めた合法手と突き合わせる。
        # 合法手判定・王手放置の除外は generate_legal_moves に委ねる（この層では判定しない）
        legal_moves = generate_legal_moves(position.board, side, _current_hand(position))
        if move not in legal_moves:
            output_fn(_MSG_ILLEGAL)
            continue

        position = position.apply_move(move)
        output_fn(_render(position))
