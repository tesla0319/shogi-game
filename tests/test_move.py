"""Move（指し手）のテスト。

通常移動 Move が従来どおり生成できること、および駒打ち Move の生成・判別・
駒種保持を検証する。合法性（二歩・打ち歩詰め等）はこの Phase の対象外。
"""

from shogi.move import Move
from shogi.piece import PieceType


class TestNormalMove:
    """通常移動 Move が既存仕様のまま壊れていないこと。"""

    def test_positional_construction(self):
        # 既存コードと同じ位置引数での生成が維持されていること
        move = Move(7, 7, 7, 6)
        assert move.from_file == 7
        assert move.from_rank == 7
        assert move.to_file == 7
        assert move.to_rank == 6

    def test_is_promotion_defaults_false(self):
        assert Move(7, 7, 7, 6).is_promotion is False

    def test_promotion_move(self):
        move = Move(8, 8, 2, 2, is_promotion=True)
        assert move.is_promotion is True

    def test_normal_move_is_not_drop(self):
        assert Move(7, 7, 7, 6).is_drop is False

    def test_normal_move_drop_piece_type_is_none(self):
        assert Move(7, 7, 7, 6).drop_piece_type is None

    def test_equality_unaffected(self):
        assert Move(7, 7, 7, 6) == Move(7, 7, 7, 6)
        assert Move(7, 7, 7, 6) != Move(7, 7, 7, 6, is_promotion=True)


class TestDropMove:
    """駒打ち Move の生成・判別・駒種保持。"""

    def test_drop_is_drop_true(self):
        move = Move.drop(PieceType.PAWN, 5, 5)
        assert move.is_drop is True

    def test_drop_holds_piece_type(self):
        move = Move.drop(PieceType.SILVER, 5, 5)
        assert move.drop_piece_type is PieceType.SILVER

    def test_drop_holds_destination(self):
        move = Move.drop(PieceType.KNIGHT, 3, 4)
        assert move.to_file == 3
        assert move.to_rank == 4

    def test_drop_is_not_promotion(self):
        # 駒打ちは成りを伴わない
        assert Move.drop(PieceType.PAWN, 5, 5).is_promotion is False

    def test_drop_moves_equal_for_same_args(self):
        assert Move.drop(PieceType.PAWN, 5, 5) == Move.drop(PieceType.PAWN, 5, 5)

    def test_drop_moves_differ_by_piece_type(self):
        assert Move.drop(PieceType.PAWN, 5, 5) != Move.drop(PieceType.LANCE, 5, 5)

    def test_drop_moves_differ_by_destination(self):
        assert Move.drop(PieceType.PAWN, 5, 5) != Move.drop(PieceType.PAWN, 5, 6)

    def test_all_droppable_piece_types(self):
        # 打てる駒種すべてで駒種が正しく保持されること
        droppable = [
            PieceType.PAWN,
            PieceType.LANCE,
            PieceType.KNIGHT,
            PieceType.SILVER,
            PieceType.GOLD,
            PieceType.BISHOP,
            PieceType.ROOK,
        ]
        for piece_type in droppable:
            move = Move.drop(piece_type, 5, 5)
            assert move.is_drop is True
            assert move.drop_piece_type is piece_type
