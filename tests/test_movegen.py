"""疑似合法手生成のテスト（SHOGI-2a: 歩、SHOGI-2b: 香車）。

疑似合法手の範囲（盤外・味方駒マスの除外、走り駒の停止位置）のみを検証する。
二歩・王手放置などの反則除外（SHOGI-3）、成り、駒打ちは対象外。
"""

import pytest

from shogi.board import Board
from shogi.initial_position import create_hirate_board
from shogi.move import Move
from shogi.movegen import generate_lance_moves, generate_pawn_moves
from shogi.piece import Color, Piece, PieceType


def board_with(*placements: tuple[int, int, Piece]) -> Board:
    """指定した駒だけを置いた盤面を作るテスト用ヘルパー。"""
    board = Board()
    for file, rank, piece in placements:
        board.set_piece(file, rank, piece)
    return board


class Test歩の進む方向:
    def test_先手の歩は奥へ1マス進む(self):
        # 5五の先手歩 → 5四へ（rank が 1 減る）
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 4)]

    def test_後手の歩は手前へ1マス進む(self):
        # 5五の後手歩 → 5六へ（rank が 1 増える）
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 6)]

    @pytest.mark.parametrize("file", [1, 9])
    def test_端の筋でも同じように進める(self, file):
        board = board_with((file, 5, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, file, 5) == [Move(file, 5, file, 4)]


class Test盤の端:
    def test_最奥の段の先手歩は動けない(self):
        # rank=1 の先手歩の移動先は盤外。実局面では行き所のない駒（SHOGI-3 の反則）
        # だが、疑似合法手の層では「候補なし」として空リストを返す
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 1) == []

    def test_最奥の段の後手歩は動けない(self):
        board = board_with((5, 9, Piece(Color.WHITE, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 9) == []


class Test移動先の駒:
    def test_移動先に味方駒があると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.BLACK, PieceType.GOLD)),
        )
        assert generate_pawn_moves(board, 5, 5) == []

    def test_移動先に相手駒があれば進める_取る手になる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.WHITE, PieceType.GOLD)),
        )
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 4)]

    def test_後手の歩も味方駒に塞がれると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
            (5, 6, Piece(Color.WHITE, PieceType.SILVER)),
        )
        assert generate_pawn_moves(board, 5, 5) == []


class Test平手初期局面:
    @pytest.mark.parametrize("file", range(1, 10))
    def test_先手の歩9枚はそれぞれ1マス進める(self, file):
        board = create_hirate_board()
        assert generate_pawn_moves(board, file, 7) == [Move(file, 7, file, 6)]

    @pytest.mark.parametrize("file", range(1, 10))
    def test_後手の歩9枚はそれぞれ1マス進める(self, file):
        board = create_hirate_board()
        assert generate_pawn_moves(board, file, 3) == [Move(file, 3, file, 4)]


class Test異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_pawn_moves(Board(), 5, 5)

    def test_歩以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            generate_pawn_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_pawn_moves(Board(), 0, 5)


class Test香車の走り:
    def test_先手の香は前方向へ盤の端まで走る(self):
        # 空盤の5九の先手香 → 5八〜5一の8マス（近い順）
        board = board_with((5, 9, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, to_rank) for to_rank in range(8, 0, -1)
        ]

    def test_後手の香は後方向へ盤の端まで走る(self):
        # 空盤の5一の後手香 → 5二〜5九の8マス（近い順）
        board = board_with((5, 1, Piece(Color.WHITE, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 1) == [
            Move(5, 1, 5, to_rank) for to_rank in range(2, 10)
        ]

    def test_盤の途中からは残りの段だけ走る(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 5) == [
            Move(5, 5, 5, 4),
            Move(5, 5, 5, 3),
            Move(5, 5, 5, 2),
            Move(5, 5, 5, 1),
        ]

    def test_最奥の段の香は動けない(self):
        # 実局面では行き所のない駒（SHOGI-3 の反則）だが、ここでは候補なし
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 1) == []


class Test香車の停止:
    def test_味方駒の手前で停止しそのマスは含めない(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, 8),
            Move(5, 9, 5, 7),
            Move(5, 9, 5, 6),
        ]

    def test_相手駒のマスで停止しそのマスは含める(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, 8),
            Move(5, 9, 5, 7),
            Move(5, 9, 5, 6),
            Move(5, 9, 5, 5),  # 相手駒を取る手
        ]

    def test_相手駒の先へは飛び越えられない(self):
        # 相手駒で停止した後ろにある空きマス（5四〜5一）が含まれないこと
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
        )
        moves = generate_lance_moves(board, 5, 9)
        assert all(move.to_rank >= 5 for move in moves)

    def test_隣が味方駒なら候補なし(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 8, Piece(Color.BLACK, PieceType.GOLD)),
        )
        assert generate_lance_moves(board, 5, 9) == []

    def test_隣が相手駒ならその1マスだけ(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 8, Piece(Color.WHITE, PieceType.GOLD)),
        )
        assert generate_lance_moves(board, 5, 9) == [Move(5, 9, 5, 8)]

    def test_後手の香も味方駒の手前で停止する(self):
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.LANCE)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 1) == [
            Move(5, 1, 5, 2),
            Move(5, 1, 5, 3),
        ]


class Test香車の平手初期局面:
    @pytest.mark.parametrize("file", [1, 9])
    def test_先手の香は自陣の歩の手前まで動ける(self, file):
        # 九段目の香は七段目の味方歩に塞がれ、八段目の1マスのみ
        board = create_hirate_board()
        assert generate_lance_moves(board, file, 9) == [Move(file, 9, file, 8)]

    @pytest.mark.parametrize("file", [1, 9])
    def test_後手の香も自陣の歩の手前まで動ける(self, file):
        board = create_hirate_board()
        assert generate_lance_moves(board, file, 1) == [Move(file, 1, file, 2)]


class Test香車の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_lance_moves(Board(), 5, 5)

    def test_香車以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.PAWN)))
        with pytest.raises(ValueError):
            generate_lance_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_lance_moves(Board(), 5, 10)
