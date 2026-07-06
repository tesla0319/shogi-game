"""合法手判定の基盤のテスト（SHOGI-3a: 盤面シミュレート）。

board_after_move が「ある手を指した後の盤面」を、取り・成りを反映しつつ
元の盤面を壊さずに作れることを検証する。
王手検出・自殺手除外・駒打ち・持ち駒は対象外（後続 Phase）。
"""

import pytest

from shogi.board import Board
from shogi.move import Move
from shogi.piece import Color, Piece, PieceType
from shogi.rules import board_after_move


def board_with(*placements: tuple[int, int, Piece]) -> Board:
    """指定した駒だけを置いた盤面を作るテスト用ヘルパー。"""
    board = Board()
    for file, rank, piece in placements:
        board.set_piece(file, rank, piece)
    return board


class Test取りも成りもない移動:
    def test_駒が移動元から移動先へ動く(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        result = board_after_move(board, Move(5, 5, 5, 4))
        assert result.get_piece(5, 5) is None
        assert result.get_piece(5, 4) == Piece(Color.BLACK, PieceType.GOLD)


class Test取りのある移動:
    def test_移動先の相手駒が取り除かれ自駒に置き換わる(self):
        # 先手金(5五) が 後手歩(5四) を取る
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 5, 5, 4))
        assert result.get_piece(5, 5) is None
        assert result.get_piece(5, 4) == Piece(Color.BLACK, PieceType.GOLD)

    def test_取った駒は持ち駒に加えない(self):
        # 持ち駒は SHOGI-4 の責務。board_after_move は盤から除去するだけ。
        # 盤上のどこにも取った後手歩が残っていないことで確認する
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 2, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 5, 5, 2))
        white_pawns = [
            (f, r)
            for f in range(1, 10)
            for r in range(1, 10)
            if result.get_piece(f, r) == Piece(Color.WHITE, PieceType.PAWN)
        ]
        assert white_pawns == []


class Test成りのある移動:
    # 成れる6駒種それぞれについて、is_promotion=True で駒種が成駒に変わること
    @pytest.mark.parametrize(
        ("before", "after"),
        [
            (PieceType.PAWN, PieceType.PROMOTED_PAWN),
            (PieceType.LANCE, PieceType.PROMOTED_LANCE),
            (PieceType.KNIGHT, PieceType.PROMOTED_KNIGHT),
            (PieceType.SILVER, PieceType.PROMOTED_SILVER),
            (PieceType.BISHOP, PieceType.HORSE),
            (PieceType.ROOK, PieceType.DRAGON),
        ],
    )
    def test_成る手で駒種が成駒に変わる(self, before, after):
        # 先手が敵陣（3段目→2段目）へ動いて成る
        board = board_with((5, 3, Piece(Color.BLACK, before)))
        result = board_after_move(board, Move(5, 3, 5, 2, is_promotion=True))
        assert result.get_piece(5, 3) is None
        assert result.get_piece(5, 2) == Piece(Color.BLACK, after)

    def test_成りと取りが同時に起きる(self):
        # 先手角(5三) が 後手歩(4二) を取りながら馬に成る
        board = board_with(
            (5, 3, Piece(Color.BLACK, PieceType.BISHOP)),
            (4, 2, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 3, 4, 2, is_promotion=True))
        assert result.get_piece(4, 2) == Piece(Color.BLACK, PieceType.HORSE)

    def test_成らない手では駒種が変わらない(self):
        board = board_with((5, 3, Piece(Color.BLACK, PieceType.SILVER)))
        result = board_after_move(board, Move(5, 3, 5, 2))  # is_promotion 既定 False
        assert result.get_piece(5, 2) == Piece(Color.BLACK, PieceType.SILVER)


class Test元の盤面を壊さない:
    def test_指した後も元の盤面は変わらない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        board_after_move(board, Move(5, 5, 5, 4))
        # 元盤面はそのまま（シミュレートは複製上で行う）
        assert board.get_piece(5, 5) == Piece(Color.BLACK, PieceType.GOLD)
        assert board.get_piece(5, 4) == Piece(Color.WHITE, PieceType.PAWN)


class Test異常系:
    def test_移動元が空きマスならValueError(self):
        board = Board()
        with pytest.raises(ValueError):
            board_after_move(board, Move(5, 5, 5, 4))

    def test_成れない駒種の成り指定はValueError(self):
        # 金は成れない。movegen は生成しないが、防御的に弾く
        board = board_with((5, 3, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            board_after_move(board, Move(5, 3, 5, 2, is_promotion=True))
