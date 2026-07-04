"""Color / PieceType / Piece の生成テスト（SHOGI-1b）。

データ構造の定義と生成だけを検証する。駒の動き・SFEN は対象外。
"""

import dataclasses

import pytest

from shogi.piece import Color, Piece, PieceType


class TestColor:
    def test_先手と後手のちょうど2値を持つ(self):
        assert set(Color) == {Color.BLACK, Color.WHITE}

    def test_先手と後手は異なる値である(self):
        assert Color.BLACK != Color.WHITE


class TestPieceType:
    def test_基本8種と成駒6種の計14種を持つ(self):
        assert len(PieceType) == 14

    def test_成れない駒の成りは駒種として存在しない(self):
        # 金・玉に成りはない。型の段階で不正な状態を作れないことの確認
        names = {piece_type.name for piece_type in PieceType}
        assert "PROMOTED_GOLD" not in names
        assert "PROMOTED_KING" not in names


class TestPiece:
    def test_先手の歩を生成できる(self):
        piece = Piece(Color.BLACK, PieceType.PAWN)
        assert piece.color is Color.BLACK
        assert piece.piece_type is PieceType.PAWN

    @pytest.mark.parametrize("piece_type", PieceType)
    @pytest.mark.parametrize("color", Color)
    def test_全ての手番と駒種の組み合わせで生成できる(self, color, piece_type):
        # 2手番 × 14駒種 = 28通りの生成を網羅する
        piece = Piece(color, piece_type)
        assert piece.color is color
        assert piece.piece_type is piece_type

    def test_手番と駒種が同じ駒は等価である(self):
        assert Piece(Color.BLACK, PieceType.ROOK) == Piece(Color.BLACK, PieceType.ROOK)

    def test_手番が違う駒は等価でない(self):
        assert Piece(Color.BLACK, PieceType.ROOK) != Piece(Color.WHITE, PieceType.ROOK)

    def test_駒種が違う駒は等価でない(self):
        assert Piece(Color.BLACK, PieceType.ROOK) != Piece(Color.BLACK, PieceType.BISHOP)

    def test_生成後に書き換えできない(self):
        piece = Piece(Color.BLACK, PieceType.PAWN)
        with pytest.raises(dataclasses.FrozenInstanceError):
            piece.color = Color.WHITE
