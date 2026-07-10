"""USI 指し手表記の入出力（SHOGI-4i）のテスト。

move_from_usi（USI → Move）と move_to_usi（Move → USI）の相互変換を、
正常系・境界値・異常系で検証する。盤面上の合法性は対象外（表記の形のみ）。
"""

import pytest

from shogi.move import Move
from shogi.piece import PieceType
from shogi.usi import move_from_usi, move_to_usi

# 打てる7駒種と USI 駒打ち文字の対応（テストの網羅用にテスト側でも独立に持つ）
_DROPPABLE = [
    ("P", PieceType.PAWN),
    ("L", PieceType.LANCE),
    ("N", PieceType.KNIGHT),
    ("S", PieceType.SILVER),
    ("G", PieceType.GOLD),
    ("B", PieceType.BISHOP),
    ("R", PieceType.ROOK),
]


class TestUsiToMoveNormal:
    """USI → Move（通常移動・成り）。"""

    def test_通常移動(self):
        # "7g7f" = 7筋7段 → 7筋6段（段 g=7, f=6）
        assert move_from_usi("7g7f") == Move(7, 7, 7, 6)

    def test_成り移動(self):
        # "8h2b+" = 8筋8段 → 2筋2段で成る（段 h=8, b=2）
        assert move_from_usi("8h2b+") == Move(8, 8, 2, 2, is_promotion=True)

    def test_成りでない移動はis_promotionがFalse(self):
        assert move_from_usi("7g7f").is_promotion is False

    def test_段aからiが1から9に対応する(self):
        # 段の全字を to_rank で確認（"5a"〜"5i" → rank 1〜9）
        for index, letter in enumerate("abcdefghi", start=1):
            move = move_from_usi(f"5a5{letter}")
            assert move.to_rank == index


class TestUsiToMoveDrop:
    """USI → Move（駒打ち）。"""

    def test_歩打ち(self):
        # "P*5e" = 歩を5筋5段に打つ（段 e=5）
        assert move_from_usi("P*5e") == Move.drop(PieceType.PAWN, 5, 5)

    def test_打てる全駒種(self):
        for letter, piece_type in _DROPPABLE:
            move = move_from_usi(f"{letter}*5e")
            assert move.is_drop is True
            assert move.drop_piece_type is piece_type

    def test_駒打ちは成りを持たない(self):
        assert move_from_usi("S*5e").is_promotion is False


class TestUsiToMoveBoundary:
    """USI → Move の境界値（盤の四隅・段の両端）。"""

    def test_右上隅から右上隅(self):
        # "1a1a" = 1筋1段。表記としては有効（合法性は判定しない）
        assert move_from_usi("1a1a") == Move(1, 1, 1, 1)

    def test_左下隅(self):
        # "9i9i" = 9筋9段（file/rank の最大値）
        assert move_from_usi("9i9i") == Move(9, 9, 9, 9)

    def test_隅への駒打ち(self):
        assert move_from_usi("L*9i") == Move.drop(PieceType.LANCE, 9, 9)


class TestUsiToMoveInvalid:
    """USI → Move の異常系（不正な表記は ValueError）。"""

    @pytest.mark.parametrize(
        "usi",
        [
            "",  # 空文字列
            "7g7",  # 短すぎる
            "7g7f6",  # 長すぎる（本体5文字）
            "7g",  # 短すぎる
        ],
    )
    def test_長さが不正(self, usi):
        with pytest.raises(ValueError):
            move_from_usi(usi)

    @pytest.mark.parametrize("usi", ["0a1a", "1a0a", "7g7f".replace("7f", "af")])
    def test_不正な筋(self, usi):
        # 筋に 0 や英字が来るケース
        with pytest.raises(ValueError):
            move_from_usi(usi)

    @pytest.mark.parametrize("usi", ["7z7f", "7g7j", "7A7f"])
    def test_不正な段(self, usi):
        # 段に a〜i 以外（z, j, 大文字A）が来るケース
        with pytest.raises(ValueError):
            move_from_usi(usi)

    @pytest.mark.parametrize("usi", ["7+g7f", "+7g7f", "7g7f++"])
    def test_成り記号の位置が不正(self, usi):
        with pytest.raises(ValueError):
            move_from_usi(usi)

    @pytest.mark.parametrize("usi", ["K*5e", "X*5e", "p*5e", "+P*5e"])
    def test_駒打ちの駒種が不正(self, usi):
        # 玉・未知文字・小文字・成駒はいずれも打てない
        with pytest.raises(ValueError):
            move_from_usi(usi)

    def test_駒打ちに成り記号は不正(self):
        # 打った駒は成れないので "P*5e+" は弾く
        with pytest.raises(ValueError):
            move_from_usi("P*5e+")

    @pytest.mark.parametrize("usi", ["P*0e", "P*5z", "P*5", "PP*5e"])
    def test_駒打ちの座標や形式が不正(self, usi):
        with pytest.raises(ValueError):
            move_from_usi(usi)


class TestMoveToUsiNormal:
    """Move → USI（通常移動・成り・駒打ち）。"""

    def test_通常移動(self):
        assert move_to_usi(Move(7, 7, 7, 6)) == "7g7f"

    def test_成り移動(self):
        assert move_to_usi(Move(8, 8, 2, 2, is_promotion=True)) == "8h2b+"

    def test_歩打ち(self):
        assert move_to_usi(Move.drop(PieceType.PAWN, 5, 5)) == "P*5e"

    def test_打てる全駒種(self):
        for letter, piece_type in _DROPPABLE:
            assert move_to_usi(Move.drop(piece_type, 5, 5)) == f"{letter}*5e"

    def test_駒打ちに成り記号は付かない(self):
        assert "+" not in move_to_usi(Move.drop(PieceType.SILVER, 5, 5))


class TestMoveToUsiBoundary:
    """Move → USI の境界値。"""

    def test_四隅と段の両端(self):
        assert move_to_usi(Move(1, 1, 1, 1)) == "1a1a"
        assert move_to_usi(Move(9, 9, 9, 9)) == "9i9i"


class TestMoveToUsiInvalid:
    """Move → USI の異常系（USI で表現できない Move は ValueError）。"""

    @pytest.mark.parametrize(
        "move",
        [
            Move(0, 1, 1, 1),  # 筋が範囲外
            Move(1, 1, 1, 10),  # 段が範囲外
        ],
    )
    def test_座標が範囲外(self, move):
        with pytest.raises(ValueError):
            move_to_usi(move)

    @pytest.mark.parametrize("piece_type", [PieceType.KING, PieceType.PROMOTED_PAWN])
    def test_打てない駒種の駒打ち(self, piece_type):
        # Move.drop は駒種を検証しないため、打てない駒種の駒打ち Move を作れてしまう。
        # その Move を USI 化しようとした時点で弾く
        with pytest.raises(ValueError):
            move_to_usi(Move.drop(piece_type, 5, 5))


class TestRoundTrip:
    """相互変換の往復で元に戻ること。"""

    @pytest.mark.parametrize("usi", ["7g7f", "8h2b+", "P*5e", "1a9i", "R*5e", "2b8h+"])
    def test_usi_move_usi(self, usi):
        # USI → Move → USI で元の文字列に戻る
        assert move_to_usi(move_from_usi(usi)) == usi

    @pytest.mark.parametrize(
        "move",
        [
            Move(7, 7, 7, 6),
            Move(8, 8, 2, 2, is_promotion=True),
            Move.drop(PieceType.PAWN, 5, 5),
            Move.drop(PieceType.ROOK, 1, 9),
            Move(2, 2, 8, 8, is_promotion=True),
        ],
    )
    def test_move_usi_move(self, move):
        # Move → USI → Move で元の Move に戻る
        assert move_from_usi(move_to_usi(move)) == move
