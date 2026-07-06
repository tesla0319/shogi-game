"""Board クラスのテスト（SHOGI-1c）。

盤面の状態保持と空盤初期化だけを検証する。初期局面・SFEN・駒の移動は対象外。
"""

import pytest

from shogi.board import BOARD_SIZE, Board
from shogi.piece import Color, Piece, PieceType


class TestBoard初期化:
    def test_生成直後は全81マスが空である(self):
        board = Board()
        for file in range(1, BOARD_SIZE + 1):
            for rank in range(1, BOARD_SIZE + 1):
                assert board.get_piece(file, rank) is None

    def test_複数の盤面は状態を共有しない(self):
        # 内部リストの行共有バグ（[[None] * 9] * 9）や盤面間の共有がないことの確認
        board1 = Board()
        board2 = Board()
        board1.set_piece(5, 5, Piece(Color.BLACK, PieceType.PAWN))
        assert board2.get_piece(5, 5) is None

    def test_同じ盤面内で行が共有されていない(self):
        board = Board()
        board.set_piece(5, 1, Piece(Color.BLACK, PieceType.PAWN))
        # 行リストが共有されていると (5, 1) への配置が全段に波及する
        for rank in range(2, BOARD_SIZE + 1):
            assert board.get_piece(5, rank) is None


class TestBoardマスの読み書き:
    def test_置いた駒を同じマスから取得できる(self):
        board = Board()
        piece = Piece(Color.WHITE, PieceType.ROOK)
        board.set_piece(2, 8, piece)
        assert board.get_piece(2, 8) == piece

    def test_駒を置いても他のマスは空のままである(self):
        board = Board()
        board.set_piece(2, 8, Piece(Color.WHITE, PieceType.ROOK))
        assert board.get_piece(8, 2) is None  # file と rank の取り違えがないこと
        assert board.get_piece(2, 7) is None

    def test_Noneを置くとマスが空になる(self):
        board = Board()
        board.set_piece(5, 5, Piece(Color.BLACK, PieceType.GOLD))
        board.set_piece(5, 5, None)
        assert board.get_piece(5, 5) is None

    @pytest.mark.parametrize(("file", "rank"), [(1, 1), (9, 1), (1, 9), (9, 9)])
    def test_四隅のマスに読み書きできる(self, file, rank):
        board = Board()
        piece = Piece(Color.BLACK, PieceType.KING)
        board.set_piece(file, rank, piece)
        assert board.get_piece(file, rank) == piece


class TestBoardの複製:
    def test_複製は元と同じ駒配置を持つ(self):
        board = Board()
        board.set_piece(5, 5, Piece(Color.BLACK, PieceType.PAWN))
        board.set_piece(2, 8, Piece(Color.WHITE, PieceType.ROOK))
        clone = board.copy()
        assert clone.get_piece(5, 5) == Piece(Color.BLACK, PieceType.PAWN)
        assert clone.get_piece(2, 8) == Piece(Color.WHITE, PieceType.ROOK)
        assert clone.get_piece(1, 1) is None

    def test_複製を変更しても元の盤面に波及しない(self):
        board = Board()
        board.set_piece(5, 5, Piece(Color.BLACK, PieceType.PAWN))
        clone = board.copy()
        clone.set_piece(5, 5, None)
        clone.set_piece(1, 1, Piece(Color.WHITE, PieceType.GOLD))
        # 元の盤面は変わらない
        assert board.get_piece(5, 5) == Piece(Color.BLACK, PieceType.PAWN)
        assert board.get_piece(1, 1) is None

    def test_元の盤面を変更しても複製に波及しない(self):
        board = Board()
        board.set_piece(5, 5, Piece(Color.BLACK, PieceType.PAWN))
        clone = board.copy()
        board.set_piece(5, 5, Piece(Color.WHITE, PieceType.SILVER))
        # 複製は複製した時点の状態を保つ
        assert clone.get_piece(5, 5) == Piece(Color.BLACK, PieceType.PAWN)


class TestBoard盤外の座標:
    @pytest.mark.parametrize(
        ("file", "rank"),
        [(0, 5), (10, 5), (5, 0), (5, 10), (0, 0), (10, 10), (-1, 5), (5, -1)],
    )
    def test_盤外への読み書きはValueErrorになる(self, file, rank):
        board = Board()
        with pytest.raises(ValueError):
            board.get_piece(file, rank)
        with pytest.raises(ValueError):
            board.set_piece(file, rank, Piece(Color.BLACK, PieceType.PAWN))
