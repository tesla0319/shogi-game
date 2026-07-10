"""AI の手選択（SHOGI-5a）のテスト。

choose_move が合法手からランダムに1手を選ぶこと、渡した rng による再現性、
空リストでの例外、入力を変更しないことを検証する。合法手生成・局面評価・終局判定は
このフェーズの対象外なので参照しない（Move だけを使う）。
"""

import random

import pytest

from shogi.ai import choose_move
from shogi.move import Move
from shogi.piece import PieceType

# 検証用の合法手サンプル（盤面には依存しない。Move の形だけを使う）
_MOVES = [
    Move(7, 7, 7, 6),
    Move(2, 7, 2, 6),
    Move(8, 8, 2, 2, is_promotion=True),
    Move.drop(PieceType.PAWN, 5, 5),
    Move.drop(PieceType.SILVER, 3, 4),
]


class TestSingleMove:
    def test_合法手が1件ならその手を返す(self):
        only = [Move(7, 7, 7, 6)]
        assert choose_move(only, random.Random(0)) == Move(7, 7, 7, 6)


class TestMultipleMoves:
    def test_返す手は入力の合法手に含まれる(self):
        rng = random.Random(0)
        # 何度引いても必ず入力集合の要素（どの抽選結果でも成り立つ不変条件）
        for _ in range(50):
            assert choose_move(_MOVES, rng) in _MOVES


class TestReproducibility:
    def test_同じシードなら同じ手を返す(self):
        # 別インスタンスでも同じシードなら結果が一致する（再現性）
        first = choose_move(_MOVES, random.Random(42))
        second = choose_move(_MOVES, random.Random(42))
        assert first == second

    def test_同じrngの連続呼び出し列も再現する(self):
        rng_a = random.Random(7)
        rng_b = random.Random(7)
        assert [choose_move(_MOVES, rng_a) for _ in range(10)] == [
            choose_move(_MOVES, rng_b) for _ in range(10)
        ]

    def test_グローバル乱数の状態に依存しない(self):
        # グローバル random をどう変えても、注入した rng の結果は変わらない
        random.seed(12345)
        expected = choose_move(_MOVES, random.Random(0))
        random.seed(99999)
        [random.random() for _ in range(10)]  # グローバル状態を動かす
        assert choose_move(_MOVES, random.Random(0)) == expected


class TestEmpty:
    def test_空の合法手はValueError(self):
        with pytest.raises(ValueError):
            choose_move([], random.Random(0))


class TestInputNotMutated:
    def test_入力リストを変更しない(self):
        moves = list(_MOVES)
        before = list(moves)
        choose_move(moves, random.Random(0))
        assert moves == before  # 要素も順序も変わらない
