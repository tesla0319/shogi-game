"""平手初期局面のテスト（SHOGI-1d）。

40枚すべての配置を、実装とは独立に書いたリテラルの期待値と突き合わせる。
手番・持ち駒・SFEN・駒の移動は対象外。
"""

from collections import Counter

from shogi.board import BOARD_SIZE
from shogi.initial_position import create_hirate_board
from shogi.piece import Color, Piece, PieceType

B = Color.BLACK
W = Color.WHITE

# 平手の全40枚の期待配置。(file, rank) -> (手番, 駒種)。
# 実装のロジックを再利用せず、盤面図から1マスずつ書き起こしている。
#
#   9  8  7  6  5  4  3  2  1   file
#   香 桂 銀 金 玉 金 銀 桂 香   rank 1 後手
#   ・ 飛 ・ ・ ・ ・ ・ 角 ・   rank 2 後手
#   歩 歩 歩 歩 歩 歩 歩 歩 歩   rank 3 後手
#   （rank 4〜6 は空き）
#   歩 歩 歩 歩 歩 歩 歩 歩 歩   rank 7 先手
#   ・ 角 ・ ・ ・ ・ ・ 飛 ・   rank 8 先手
#   香 桂 銀 金 玉 金 銀 桂 香   rank 9 先手
EXPECTED_HIRATE = {
    # rank 1（後手の奥の段）
    (9, 1): (W, PieceType.LANCE),
    (8, 1): (W, PieceType.KNIGHT),
    (7, 1): (W, PieceType.SILVER),
    (6, 1): (W, PieceType.GOLD),
    (5, 1): (W, PieceType.KING),
    (4, 1): (W, PieceType.GOLD),
    (3, 1): (W, PieceType.SILVER),
    (2, 1): (W, PieceType.KNIGHT),
    (1, 1): (W, PieceType.LANCE),
    # rank 2（後手の飛角）
    (8, 2): (W, PieceType.ROOK),
    (2, 2): (W, PieceType.BISHOP),
    # rank 3（後手の歩）
    (9, 3): (W, PieceType.PAWN),
    (8, 3): (W, PieceType.PAWN),
    (7, 3): (W, PieceType.PAWN),
    (6, 3): (W, PieceType.PAWN),
    (5, 3): (W, PieceType.PAWN),
    (4, 3): (W, PieceType.PAWN),
    (3, 3): (W, PieceType.PAWN),
    (2, 3): (W, PieceType.PAWN),
    (1, 3): (W, PieceType.PAWN),
    # rank 7（先手の歩）
    (9, 7): (B, PieceType.PAWN),
    (8, 7): (B, PieceType.PAWN),
    (7, 7): (B, PieceType.PAWN),
    (6, 7): (B, PieceType.PAWN),
    (5, 7): (B, PieceType.PAWN),
    (4, 7): (B, PieceType.PAWN),
    (3, 7): (B, PieceType.PAWN),
    (2, 7): (B, PieceType.PAWN),
    (1, 7): (B, PieceType.PAWN),
    # rank 8（先手の飛角）
    (2, 8): (B, PieceType.ROOK),
    (8, 8): (B, PieceType.BISHOP),
    # rank 9（先手の奥の段）
    (9, 9): (B, PieceType.LANCE),
    (8, 9): (B, PieceType.KNIGHT),
    (7, 9): (B, PieceType.SILVER),
    (6, 9): (B, PieceType.GOLD),
    (5, 9): (B, PieceType.KING),
    (4, 9): (B, PieceType.GOLD),
    (3, 9): (B, PieceType.SILVER),
    (2, 9): (B, PieceType.KNIGHT),
    (1, 9): (B, PieceType.LANCE),
}


def _all_squares():
    for file in range(1, BOARD_SIZE + 1):
        for rank in range(1, BOARD_SIZE + 1):
            yield file, rank


class Test平手初期局面:
    def test_期待値の駒数が40である(self):
        # テスト自身の期待値表の書き漏らしを検出する
        assert len(EXPECTED_HIRATE) == 40

    def test_全81マスが期待配置と一致する(self):
        board = create_hirate_board()
        for file, rank in _all_squares():
            actual = board.get_piece(file, rank)
            if (file, rank) in EXPECTED_HIRATE:
                color, piece_type = EXPECTED_HIRATE[(file, rank)]
                assert actual == Piece(color, piece_type), f"({file}, {rank}) の駒が違う"
            else:
                assert actual is None, f"({file}, {rank}) は空きマスのはず"

    def test_駒数の内訳が正しい(self):
        board = create_hirate_board()
        counts = Counter(
            (piece.color, piece.piece_type)
            for file, rank in _all_squares()
            if (piece := board.get_piece(file, rank)) is not None
        )
        expected_per_side = {
            PieceType.PAWN: 9,
            PieceType.LANCE: 2,
            PieceType.KNIGHT: 2,
            PieceType.SILVER: 2,
            PieceType.GOLD: 2,
            PieceType.BISHOP: 1,
            PieceType.ROOK: 1,
            PieceType.KING: 1,
        }
        for color in Color:
            for piece_type, count in expected_per_side.items():
                assert counts[(color, piece_type)] == count, f"{color} の {piece_type}"
        assert sum(counts.values()) == 40

    def test_成駒は1枚も存在しない(self):
        board = create_hirate_board()
        promoted = {
            PieceType.PROMOTED_PAWN,
            PieceType.PROMOTED_LANCE,
            PieceType.PROMOTED_KNIGHT,
            PieceType.PROMOTED_SILVER,
            PieceType.HORSE,
            PieceType.DRAGON,
        }
        for file, rank in _all_squares():
            piece = board.get_piece(file, rank)
            assert piece is None or piece.piece_type not in promoted

    def test_呼び出すたびに独立した盤面を返す(self):
        board1 = create_hirate_board()
        board2 = create_hirate_board()
        board1.set_piece(5, 5, Piece(Color.BLACK, PieceType.GOLD))
        assert board2.get_piece(5, 5) is None
