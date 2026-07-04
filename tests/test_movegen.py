"""疑似合法手生成のテスト（SHOGI-2a: 歩、2b: 香車、2c: 桂馬、2d: 銀将、2e: 金将）。

疑似合法手の範囲（盤外・味方駒マスの除外、走り駒の停止位置）のみを検証する。
二歩・王手放置などの反則除外（SHOGI-3）、成り、駒打ちは対象外。
"""

import pytest

from shogi.board import Board
from shogi.initial_position import create_hirate_board
from shogi.move import Move
from shogi.movegen import (
    generate_gold_moves,
    generate_knight_moves,
    generate_lance_moves,
    generate_pawn_moves,
    generate_silver_moves,
)
from shogi.piece import Color, Piece, PieceType


def board_with(*placements: tuple[int, int, Piece]) -> Board:
    """指定した駒だけを置いた盤面を作るテスト用ヘルパー。"""
    board = Board()
    for file, rank, piece in placements:
        board.set_piece(file, rank, piece)
    return board


class Test歩の進む方向:
    def test_先手の歩は奥へ1マス進む(self):
        # 5五の先手歩 → 5四へ（rank が 1 減る）
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 4)]

    def test_後手の歩は手前へ1マス進む(self):
        # 5五の後手歩 → 5六へ（rank が 1 増える）
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 6)]

    @pytest.mark.parametrize("file", [1, 9])
    def test_端の筋でも同じように進める(self, file):
        board = board_with((file, 5, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, file, 5) == [Move(file, 5, file, 4)]


class Test盤の端:
    def test_最奥の段の先手歩は動けない(self):
        # rank=1 の先手歩の移動先は盤外。実局面では行き所のない駒（SHOGI-3 の反則）
        # だが、疑似合法手の層では「候補なし」として空リストを返す
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 1) == []

    def test_最奥の段の後手歩は動けない(self):
        board = board_with((5, 9, Piece(Color.WHITE, PieceType.PAWN)))
        assert generate_pawn_moves(board, 5, 9) == []


class Test移動先の駒:
    def test_移動先に味方駒があると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.BLACK, PieceType.GOLD)),
        )
        assert generate_pawn_moves(board, 5, 5) == []

    def test_移動先に相手駒があれば進める_取る手になる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.WHITE, PieceType.GOLD)),
        )
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 4)]

    def test_後手の歩も味方駒に塞がれると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
            (5, 6, Piece(Color.WHITE, PieceType.SILVER)),
        )
        assert generate_pawn_moves(board, 5, 5) == []


class Test平手初期局面:
    @pytest.mark.parametrize("file", range(1, 10))
    def test_先手の歩9枚はそれぞれ1マス進める(self, file):
        board = create_hirate_board()
        assert generate_pawn_moves(board, file, 7) == [Move(file, 7, file, 6)]

    @pytest.mark.parametrize("file", range(1, 10))
    def test_後手の歩9枚はそれぞれ1マス進める(self, file):
        board = create_hirate_board()
        assert generate_pawn_moves(board, file, 3) == [Move(file, 3, file, 4)]


class Test異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_pawn_moves(Board(), 5, 5)

    def test_歩以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            generate_pawn_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_pawn_moves(Board(), 0, 5)


class Test香車の走り:
    def test_先手の香は前方向へ盤の端まで走る(self):
        # 空盤の5九の先手香 → 5八〜5一の8マス（近い順）
        board = board_with((5, 9, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, to_rank) for to_rank in range(8, 0, -1)
        ]

    def test_後手の香は後方向へ盤の端まで走る(self):
        # 空盤の5一の後手香 → 5二〜5九の8マス（近い順）
        board = board_with((5, 1, Piece(Color.WHITE, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 1) == [
            Move(5, 1, 5, to_rank) for to_rank in range(2, 10)
        ]

    def test_盤の途中からは残りの段だけ走る(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 5) == [
            Move(5, 5, 5, 4),
            Move(5, 5, 5, 3),
            Move(5, 5, 5, 2),
            Move(5, 5, 5, 1),
        ]

    def test_最奥の段の香は動けない(self):
        # 実局面では行き所のない駒（SHOGI-3 の反則）だが、ここでは候補なし
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.LANCE)))
        assert generate_lance_moves(board, 5, 1) == []


class Test香車の停止:
    def test_味方駒の手前で停止しそのマスは含めない(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, 8),
            Move(5, 9, 5, 7),
            Move(5, 9, 5, 6),
        ]

    def test_相手駒のマスで停止しそのマスは含める(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 9) == [
            Move(5, 9, 5, 8),
            Move(5, 9, 5, 7),
            Move(5, 9, 5, 6),
            Move(5, 9, 5, 5),  # 相手駒を取る手
        ]

    def test_相手駒の先へは飛び越えられない(self):
        # 相手駒で停止した後ろにある空きマス（5四〜5一）が含まれないこと
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
        )
        moves = generate_lance_moves(board, 5, 9)
        assert all(move.to_rank >= 5 for move in moves)

    def test_隣が味方駒なら候補なし(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 8, Piece(Color.BLACK, PieceType.GOLD)),
        )
        assert generate_lance_moves(board, 5, 9) == []

    def test_隣が相手駒ならその1マスだけ(self):
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.LANCE)),
            (5, 8, Piece(Color.WHITE, PieceType.GOLD)),
        )
        assert generate_lance_moves(board, 5, 9) == [Move(5, 9, 5, 8)]

    def test_後手の香も味方駒の手前で停止する(self):
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.LANCE)),
            (5, 4, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 1) == [
            Move(5, 1, 5, 2),
            Move(5, 1, 5, 3),
        ]


class Test香車の平手初期局面:
    @pytest.mark.parametrize("file", [1, 9])
    def test_先手の香は自陣の歩の手前まで動ける(self, file):
        # 九段目の香は七段目の味方歩に塞がれ、八段目の1マスのみ
        board = create_hirate_board()
        assert generate_lance_moves(board, file, 9) == [Move(file, 9, file, 8)]

    @pytest.mark.parametrize("file", [1, 9])
    def test_後手の香も自陣の歩の手前まで動ける(self, file):
        board = create_hirate_board()
        assert generate_lance_moves(board, file, 1) == [Move(file, 1, file, 2)]


class Test香車の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_lance_moves(Board(), 5, 5)

    def test_香車以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.PAWN)))
        with pytest.raises(ValueError):
            generate_lance_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_lance_moves(Board(), 5, 10)


class Test桂馬の跳び先:
    def test_先手の桂は前2段の左右へ跳ぶ(self):
        # 5五の先手桂 → 4三と6三（file の小さい側から）
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 5, 5) == [
            Move(5, 5, 4, 3),
            Move(5, 5, 6, 3),
        ]

    def test_後手の桂は後2段の左右へ跳ぶ(self):
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 5, 5) == [
            Move(5, 5, 4, 7),
            Move(5, 5, 6, 7),
        ]

    def test_途中に駒があっても飛び越えられる(self):
        # 跳び先の間にある3マスを味方駒で埋めても、跳び先2箇所は変わらない
        board = board_with(
            (5, 9, Piece(Color.BLACK, PieceType.KNIGHT)),
            (4, 8, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 8, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 8, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_knight_moves(board, 5, 9) == [
            Move(5, 9, 4, 7),
            Move(5, 9, 6, 7),
        ]


class Test桂馬の盤外:
    def test_1筋の桂は左側だけに跳ぶ(self):
        board = board_with((1, 5, Piece(Color.BLACK, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 1, 5) == [Move(1, 5, 2, 3)]

    def test_9筋の桂は右側だけに跳ぶ(self):
        board = board_with((9, 5, Piece(Color.BLACK, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 9, 5) == [Move(9, 5, 8, 3)]

    @pytest.mark.parametrize("rank", [1, 2])
    def test_奥から2段以内の先手桂は動けない(self, rank):
        # 跳び先が盤外。実局面では行き所のない駒（SHOGI-3 の反則）だが候補なしを返す
        board = board_with((5, rank, Piece(Color.BLACK, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 5, rank) == []

    @pytest.mark.parametrize("rank", [8, 9])
    def test_奥から2段以内の後手桂は動けない(self, rank):
        board = board_with((5, rank, Piece(Color.WHITE, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 5, rank) == []

    def test_三段目の先手桂は一段目へ跳べる(self):
        # 盤外判定の境界（rank 2→NG, 3→OK）
        board = board_with((5, 3, Piece(Color.BLACK, PieceType.KNIGHT)))
        assert generate_knight_moves(board, 5, 3) == [
            Move(5, 3, 4, 1),
            Move(5, 3, 6, 1),
        ]


class Test桂馬の跳び先の駒:
    def test_片方が味方駒ならもう片方だけ(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KNIGHT)),
            (4, 3, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_knight_moves(board, 5, 5) == [Move(5, 5, 6, 3)]

    def test_両方が味方駒なら候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KNIGHT)),
            (4, 3, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 3, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_knight_moves(board, 5, 5) == []

    def test_相手駒のマスへは跳べる_取る手になる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KNIGHT)),
            (4, 3, Piece(Color.WHITE, PieceType.PAWN)),
            (6, 3, Piece(Color.WHITE, PieceType.GOLD)),
        )
        assert generate_knight_moves(board, 5, 5) == [
            Move(5, 5, 4, 3),
            Move(5, 5, 6, 3),
        ]


class Test桂馬の平手初期局面:
    @pytest.mark.parametrize(("file", "rank", "color"), [
        (2, 9, Color.BLACK),
        (8, 9, Color.BLACK),
        (2, 1, Color.WHITE),
        (8, 1, Color.WHITE),
    ])
    def test_初期配置の桂は自陣の歩に塞がれて動けない(self, file, rank, color):
        # 跳び先（三段目/七段目）が両方とも味方の歩
        board = create_hirate_board()
        assert generate_knight_moves(board, file, rank) == []


class Test桂馬の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_knight_moves(Board(), 5, 5)

    def test_桂馬以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.LANCE)))
        with pytest.raises(ValueError):
            generate_knight_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_knight_moves(Board(), 10, 5)


class Test銀将の5方向:
    def test_先手の銀は前3方向と後ろ斜め2方向へ動ける(self):
        # 5五の先手銀 → 前: 4四 5四 6四、後ろ斜め: 4六 6六
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.SILVER)))
        assert generate_silver_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),
            Move(5, 5, 5, 4),
            Move(5, 5, 6, 4),
            Move(5, 5, 4, 6),
            Move(5, 5, 6, 6),
        ]

    def test_後手の銀は方向が反転する(self):
        # 5五の後手銀 → 前(rank+1): 4六 5六 6六、後ろ斜め(rank-1): 4四 6四
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.SILVER)))
        assert generate_silver_moves(board, 5, 5) == [
            Move(5, 5, 4, 6),
            Move(5, 5, 5, 6),
            Move(5, 5, 6, 6),
            Move(5, 5, 4, 4),
            Move(5, 5, 6, 4),
        ]

    def test_横と真後ろには動けない(self):
        # 完全一致テストの補強として、動けない3方向を明示的に確認する
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.SILVER)))
        destinations = {
            (move.to_file, move.to_rank) for move in generate_silver_moves(board, 5, 5)
        }
        assert (4, 5) not in destinations  # 横
        assert (6, 5) not in destinations  # 横
        assert (5, 6) not in destinations  # 真後ろ


class Test銀将の盤の端:
    def test_1筋の銀は左方向が欠ける(self):
        board = board_with((1, 5, Piece(Color.BLACK, PieceType.SILVER)))
        assert generate_silver_moves(board, 1, 5) == [
            Move(1, 5, 1, 4),
            Move(1, 5, 2, 4),
            Move(1, 5, 2, 6),
        ]

    def test_最奥の段の銀は後ろ斜めしか残らない(self):
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.SILVER)))
        assert generate_silver_moves(board, 5, 1) == [
            Move(5, 1, 4, 2),
            Move(5, 1, 6, 2),
        ]

    def test_先手の銀が一一の角では後ろ斜め1マスだけ(self):
        # 前3方向は盤外（rank 0）、後ろ斜め左（file 0）も盤外
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.SILVER)))
        assert generate_silver_moves(board, 1, 1) == [Move(1, 1, 2, 2)]

    def test_後手の銀が九九の角では後ろ斜め1マスだけ(self):
        board = board_with((9, 9, Piece(Color.WHITE, PieceType.SILVER)))
        assert generate_silver_moves(board, 9, 9) == [Move(9, 9, 8, 8)]


class Test銀将の移動先の駒:
    def test_味方駒のマスは除外され相手駒のマスは含まれる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.SILVER)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 前: 味方 → 除外
            (4, 4, Piece(Color.WHITE, PieceType.PAWN)),  # 前斜め左: 相手 → 含む
        )
        assert generate_silver_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),  # 相手駒を取る手
            Move(5, 5, 6, 4),
            Move(5, 5, 4, 6),
            Move(5, 5, 6, 6),
        ]

    def test_5方向すべて味方駒なら候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.SILVER)),
            (4, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (4, 6, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 6, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_silver_moves(board, 5, 5) == []


class Test銀将の平手初期局面:
    def test_先手の3九銀は2八の飛車に塞がれる(self):
        # 後ろ斜めは盤外（rank 10）、前斜め右の2八は味方の飛車 → 除外
        board = create_hirate_board()
        assert generate_silver_moves(board, 3, 9) == [
            Move(3, 9, 3, 8),
            Move(3, 9, 4, 8),
        ]

    def test_先手の7九銀は8八の角に塞がれる(self):
        board = create_hirate_board()
        assert generate_silver_moves(board, 7, 9) == [
            Move(7, 9, 6, 8),
            Move(7, 9, 7, 8),
        ]

    def test_後手の3一銀は2二の角に塞がれる(self):
        board = create_hirate_board()
        assert generate_silver_moves(board, 3, 1) == [
            Move(3, 1, 3, 2),
            Move(3, 1, 4, 2),
        ]


class Test銀将の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_silver_moves(Board(), 5, 5)

    def test_銀将以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            generate_silver_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_silver_moves(Board(), 0, 0)


class Test金将の6方向:
    def test_先手の金は前3方向と横2方向と真後ろへ動ける(self):
        # 5五の先手金 → 前: 4四 5四 6四、横: 4五 6五、真後ろ: 5六
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        assert generate_gold_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),
            Move(5, 5, 5, 4),
            Move(5, 5, 6, 4),
            Move(5, 5, 4, 5),
            Move(5, 5, 6, 5),
            Move(5, 5, 5, 6),
        ]

    def test_後手の金は前後が反転する(self):
        # 5五の後手金 → 前(rank+1): 4六 5六 6六、横: 4五 6五、真後ろ: 5四
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.GOLD)))
        assert generate_gold_moves(board, 5, 5) == [
            Move(5, 5, 4, 6),
            Move(5, 5, 5, 6),
            Move(5, 5, 6, 6),
            Move(5, 5, 4, 5),
            Move(5, 5, 6, 5),
            Move(5, 5, 5, 4),
        ]

    def test_後ろ斜めには動けない(self):
        # 銀との違い。完全一致テストの補強として明示的に確認する
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        destinations = {
            (move.to_file, move.to_rank) for move in generate_gold_moves(board, 5, 5)
        }
        assert (4, 6) not in destinations  # 後ろ斜め左
        assert (6, 6) not in destinations  # 後ろ斜め右


class Test金将の盤の端:
    def test_1筋の金は左方向が欠ける(self):
        board = board_with((1, 5, Piece(Color.BLACK, PieceType.GOLD)))
        assert generate_gold_moves(board, 1, 5) == [
            Move(1, 5, 1, 4),
            Move(1, 5, 2, 4),
            Move(1, 5, 2, 5),
            Move(1, 5, 1, 6),
        ]

    def test_最奥の段の金は横と真後ろだけ残る(self):
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.GOLD)))
        assert generate_gold_moves(board, 5, 1) == [
            Move(5, 1, 4, 1),
            Move(5, 1, 6, 1),
            Move(5, 1, 5, 2),
        ]

    def test_先手の金が一一の角では横と真後ろの2マスだけ(self):
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.GOLD)))
        assert generate_gold_moves(board, 1, 1) == [
            Move(1, 1, 2, 1),
            Move(1, 1, 1, 2),
        ]

    def test_後手の金が九九の角では横と真後ろの2マスだけ(self):
        board = board_with((9, 9, Piece(Color.WHITE, PieceType.GOLD)))
        assert generate_gold_moves(board, 9, 9) == [
            Move(9, 9, 8, 9),
            Move(9, 9, 9, 8),
        ]


class Test金将の移動先の駒:
    def test_味方駒のマスは除外され相手駒のマスは含まれる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 前: 味方 → 除外
            (4, 5, Piece(Color.WHITE, PieceType.PAWN)),  # 横左: 相手 → 含む
        )
        assert generate_gold_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),
            Move(5, 5, 6, 4),
            Move(5, 5, 4, 5),  # 相手駒を取る手
            Move(5, 5, 6, 5),
            Move(5, 5, 5, 6),
        ]

    def test_6方向すべて味方駒なら候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.GOLD)),
            (4, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (4, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 6, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_gold_moves(board, 5, 5) == []


class Test金将の平手初期局面:
    def test_先手の4九金は前3マスに動ける(self):
        # 横の3九銀・5九玉は味方 → 除外、真後ろは盤外
        board = create_hirate_board()
        assert generate_gold_moves(board, 4, 9) == [
            Move(4, 9, 3, 8),
            Move(4, 9, 4, 8),
            Move(4, 9, 5, 8),
        ]

    def test_後手の6一金は前3マスに動ける(self):
        # 横の5一玉・7一銀は味方 → 除外、真後ろは盤外
        board = create_hirate_board()
        assert generate_gold_moves(board, 6, 1) == [
            Move(6, 1, 5, 2),
            Move(6, 1, 6, 2),
            Move(6, 1, 7, 2),
        ]


class Test金将の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_gold_moves(Board(), 5, 5)

    def test_金将以外の駒を指定するとValueError(self):
        # 動きが同じ「と金」も金将ではないので ValueError（成駒対応は別 Phase）
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.PROMOTED_PAWN)))
        with pytest.raises(ValueError):
            generate_gold_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_gold_moves(Board(), 5, 0)
