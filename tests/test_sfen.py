"""SFEN 盤面部出力のテスト（SHOGI-1e-1）。

board_to_sfen の空きマス圧縮・駒文字化・段/筋の並び順を検証する。
SFEN の読み込み・手番・持ち駒・手数は対象外。
"""

import pytest

from shogi.board import Board
from shogi.initial_position import create_hirate_board
from shogi.piece import Color, Piece, PieceType
from shogi.sfen import board_to_sfen

# 平手初期局面の盤面部。USI 仕様書等で公知の文字列をそのまま書き写している
HIRATE_BOARD_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL"


class Test代表局面:
    def test_空盤は9を9段並べた形になる(self):
        assert board_to_sfen(Board()) == "9/9/9/9/9/9/9/9/9"

    def test_平手初期局面が公知のSFENと一致する(self):
        board = create_hirate_board()
        assert board_to_sfen(board) == HIRATE_BOARD_SFEN


class Test駒文字:
    # 駒種 → (先手の文字, 後手の文字)。SFEN 規則から独立に書き起こした期待値
    LETTER_CASES = [
        (PieceType.PAWN, "P", "p"),
        (PieceType.LANCE, "L", "l"),
        (PieceType.KNIGHT, "N", "n"),
        (PieceType.SILVER, "S", "s"),
        (PieceType.GOLD, "G", "g"),
        (PieceType.BISHOP, "B", "b"),
        (PieceType.ROOK, "R", "r"),
        (PieceType.KING, "K", "k"),
        (PieceType.PROMOTED_PAWN, "+P", "+p"),
        (PieceType.PROMOTED_LANCE, "+L", "+l"),
        (PieceType.PROMOTED_KNIGHT, "+N", "+n"),
        (PieceType.PROMOTED_SILVER, "+S", "+s"),
        (PieceType.HORSE, "+B", "+b"),
        (PieceType.DRAGON, "+R", "+r"),
    ]

    @pytest.mark.parametrize(("piece_type", "black_letter", "white_letter"), LETTER_CASES)
    def test_全14駒種が先手大文字_後手小文字で出力される(
        self, piece_type, black_letter, white_letter
    ):
        # file=9, rank=1（段の先頭）に置くと、1段目が「駒文字 + 8」になる
        board = Board()
        board.set_piece(9, 1, Piece(Color.BLACK, piece_type))
        assert board_to_sfen(board).split("/")[0] == f"{black_letter}8"

        board.set_piece(9, 1, Piece(Color.WHITE, piece_type))
        assert board_to_sfen(board).split("/")[0] == f"{white_letter}8"


class Test空きマス圧縮と並び順:
    def test_段の中央の駒は左右の空きマス数で挟まれる(self):
        # 5五（file=5, rank=5）の先手歩 → 5段目は file 9〜6 の空き4 + P + file 4〜1 の空き4
        board = Board()
        board.set_piece(5, 5, Piece(Color.BLACK, PieceType.PAWN))
        assert board_to_sfen(board) == "9/9/9/9/4P4/9/9/9/9"

    def test_段の末尾が空きマスでも数字が付く(self):
        # file=9 に駒 → 段は「P8」で終わる（末尾の空き8個を省略しない）
        board = Board()
        board.set_piece(9, 5, Piece(Color.BLACK, PieceType.PAWN))
        assert board_to_sfen(board).split("/")[4] == "P8"

    def test_段の先頭が空きマスなら数字から始まる(self):
        # file=1 に駒 → 段は「8p」（file 9〜2 の空き8個が先に来る）
        board = Board()
        board.set_piece(1, 5, Piece(Color.WHITE, PieceType.PAWN))
        assert board_to_sfen(board).split("/")[4] == "8p"

    def test_駒と駒の間の空きマスが正しく数えられる(self):
        # file=9 と file=7 に駒 → 「P1P6」（間の空き1個・後ろの空き6個）
        board = Board()
        board.set_piece(9, 5, Piece(Color.BLACK, PieceType.PAWN))
        board.set_piece(7, 5, Piece(Color.BLACK, PieceType.PAWN))
        assert board_to_sfen(board).split("/")[4] == "P1P6"

    def test_隣接する駒の間に数字は入らない(self):
        board = Board()
        board.set_piece(9, 5, Piece(Color.BLACK, PieceType.PAWN))
        board.set_piece(8, 5, Piece(Color.WHITE, PieceType.PAWN))
        assert board_to_sfen(board).split("/")[4] == "Pp7"

    def test_段は1段目から9段目の順に並ぶ(self):
        # rank=1 と rank=9 に別の駒を置き、出力の1行目と9行目に対応することを確認
        board = Board()
        board.set_piece(9, 1, Piece(Color.WHITE, PieceType.KING))
        board.set_piece(9, 9, Piece(Color.BLACK, PieceType.KING))
        rows = board_to_sfen(board).split("/")
        assert rows[0] == "k8"
        assert rows[8] == "K8"
