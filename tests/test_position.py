"""対局状態（Position）と着手適用（SHOGI-4k）のテスト。

Position が盤面・両者持ち駒・手番を保持し、apply_move が「元の局面を壊さずに
次の局面を作る」こと（状態遷移の正しさと不変性）を検証する。
合法性・終局判定は Position の責務ではないため対象外。
"""

import pytest

from shogi.hand import Hand
from shogi.move import Move
from shogi.piece import Color, PieceType
from shogi.position import Position, create_hirate_position
from shogi.sfen import board_from_sfen, board_to_sfen

# 平手初期局面の盤面部 SFEN（照合用）
_HIRATE_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL"


def _empty_position(black_hand: Hand, white_hand: Hand, side: Color) -> Position:
    """空盤 + 指定の持ち駒・手番の Position を作るテスト用ヘルパ。"""
    return Position(board_from_sfen("9/9/9/9/9/9/9/9/9"), black_hand, white_hand, side)


class TestInitialPosition:
    """平手初期局面の生成。"""

    def test_盤面は平手初期局面(self):
        pos = create_hirate_position()
        assert board_to_sfen(pos.board) == _HIRATE_SFEN

    def test_両者の持ち駒は空(self):
        pos = create_hirate_position()
        assert pos.black_hand.count(PieceType.PAWN) == 0
        assert pos.white_hand.count(PieceType.PAWN) == 0

    def test_手番は先手(self):
        assert create_hirate_position().side_to_move is Color.BLACK


class TestNormalMove:
    """取りのない通常移動。"""

    def test_盤面が更新され手番が反転する(self):
        # 平手から先手 7g7f（7筋7段 → 7筋6段）
        pos = create_hirate_position()
        nxt = pos.apply_move(Move(7, 7, 7, 6))
        # 7g が空き、7f に先手歩
        assert nxt.board.get_piece(7, 7) is None
        assert nxt.board.get_piece(7, 6).piece_type is PieceType.PAWN
        assert nxt.side_to_move is Color.WHITE

    def test_取りがなければ持ち駒は増えない(self):
        pos = create_hirate_position()
        nxt = pos.apply_move(Move(7, 7, 7, 6))
        assert nxt.black_hand.count(PieceType.PAWN) == 0


class TestCapture:
    """駒取りで手番側の持ち駒に加わる（先手・後手の両分岐）。"""

    def test_先手が取ると先手の持ち駒に加わる(self):
        # 5五先手飛 → 5四後手歩 を取る（5,5 → 5,4）
        #   rank4: 5筋に後手歩 / rank5: 5筋に先手飛
        pos = Position(
            board_from_sfen("9/9/9/4p4/4R4/9/9/9/9"), Hand(), Hand(), Color.BLACK
        )
        nxt = pos.apply_move(Move(5, 5, 5, 4))
        assert nxt.board.get_piece(5, 4).piece_type is PieceType.ROOK
        assert nxt.black_hand.count(PieceType.PAWN) == 1  # 取った歩が先手の持ち駒に
        assert nxt.white_hand.count(PieceType.PAWN) == 0
        assert nxt.side_to_move is Color.WHITE

    def test_後手が取ると後手の持ち駒に加わる(self):
        # 5五後手飛 → 5四先手歩 を取る。手番は後手
        pos = Position(
            board_from_sfen("9/9/9/4P4/4r4/9/9/9/9"), Hand(), Hand(), Color.WHITE
        )
        nxt = pos.apply_move(Move(5, 5, 5, 4))
        assert nxt.white_hand.count(PieceType.PAWN) == 1  # 取った歩が後手の持ち駒に
        assert nxt.black_hand.count(PieceType.PAWN) == 0
        assert nxt.side_to_move is Color.BLACK


class TestDrop:
    """駒打ちで手番側の持ち駒が1枚減る。"""

    def test_打つと盤に置かれ持ち駒が減る(self):
        black = Hand()
        black.add(PieceType.GOLD)
        pos = _empty_position(black, Hand(), Color.BLACK)
        nxt = pos.apply_move(Move.drop(PieceType.GOLD, 5, 5))
        placed = nxt.board.get_piece(5, 5)
        assert placed.piece_type is PieceType.GOLD
        assert placed.color is Color.BLACK
        assert nxt.black_hand.count(PieceType.GOLD) == 0
        assert nxt.side_to_move is Color.WHITE


class TestConsecutiveMoves:
    """着手を続けて適用でき、手番が交互に反転する。"""

    def test_先手後手と続けて指せる(self):
        pos = create_hirate_position()
        pos = pos.apply_move(Move(7, 7, 7, 6))  # 先手 7g7f
        pos = pos.apply_move(Move(3, 3, 3, 4))  # 後手 3c3d
        assert pos.board.get_piece(7, 6).piece_type is PieceType.PAWN
        assert pos.board.get_piece(3, 4).piece_type is PieceType.PAWN
        assert pos.side_to_move is Color.BLACK  # 2手指すと手番が戻る


class TestImmutability:
    """apply_move が元の Position を壊さない。"""

    def test_元の盤面と持ち駒は変化しない(self):
        pos = Position(
            board_from_sfen("9/9/9/4p4/4R4/9/9/9/9"), Hand(), Hand(), Color.BLACK
        )
        before_sfen = board_to_sfen(pos.board)
        pos.apply_move(Move(5, 5, 5, 4))  # 取りのある手を適用（戻り値は捨てる）
        # 元の Position はそのまま
        assert board_to_sfen(pos.board) == before_sfen
        assert pos.black_hand.count(PieceType.PAWN) == 0
        assert pos.side_to_move is Color.BLACK

    def test_引き継いだ相手持ち駒は独立している(self):
        # 先手が指した後、新局面の後手持ち駒を触っても元局面に影響しない
        pos = create_hirate_position()
        nxt = pos.apply_move(Move(7, 7, 7, 6))
        nxt.white_hand.add(PieceType.PAWN)
        assert pos.white_hand.count(PieceType.PAWN) == 0


class TestErrorPropagation:
    """既存 API の例外がそのまま伝播する。"""

    def test_持ち駒がない駒打ちはValueError(self):
        # 持ち駒ゼロで歩を打つと Hand.remove の ValueError が伝わる
        pos = _empty_position(Hand(), Hand(), Color.BLACK)
        with pytest.raises(ValueError):
            pos.apply_move(Move.drop(PieceType.PAWN, 5, 5))
