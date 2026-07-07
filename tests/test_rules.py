"""合法手判定の基盤のテスト（SHOGI-3a: 盤面シミュレート / 3b: 王手検出）。

board_after_move が「ある手を指した後の盤面」を、取り・成りを反映しつつ
元の盤面を壊さずに作れること、および find_king / is_attacked / is_in_check が
王手状態を正しく判定することを検証する。
自殺手除外（3c）・駒打ち・持ち駒は対象外（後続 Phase）。
"""

import pytest

from shogi.board import Board
from shogi.hand import Hand
from shogi.move import Move
from shogi.piece import Color, Piece, PieceType
from shogi.rules import (
    board_after_move,
    find_king,
    generate_legal_moves,
    is_attacked,
    is_in_check,
    position_after_move,
)
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


# ---- SHOGI-3c: 合法手生成 ----


class Test合法手の既知局面:
    def test_平手初期局面の先手合法手は30手(self):
        # 将棋の平手初期局面の合法手数は 30 手（既知の答え）
        board = board_from_sfen(_HIRATE_SFEN)
        assert len(generate_legal_moves(board, Color.BLACK)) == 30

    def test_平手初期局面の後手合法手も30手(self):
        board = board_from_sfen(_HIRATE_SFEN)
        assert len(generate_legal_moves(board, Color.WHITE)) == 30

    def test_その色の駒が無ければ合法手は空(self):
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.KING)))
        assert generate_legal_moves(board, Color.BLACK) == []


class Testピンの除外:
    def test_ピンされた駒は玉を守る筋の上でしか動けない(self):
        # 5九先手玉 — 5五先手金 — 5一後手飛 が同じ筋。金は飛にピンされている
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.KING)),
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 1, Piece(Color.WHITE, PieceType.ROOK)),
        )
        legal = generate_legal_moves(board, Color.BLACK)
        # 筋を外れる横move は自玉が飛の利きにさらされるので除外される
        assert Move(5, 5, 4, 5) not in legal
        assert Move(5, 5, 6, 5) not in legal
        # 同じ筋の上に留まる move は玉を守り続けるので合法
        assert Move(5, 5, 5, 4) in legal
        assert Move(5, 5, 5, 6) in legal


class Test王手中の合法手:
    def test_王手駒を取る手と合駒が残り王手放置は除外される(self):
        # 5五先手玉に 5一後手飛が王手。4二先手金は「飛を取る」「合駒」で解消できる
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 1, Piece(Color.WHITE, PieceType.ROOK)),
            (4, 2, Piece(Color.BLACK, PieceType.GOLD)),
        )
        legal = generate_legal_moves(board, Color.BLACK)
        assert Move(4, 2, 5, 1) in legal  # 王手駒（飛）を取って解消
        assert Move(4, 2, 5, 2) in legal  # 合駒で遮って解消
        assert Move(4, 2, 4, 1) not in legal  # 王手を解消しない手（王手放置）は除外

    def test_玉が王手の筋に留まる移動は除外される(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 1, Piece(Color.WHITE, PieceType.ROOK)),
        )
        legal = generate_legal_moves(board, Color.BLACK)
        assert Move(5, 5, 5, 6) not in legal  # 同じ筋に留まる＝まだ王手
        assert Move(5, 5, 4, 5) in legal  # 筋を外れて逃げる手は合法


class Test自殺手の除外:
    def test_玉は相手の利きへ飛び込めない(self):
        # 5五先手玉。1四後手飛が4段目を横に利かせている
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (1, 4, Piece(Color.WHITE, PieceType.ROOK)),
        )
        legal = generate_legal_moves(board, Color.BLACK)
        assert Move(5, 5, 5, 4) not in legal  # 飛の利き（4段目）へ飛び込む自殺手
        assert Move(5, 5, 5, 6) in legal  # 利きの無い方へ逃げる手は合法


class Test駒打ちの盤面反映:
    """position_after_move（SHOGI-4c）。合法性は検証せず、盤・持ち駒へ反映するだけ。"""

    def test_盤上移動はboard_after_move相当になる(self):
        board = board_with((7, 7, Piece(Color.BLACK, PieceType.PAWN)))
        hand = Hand()
        move = Move(7, 7, 7, 6)
        next_board, next_hand = position_after_move(board, hand, Color.BLACK, move)
        expected = board_after_move(board, move)
        # 全マスが board_after_move の結果と一致すること
        for rank in range(1, 10):
            for file in range(1, 10):
                assert next_board.get_piece(file, rank) == expected.get_piece(
                    file, rank
                )

    def test_駒打ちで盤面に指定駒が置かれる(self):
        board = Board()
        hand = Hand()
        hand.add(PieceType.PAWN)
        next_board, _ = position_after_move(
            board, hand, Color.BLACK, Move.drop(PieceType.PAWN, 5, 5)
        )
        assert next_board.get_piece(5, 5) == Piece(Color.BLACK, PieceType.PAWN)

    def test_後手の駒打ちは後手の駒になる(self):
        board = Board()
        hand = Hand()
        hand.add(PieceType.SILVER)
        next_board, _ = position_after_move(
            board, hand, Color.WHITE, Move.drop(PieceType.SILVER, 3, 3)
        )
        assert next_board.get_piece(3, 3) == Piece(Color.WHITE, PieceType.SILVER)

    def test_駒打ちでHandが1枚減る(self):
        board = Board()
        hand = Hand()
        hand.add(PieceType.GOLD, 2)
        _, next_hand = position_after_move(
            board, hand, Color.BLACK, Move.drop(PieceType.GOLD, 5, 5)
        )
        assert next_hand.count(PieceType.GOLD) == 1

    def test_複数駒種の代表例(self):
        # 歩・桂・飛の3種で「盤に置かれ、持ち駒が減る」ことを確認する
        for piece_type in (PieceType.PAWN, PieceType.KNIGHT, PieceType.ROOK):
            board = Board()
            hand = Hand()
            hand.add(piece_type)
            next_board, next_hand = position_after_move(
                board, hand, Color.BLACK, Move.drop(piece_type, 5, 5)
            )
            assert next_board.get_piece(5, 5) == Piece(Color.BLACK, piece_type)
            assert next_hand.count(piece_type) == 0

    def test_元のBoardとHandは変更されない(self):
        board = Board()
        hand = Hand()
        hand.add(PieceType.PAWN)
        position_after_move(
            board, hand, Color.BLACK, Move.drop(PieceType.PAWN, 5, 5)
        )
        # 元の盤面は空のまま、元の持ち駒は1枚のまま
        assert board.get_piece(5, 5) is None
        assert hand.count(PieceType.PAWN) == 1

    def test_盤上移動でも元のHandは共有されない(self):
        # 盤上移動でも戻り値の hand は複製で、後から増減しても元に影響しないこと
        board = board_with((7, 7, Piece(Color.BLACK, PieceType.PAWN)))
        hand = Hand()
        _, next_hand = position_after_move(
            board, hand, Color.BLACK, Move(7, 7, 7, 6)
        )
        next_hand.add(PieceType.PAWN)
        assert hand.count(PieceType.PAWN) == 0

    def test_持ち駒が無い駒を打つとValueError(self):
        # 合法性チェックはしないが、Hand.remove の枚数不足ガードは働く
        board = Board()
        hand = Hand()
        with pytest.raises(ValueError):
            position_after_move(
                board, hand, Color.BLACK, Move.drop(PieceType.PAWN, 5, 5)
            )
