"""持ち駒 Hand のテスト（SHOGI-4a）。

基本7駒種の枚数取得・加算・減算と、成駒・玉の拒否・不足時エラーを検証する。
駒打ちの生成・二歩・打ち歩詰め・着手適用は対象外（後続サブフェーズ）。
"""

import pytest

from shogi.hand import Hand
from shogi.piece import PieceType

# 持ち駒にできる基本7駒種
HAND_TYPES = [
    PieceType.PAWN,
    PieceType.LANCE,
    PieceType.KNIGHT,
    PieceType.SILVER,
    PieceType.GOLD,
    PieceType.BISHOP,
    PieceType.ROOK,
]

# 持ち駒にできない駒種（成駒6種 + 玉）
NON_HAND_TYPES = [
    PieceType.PROMOTED_PAWN,
    PieceType.PROMOTED_LANCE,
    PieceType.PROMOTED_KNIGHT,
    PieceType.PROMOTED_SILVER,
    PieceType.HORSE,
    PieceType.DRAGON,
    PieceType.KING,
]


class Test初期状態:
    @pytest.mark.parametrize("piece_type", HAND_TYPES)
    def test_生成直後は全駒種0枚(self, piece_type):
        assert Hand().count(piece_type) == 0

    def test_複数のHandは枚数を共有しない(self):
        hand1 = Hand()
        hand2 = Hand()
        hand1.add(PieceType.PAWN)
        assert hand2.count(PieceType.PAWN) == 0


class Test加算:
    def test_加算すると枚数が増える(self):
        hand = Hand()
        hand.add(PieceType.SILVER)
        assert hand.count(PieceType.SILVER) == 1

    def test_加算を繰り返すと累積する(self):
        hand = Hand()
        hand.add(PieceType.PAWN)
        hand.add(PieceType.PAWN)
        assert hand.count(PieceType.PAWN) == 2

    def test_枚数を指定してまとめて加算できる(self):
        hand = Hand()
        hand.add(PieceType.PAWN, 3)
        assert hand.count(PieceType.PAWN) == 3

    def test_ある駒種の加算は他の駒種に影響しない(self):
        hand = Hand()
        hand.add(PieceType.GOLD)
        assert hand.count(PieceType.SILVER) == 0

    def test_歩は18枚まで保持できる(self):
        # 盤上の歩は最大18枚。境界として全部持ち駒にできることを確認
        hand = Hand()
        hand.add(PieceType.PAWN, 18)
        assert hand.count(PieceType.PAWN) == 18


class Test減算:
    def test_減算すると枚数が減る(self):
        hand = Hand()
        hand.add(PieceType.ROOK, 2)
        hand.remove(PieceType.ROOK)
        assert hand.count(PieceType.ROOK) == 1

    def test_枚数を指定してまとめて減算できる(self):
        hand = Hand()
        hand.add(PieceType.PAWN, 3)
        hand.remove(PieceType.PAWN, 2)
        assert hand.count(PieceType.PAWN) == 1

    def test_ちょうど0枚まで減算できる(self):
        hand = Hand()
        hand.add(PieceType.BISHOP)
        hand.remove(PieceType.BISHOP)
        assert hand.count(PieceType.BISHOP) == 0

    def test_持っていない駒を減算するとValueError(self):
        hand = Hand()
        with pytest.raises(ValueError):
            hand.remove(PieceType.GOLD)

    def test_所持枚数を超える減算はValueError(self):
        hand = Hand()
        hand.add(PieceType.PAWN, 1)
        with pytest.raises(ValueError):
            hand.remove(PieceType.PAWN, 2)

    def test_減算に失敗しても枚数は変わらない(self):
        hand = Hand()
        hand.add(PieceType.PAWN, 1)
        with pytest.raises(ValueError):
            hand.remove(PieceType.PAWN, 2)
        assert hand.count(PieceType.PAWN) == 1  # 失敗時は減らさない


class Test駒種の制約:
    @pytest.mark.parametrize("piece_type", NON_HAND_TYPES)
    def test_成駒と玉はcountできない(self, piece_type):
        with pytest.raises(ValueError):
            Hand().count(piece_type)

    @pytest.mark.parametrize("piece_type", NON_HAND_TYPES)
    def test_成駒と玉はaddできない(self, piece_type):
        with pytest.raises(ValueError):
            Hand().add(piece_type)

    @pytest.mark.parametrize("piece_type", NON_HAND_TYPES)
    def test_成駒と玉はremoveできない(self, piece_type):
        with pytest.raises(ValueError):
            Hand().remove(piece_type)


class Test枚数の異常値:
    @pytest.mark.parametrize("count", [0, -1])
    def test_1未満の加算はValueError(self, count):
        with pytest.raises(ValueError):
            Hand().add(PieceType.PAWN, count)

    @pytest.mark.parametrize("count", [0, -1])
    def test_1未満の減算はValueError(self, count):
        with pytest.raises(ValueError):
            Hand().remove(PieceType.PAWN, count)
