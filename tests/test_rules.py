"""合法手判定の基盤のテスト（SHOGI-3a: 盤面シミュレート / 3b: 王手検出）。

board_after_move が「ある手を指した後の盤面」を、取り・成りを反映しつつ
元の盤面を壊さずに作れること、および find_king / is_attacked / is_in_check が
王手状態を正しく判定することを検証する。
自殺手除外（3c）・駒打ち・持ち駒は対象外（後続 Phase）。
"""

import pytest

from shogi.board import Board
from shogi.move import Move
from shogi.piece import Color, Piece, PieceType
from shogi.rules import board_after_move, find_king, is_attacked, is_in_check
from shogi.sfen import board_from_sfen


def board_with(*placements: tuple[int, int, Piece]) -> Board:
    """指定した駒だけを置いた盤面を作るテスト用ヘルパー。"""
    board = Board()
    for file, rank, piece in placements:
        board.set_piece(file, rank, piece)
    return board


class Test取りも成りもない移動:
    def test_駒が移動元から移動先へ動く(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        result = board_after_move(board, Move(5, 5, 5, 4))
        assert result.get_piece(5, 5) is None
        assert result.get_piece(5, 4) == Piece(Color.BLACK, PieceType.GOLD)


class Test取りのある移動:
    def test_移動先の相手駒が取り除かれ自駒に置き換わる(self):
        # 先手金(5五) が 後手歩(5四) を取る
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 5, 5, 4))
        assert result.get_piece(5, 5) is None
        assert result.get_piece(5, 4) == Piece(Color.BLACK, PieceType.GOLD)

    def test_取った駒は持ち駒に加えない(self):
        # 持ち駒は SHOGI-4 の責務。board_after_move は盤から除去するだけ。
        # 盤上のどこにも取った後手歩が残っていないことで確認する
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 2, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 5, 5, 2))
        white_pawns = [
            (f, r)
            for f in range(1, 10)
            for r in range(1, 10)
            if result.get_piece(f, r) == Piece(Color.WHITE, PieceType.PAWN)
        ]
        assert white_pawns == []


class Test成りのある移動:
    # 成れる6駒種それぞれについて、is_promotion=True で駒種が成駒に変わること
    @pytest.mark.parametrize(
        ("before", "after"),
        [
            (PieceType.PAWN, PieceType.PROMOTED_PAWN),
            (PieceType.LANCE, PieceType.PROMOTED_LANCE),
            (PieceType.KNIGHT, PieceType.PROMOTED_KNIGHT),
            (PieceType.SILVER, PieceType.PROMOTED_SILVER),
            (PieceType.BISHOP, PieceType.HORSE),
            (PieceType.ROOK, PieceType.DRAGON),
        ],
    )
    def test_成る手で駒種が成駒に変わる(self, before, after):
        # 先手が敵陣（3段目→2段目）へ動いて成る
        board = board_with((5, 3, Piece(Color.BLACK, before)))
        result = board_after_move(board, Move(5, 3, 5, 2, is_promotion=True))
        assert result.get_piece(5, 3) is None
        assert result.get_piece(5, 2) == Piece(Color.BLACK, after)

    def test_成りと取りが同時に起きる(self):
        # 先手角(5三) が 後手歩(4二) を取りながら馬に成る
        board = board_with(
            (5, 3, Piece(Color.BLACK, PieceType.BISHOP)),
            (4, 2, Piece(Color.WHITE, PieceType.PAWN)),
        )
        result = board_after_move(board, Move(5, 3, 4, 2, is_promotion=True))
        assert result.get_piece(4, 2) == Piece(Color.BLACK, PieceType.HORSE)

    def test_成らない手では駒種が変わらない(self):
        board = board_with((5, 3, Piece(Color.BLACK, PieceType.SILVER)))
        result = board_after_move(board, Move(5, 3, 5, 2))  # is_promotion 既定 False
        assert result.get_piece(5, 2) == Piece(Color.BLACK, PieceType.SILVER)


class Test元の盤面を壊さない:
    def test_指した後も元の盤面は変わらない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        board_after_move(board, Move(5, 5, 5, 4))
        # 元盤面はそのまま（シミュレートは複製上で行う）
        assert board.get_piece(5, 5) == Piece(Color.BLACK, PieceType.GOLD)
        assert board.get_piece(5, 4) == Piece(Color.WHITE, PieceType.PAWN)


class Test異常系:
    def test_移動元が空きマスならValueError(self):
        board = Board()
        with pytest.raises(ValueError):
            board_after_move(board, Move(5, 5, 5, 4))

    def test_成れない駒種の成り指定はValueError(self):
        # 金は成れない。movegen は生成しないが、防御的に弾く
        board = board_with((5, 3, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            board_after_move(board, Move(5, 3, 5, 2, is_promotion=True))


# ---- SHOGI-3b: 王手検出 ----

# 盤面部のみの SFEN（平手初期局面）。どちらの玉も王手されていない既知局面
_HIRATE_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL"


class Test玉の位置探索:
    def test_先手玉と後手玉をそれぞれ見つける(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.KING)),
            (5, 1, Piece(Color.WHITE, PieceType.KING)),
        )
        assert find_king(board, Color.BLACK) == (5, 9)
        assert find_king(board, Color.WHITE) == (5, 1)

    def test_玉が盤上に無ければNone(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        assert find_king(board, Color.BLACK) is None


class Testマスの攻撃判定:
    def test_走り駒の利きが通っていれば攻撃されている(self):
        # 5九の先手飛 → 5一まで縦に利きが通る（間に駒なし）
        board = board_with((5, 9, Piece(Color.BLACK, PieceType.ROOK)))
        assert is_attacked(board, 5, 1, Color.BLACK) is True

    def test_間に駒があれば遮られて攻撃されていない(self):
        # 5五に駒があると 5九の飛の利きは 5一まで届かない
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert is_attacked(board, 5, 1, Color.BLACK) is False

    def test_利きの無いマスは攻撃されていない(self):
        board = board_with((5, 9, Piece(Color.BLACK, PieceType.ROOK)))
        assert is_attacked(board, 4, 1, Color.BLACK) is False  # 横にずれたマス

    def test_by_colorの取り違え_自駒は攻撃者に数えない(self):
        # 先手飛の利きが通るマスでも「後手が攻撃しているか」は False
        board = board_with((5, 9, Piece(Color.BLACK, PieceType.ROOK)))
        assert is_attacked(board, 5, 1, Color.WHITE) is False


class Test王手検出:
    def test_飛車の遠隔王手(self):
        # 5一の後手玉に 5九の先手飛が王手（縦に利きが通る）
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.KING)),
            (5, 9, Piece(Color.BLACK, PieceType.ROOK)),
        )
        assert is_in_check(board, Color.WHITE) is True

    def test_間に駒があれば飛車の王手は成立しない(self):
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.KING)),
            (5, 9, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),  # 合駒
        )
        assert is_in_check(board, Color.WHITE) is False

    def test_角の遠隔王手(self):
        # 5五の先手玉に 1一の後手角が斜めに王手
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (1, 1, Piece(Color.WHITE, PieceType.BISHOP)),
        )
        assert is_in_check(board, Color.BLACK) is True

    def test_間に駒があれば角の王手は成立しない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (1, 1, Piece(Color.WHITE, PieceType.BISHOP)),
            (3, 3, Piece(Color.BLACK, PieceType.PAWN)),  # 合駒
        )
        assert is_in_check(board, Color.BLACK) is False

    def test_香車の王手(self):
        # 5一の後手玉に 5五の先手香が前方向の利きで王手
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.KING)),
            (5, 5, Piece(Color.BLACK, PieceType.LANCE)),
        )
        assert is_in_check(board, Color.WHITE) is True

    def test_桂馬の王手(self):
        # 5五の先手玉に 4三の後手桂が跳ねて王手（間の駒を跳び越える）
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (4, 3, Piece(Color.WHITE, PieceType.KNIGHT)),
            (4, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 桂は跳び越えるので無関係
        )
        assert is_in_check(board, Color.BLACK) is True

    def test_両王手も王手として検出する(self):
        # 5五の先手玉に 後手飛（縦）と 後手角（斜め）の2枚から同時に王手
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 1, Piece(Color.WHITE, PieceType.ROOK)),
            (1, 1, Piece(Color.WHITE, PieceType.BISHOP)),
        )
        assert is_in_check(board, Color.BLACK) is True

    def test_自駒の利きでは王手にならない(self):
        # 先手玉と先手飛が同じ筋にあっても王手ではない
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 1, Piece(Color.BLACK, PieceType.ROOK)),
        )
        assert is_in_check(board, Color.BLACK) is False

    def test_利きが届かなければ王手でない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (1, 9, Piece(Color.WHITE, PieceType.GOLD)),  # 遠くの金は届かない
        )
        assert is_in_check(board, Color.BLACK) is False

    def test_玉が盤上に無ければ王手でない(self):
        board = board_with((5, 1, Piece(Color.WHITE, PieceType.ROOK)))
        assert is_in_check(board, Color.BLACK) is False

    def test_平手初期局面はどちらも王手でない(self):
        board = board_from_sfen(_HIRATE_SFEN)
        assert is_in_check(board, Color.BLACK) is False
        assert is_in_check(board, Color.WHITE) is False
