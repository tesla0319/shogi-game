"""局面のテキスト表示（SHOGI-4j）のテスト。

position_to_text が盤面・両者持ち駒・手番を可読な文字列に変換すること、および
「同じ局面なら常に同じ文字列」（決定的・副作用なし）を検証する。
"""

from shogi.board import Board
from shogi.display import position_to_text
from shogi.hand import Hand
from shogi.initial_position import create_hirate_board
from shogi.piece import Color, Piece, PieceType
from shogi.sfen import board_from_sfen

# 平手初期局面の期待表示。盤の向きは先手視点固定（後手＝小文字が上、先手＝大文字が下）。
# 段ラベル a〜i は右端、筋ヘッダ 9〜1 は上端。空マスは "."。
_HIRATE_TEXT = (
    "後手持ち駒: なし\n"
    " 9 8 7 6 5 4 3 2 1\n"
    " l n s g k g s n l a\n"
    " . r . . . . . b . b\n"
    " p p p p p p p p p c\n"
    " . . . . . . . . . d\n"
    " . . . . . . . . . e\n"
    " . . . . . . . . . f\n"
    " P P P P P P P P P g\n"
    " . B . . . . . R . h\n"
    " L N S G K G S N L i\n"
    "先手持ち駒: なし\n"
    "手番: 先手"
)


class TestHiratePosition:
    """平手初期局面の全体スナップショット（表示形式を固定する）。"""

    def test_平手初期局面の表示(self):
        board = create_hirate_board()
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert text == _HIRATE_TEXT


class TestSideToMove:
    """手番の表示。"""

    def test_先手番(self):
        board = create_hirate_board()
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert text.endswith("手番: 先手")

    def test_後手番(self):
        board = create_hirate_board()
        text = position_to_text(board, Hand(), Hand(), Color.WHITE)
        assert text.endswith("手番: 後手")

    def test_盤と持ち駒は手番で変わらない(self):
        # 手番だけが違う2局面は、最後の「手番:」行以外が一致する
        board = create_hirate_board()
        black = position_to_text(board, Hand(), Hand(), Color.BLACK)
        white = position_to_text(board, Hand(), Hand(), Color.WHITE)
        assert black.rsplit("\n", 1)[0] == white.rsplit("\n", 1)[0]


class TestEmptyBoard:
    """空盤（駒が1枚もない）の境界。"""

    def test_空盤は全マスがドット(self):
        board = Board()
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        # 盤の各行（段ラベル a〜i を含む行）はすべて空マスのみ
        assert " . . . . . . . . . a" in text
        assert " . . . . . . . . . i" in text
        # 駒文字は現れない（王も含め、盤上に駒が無い）
        assert "K" not in text and "k" not in text

    def test_空盤の持ち駒はなし(self):
        board = Board()
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert "先手持ち駒: なし" in text
        assert "後手持ち駒: なし" in text


class TestPieceRendering:
    """先手/後手・成駒の駒文字の描き分け。"""

    def test_先手は大文字_後手は小文字(self):
        # 5五に先手飛、5三に後手飛だけを置く
        board = board_from_sfen("9/9/4r4/9/4R4/9/9/9/9")
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert " R " in text  # 先手飛（大文字）
        assert " r " in text  # 後手飛（小文字）

    def test_成駒は先頭にプラス(self):
        # 5五に先手と金（+P）、5三に後手馬（+B → +b）
        board = board_from_sfen("9/9/4+b4/9/4+P4/9/9/9/9")
        text = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert "+P" in text  # 先手と金
        assert "+b" in text  # 後手馬


class TestHandRendering:
    """持ち駒の表示（順序・枚数・空）。"""

    def test_1枚は枚数を付けない(self):
        hand = Hand()
        hand.add(PieceType.ROOK)
        text = position_to_text(Board(), hand, Hand(), Color.BLACK)
        assert "先手持ち駒: R" in text

    def test_2枚以上は枚数を付ける(self):
        hand = Hand()
        hand.add(PieceType.PAWN, 3)
        text = position_to_text(Board(), hand, Hand(), Color.BLACK)
        assert "先手持ち駒: P3" in text

    def test_持ち駒は飛角金銀桂香歩の順(self):
        hand = Hand()
        # わざと逆順に加えても、表示は _HAND_ORDER（飛→歩）の順になる
        hand.add(PieceType.PAWN)
        hand.add(PieceType.LANCE)
        hand.add(PieceType.ROOK)
        text = position_to_text(Board(), hand, Hand(), Color.BLACK)
        assert "先手持ち駒: R L P" in text

    def test_先手と後手の持ち駒を別々に表示(self):
        black = Hand()
        black.add(PieceType.GOLD)
        white = Hand()
        white.add(PieceType.SILVER, 2)
        text = position_to_text(Board(), black, white, Color.BLACK)
        assert "先手持ち駒: G" in text
        assert "後手持ち駒: S2" in text


class TestDeterministicAndPure:
    """決定性（同じ局面は同じ文字列）と副作用のなさ。"""

    def test_同じ局面は常に同じ文字列(self):
        board = create_hirate_board()
        first = position_to_text(board, Hand(), Hand(), Color.BLACK)
        second = position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert first == second

    def test_盤を変更しない(self):
        # 表示後も盤面が元のまま（SFEN が変わらない）＝副作用がない
        board = create_hirate_board()
        from shogi.sfen import board_to_sfen

        before = board_to_sfen(board)
        position_to_text(board, Hand(), Hand(), Color.BLACK)
        assert board_to_sfen(board) == before
