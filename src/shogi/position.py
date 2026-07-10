"""対局状態（局面）の集約と着手による状態遷移（SHOGI-4k）。

盤面・両者の持ち駒・手番を1つの Position にまとめ、着手を適用した「次の局面」を
元の局面を壊さずに作る。これまで呼び出し側がバラバラに持ち回っていた
(board, hand, color) を1つの値にまとめ、CLI 対局ループが状態を1オブジェクトで
扱えるようにするためのもの。

責務は「状態の保持」と「着手による状態遷移の計算」だけに絞る。着手が合法か
（合法手か・王手放置でないか）の判定や終局判定は行わず、呼び出し側（対局ループ）が
`rules.generate_legal_moves` などで確認済みの手を渡す前提とする。
盤面更新・持ち駒の増減そのものは既存の `rules.position_after_move` に委譲し、
Position はそこに「両者の持ち駒管理」と「手番の反転」を足すだけにする。
"""

from dataclasses import dataclass

from shogi import rules
from shogi.board import Board
from shogi.hand import Hand
from shogi.initial_position import create_hirate_board
from shogi.move import Move
from shogi.piece import Color


@dataclass(frozen=True)
class Position:
    """1局面。盤面・先手の持ち駒・後手の持ち駒・手番を保持する。

    frozen=True にしているのは、着手のたびに「次の局面」を新しく作る値オブジェクトとして
    扱い、既存局面を上書きしないため（合法手の試し打ちや履歴保持を壊さない）。
    ただし board / black_hand / white_hand の中身（Board・Hand）は可変オブジェクトなので、
    apply_move は必ず新しい Board・Hand を持つ Position を返し、元の Position が持つ
    オブジェクトには一切触れない（下記メソッド参照）。

    合法性・終局の判定は持たない（呼び出し側の責務）。
    """

    board: Board
    black_hand: Hand
    white_hand: Hand
    side_to_move: Color

    def apply_move(self, move: Move) -> "Position":
        """`move` を指した後の局面を、元の局面（self）を壊さずに新しく作って返す。

        盤面更新と手番側の持ち駒増減は既存の `rules.position_after_move` に委譲する
        （盤上移動の駒取りは手番側の持ち駒に加わり、駒打ちは手番側から1枚減る）。
        相手側の持ち駒はこの手では変化しないので、そのまま引き継ぐ。最後に手番を反転する。

        合法性は検証しない。`rules.position_after_move` が送出する例外
        （例: 持ち駒が無い駒を打つと ValueError）はそのまま呼び出し側へ伝播させる。
        """
        mover_hand = (
            self.black_hand if self.side_to_move is Color.BLACK else self.white_hand
        )
        next_board, next_mover_hand = rules.position_after_move(
            self.board, mover_hand, self.side_to_move, move
        )

        # 相手側の持ち駒はこの手では変わらない。値オブジェクトとして独立させるため、
        # 参照を共有せず複製して引き継ぐ（元 Position の Hand を誤って共有・変更しない）。
        if self.side_to_move is Color.BLACK:
            next_black_hand = next_mover_hand
            next_white_hand = self.white_hand.copy()
        else:
            next_black_hand = self.black_hand.copy()
            next_white_hand = next_mover_hand

        next_side = Color.WHITE if self.side_to_move is Color.BLACK else Color.BLACK
        return Position(next_board, next_black_hand, next_white_hand, next_side)


def create_hirate_position() -> Position:
    """平手初期局面の Position を返す（平手盤・両者持ち駒なし・先手番）。

    盤面の生成は既存の `create_hirate_board` に委譲する（初期配置の定義を二重に持たない）。
    """
    return Position(
        board=create_hirate_board(),
        black_hand=Hand(),
        white_hand=Hand(),
        side_to_move=Color.BLACK,
    )
