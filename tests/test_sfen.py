"""SFEN 盤面部の出力（SHOGI-1e-1）と読み込み（SHOGI-1e-2）のテスト。

手番・持ち駒・手数を含む完全な SFEN は対象外。
"""

import pytest

from shogi.board import BOARD_SIZE, Board
from shogi.initial_position import create_hirate_board
from shogi.piece import Color, Piece, PieceType
from shogi.sfen import board_from_sfen, board_to_sfen


def assert_same_board(actual: Board, expected: Board) -> None:
    """2つの盤面の全81マスが一致することを検証する。"""
    for file in range(1, BOARD_SIZE + 1):
        for rank in range(1, BOARD_SIZE + 1):
            assert actual.get_piece(file, rank) == expected.get_piece(file, rank), (
                f"({file}, {rank}) が一致しない"
            )

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


class Test読み込み正常系:
    def test_空盤を復元できる(self):
        assert_same_board(board_from_sfen("9/9/9/9/9/9/9/9/9"), Board())

    def test_平手初期局面を復元できる(self):
        # 復元結果が「手動構築（create_hirate_board）した盤面」と全マス一致すること
        board = board_from_sfen(HIRATE_BOARD_SFEN)
        assert_same_board(board, create_hirate_board())

    @pytest.mark.parametrize(
        ("piece_type", "black_letter", "white_letter"), Test駒文字.LETTER_CASES
    )
    def test_全14駒種を先手後手とも復元できる(self, piece_type, black_letter, white_letter):
        board = board_from_sfen(f"{black_letter}8/9/9/9/9/9/9/9/9")
        assert board.get_piece(9, 1) == Piece(Color.BLACK, piece_type)

        board = board_from_sfen(f"{white_letter}8/9/9/9/9/9/9/9/9")
        assert board.get_piece(9, 1) == Piece(Color.WHITE, piece_type)

    def test_段の途中の駒が正しい筋に置かれる(self):
        # "4P4" → file=5 に先手歩。筋の数え方（9から左→右）の取り違え検出
        board = board_from_sfen("9/9/9/9/4P4/9/9/9/9")
        assert board.get_piece(5, 5) == Piece(Color.BLACK, PieceType.PAWN)
        assert board.get_piece(4, 5) is None
        assert board.get_piece(6, 5) is None

    @pytest.mark.parametrize(
        "sfen",
        [
            "9/9/9/9/9/9/9/9/9",
            HIRATE_BOARD_SFEN,
            "k8/1+P7/9/9/4+b4/9/9/7r1/K8",  # 成駒と後手駒が混ざった局面
        ],
    )
    def test_読み込んで書き出すと元の文字列に戻る(self, sfen):
        assert board_to_sfen(board_from_sfen(sfen)) == sfen


class Test読み込み異常系:
    @pytest.mark.parametrize(
        "sfen",
        [
            "",  # 空文字列
            "9/9/9/9/9/9/9/9",  # 段数不足（8段）
            "9/9/9/9/9/9/9/9/9/9",  # 段数過多（10段）
            "9//9/9/9/9/9/9/9",  # 空の段（段数は9だがマス数0）
        ],
    )
    def test_段数や段の形が不正ならValueError(self, sfen):
        with pytest.raises(ValueError):
            board_from_sfen(sfen)

    @pytest.mark.parametrize(
        "bad_row",
        [
            "8",  # マス数不足（8マス）
            "PPPPPPPP",  # マス数不足（駒8枚）
            "PPPPPPPPPP",  # マス数過多（駒10枚）
            "5P4",  # マス数過多（5+1+4=10）
            "55",  # マス数過多（数字の連続で5+5=10）
            "9P",  # 空き9マスの後に駒（10マス目）
        ],
    )
    def test_1段のマス数が9でなければValueError(self, bad_row):
        with pytest.raises(ValueError):
            board_from_sfen(f"{bad_row}/9/9/9/9/9/9/9/9")

    @pytest.mark.parametrize(
        "bad_row",
        [
            "X8",  # 駒として存在しない文字
            "08",  # 空きマス数に 0 は使えない
            "５8",  # 全角数字
            "+G8",  # 金は成れない
            "+K8",  # 玉は成れない
            "+58",  # "+" の後が駒文字でない
            "8+",  # 段末の孤立した "+"
            "P 7P",  # 空白文字
        ],
    )
    def test_不正な文字が含まれていればValueError(self, bad_row):
        with pytest.raises(ValueError):
            board_from_sfen(f"{bad_row}/9/9/9/9/9/9/9/9")
