"""疑似合法手生成のテスト（SHOGI-2a〜2h: 基本8駒種、2i: 成駒6種）。

疑似合法手の範囲（盤外・味方駒マスの除外、走り駒の停止位置）のみを検証する。
二歩・王手放置などの反則除外（SHOGI-3）、成り、駒打ちは対象外。
"""

import pytest

from shogi.board import Board
from shogi.initial_position import create_hirate_board
from shogi.move import Move
from shogi.movegen import (
    generate_bishop_moves,
    generate_dragon_moves,
    generate_gold_moves,
    generate_horse_moves,
    generate_king_moves,
    generate_knight_moves,
    generate_lance_moves,
    generate_pawn_moves,
    generate_piece_moves,
    generate_promoted_knight_moves,
    generate_promoted_lance_moves,
    generate_promoted_pawn_moves,
    generate_promoted_silver_moves,
    generate_rook_moves,
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

    def test_後手の歩も相手駒を取れる(self):
        board = board_with(
            (5, 5, Piece(Color.WHITE, PieceType.PAWN)),
            (5, 6, Piece(Color.BLACK, PieceType.GOLD)),
        )
        assert generate_pawn_moves(board, 5, 5) == [Move(5, 5, 5, 6)]


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

    def test_後手の香も相手駒のマスで停止する(self):
        board = board_with(
            (5, 1, Piece(Color.WHITE, PieceType.LANCE)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_lance_moves(board, 5, 1) == [
            Move(5, 1, 5, 2),
            Move(5, 1, 5, 3),
            Move(5, 1, 5, 4),  # 相手駒を取る手。その先（5五以降）は不可
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


class Test玉将の8方向:
    # file の小さい側から、同じ file 内では rank の小さい側から並ぶ
    EXPECTED_FROM_5_5 = [
        Move(5, 5, 4, 4),
        Move(5, 5, 4, 5),
        Move(5, 5, 4, 6),
        Move(5, 5, 5, 4),
        Move(5, 5, 5, 6),
        Move(5, 5, 6, 4),
        Move(5, 5, 6, 5),
        Move(5, 5, 6, 6),
    ]

    def test_先手の玉は隣接8方向へ動ける(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.KING)))
        assert generate_king_moves(board, 5, 5) == self.EXPECTED_FROM_5_5

    def test_後手の玉も同じ8方向へ動ける(self):
        # 玉は全方向対称なので手番で動きが変わらない
        board = board_with((5, 5, Piece(Color.WHITE, PieceType.KING)))
        assert generate_king_moves(board, 5, 5) == self.EXPECTED_FROM_5_5


class Test玉将の盤の端:
    def test_1筋の玉は左方向が欠けて5マス(self):
        board = board_with((1, 5, Piece(Color.BLACK, PieceType.KING)))
        assert generate_king_moves(board, 1, 5) == [
            Move(1, 5, 1, 4),
            Move(1, 5, 1, 6),
            Move(1, 5, 2, 4),
            Move(1, 5, 2, 5),
            Move(1, 5, 2, 6),
        ]

    def test_最奥の段の玉は前方向が欠けて5マス(self):
        board = board_with((5, 1, Piece(Color.BLACK, PieceType.KING)))
        assert generate_king_moves(board, 5, 1) == [
            Move(5, 1, 4, 1),
            Move(5, 1, 4, 2),
            Move(5, 1, 5, 2),
            Move(5, 1, 6, 1),
            Move(5, 1, 6, 2),
        ]

    def test_一一の角では3マスだけ(self):
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.KING)))
        assert generate_king_moves(board, 1, 1) == [
            Move(1, 1, 1, 2),
            Move(1, 1, 2, 1),
            Move(1, 1, 2, 2),
        ]

    def test_九九の角では3マスだけ(self):
        board = board_with((9, 9, Piece(Color.WHITE, PieceType.KING)))
        assert generate_king_moves(board, 9, 9) == [
            Move(9, 9, 8, 8),
            Move(9, 9, 8, 9),
            Move(9, 9, 9, 8),
        ]


class Test玉将の移動先の駒:
    def test_味方駒のマスは除外され相手駒のマスは含まれる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 4, Piece(Color.BLACK, PieceType.GOLD)),  # 前: 味方 → 除外
            (4, 4, Piece(Color.WHITE, PieceType.PAWN)),  # 前斜め左: 相手 → 含む
        )
        assert generate_king_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),  # 相手駒を取る手
            Move(5, 5, 4, 5),
            Move(5, 5, 4, 6),
            Move(5, 5, 5, 6),
            Move(5, 5, 6, 4),
            Move(5, 5, 6, 5),
            Move(5, 5, 6, 6),
        ]

    def test_8方向すべて味方駒なら候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            *(
                (5 + dfile, 5 + drank, Piece(Color.BLACK, PieceType.PAWN))
                for dfile in (-1, 0, 1)
                for drank in (-1, 0, 1)
                if (dfile, drank) != (0, 0)
            ),
        )
        assert generate_king_moves(board, 5, 5) == []

    def test_相手の利きがあるマスも候補に含める(self):
        # 5四は後手歩（5三）の利きだが、疑似合法手の層では除外しない
        # （自殺手の除外は SHOGI-3 の合法手判定の責務）
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.KING)),
            (5, 3, Piece(Color.WHITE, PieceType.PAWN)),
        )
        assert Move(5, 5, 5, 4) in generate_king_moves(board, 5, 5)


class Test玉将の平手初期局面:
    def test_先手の5九玉は前3マスに動ける(self):
        # 横の4九金・6九金は味方 → 除外、後ろは盤外
        board = create_hirate_board()
        assert generate_king_moves(board, 5, 9) == [
            Move(5, 9, 4, 8),
            Move(5, 9, 5, 8),
            Move(5, 9, 6, 8),
        ]

    def test_後手の5一玉は前3マスに動ける(self):
        board = create_hirate_board()
        assert generate_king_moves(board, 5, 1) == [
            Move(5, 1, 4, 2),
            Move(5, 1, 5, 2),
            Move(5, 1, 6, 2),
        ]


class Test玉将の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_king_moves(Board(), 5, 5)

    def test_玉将以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            generate_king_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_king_moves(Board(), 0, 5)


class Test飛車の走り:
    def test_中央から縦横4方向へ盤端まで走る(self):
        # 空盤の5五の飛車 → 縦8マス + 横8マスの計16手
        # 並び: 縦(rank小→大) → 横(file小→大)、各方向とも近い順
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.ROOK)))
        assert generate_rook_moves(board, 5, 5) == [
            # 奥方向（rank 4→1）
            Move(5, 5, 5, 4),
            Move(5, 5, 5, 3),
            Move(5, 5, 5, 2),
            Move(5, 5, 5, 1),
            # 手前方向（rank 6→9）
            Move(5, 5, 5, 6),
            Move(5, 5, 5, 7),
            Move(5, 5, 5, 8),
            Move(5, 5, 5, 9),
            # file の小さい方向（4→1）
            Move(5, 5, 4, 5),
            Move(5, 5, 3, 5),
            Move(5, 5, 2, 5),
            Move(5, 5, 1, 5),
            # file の大きい方向（6→9）
            Move(5, 5, 6, 5),
            Move(5, 5, 7, 5),
            Move(5, 5, 8, 5),
            Move(5, 5, 9, 5),
        ]

    def test_後手の飛車も同じ動きになる(self):
        # 飛車は全方向対称なので手番で動きが変わらない
        black = board_with((5, 5, Piece(Color.BLACK, PieceType.ROOK)))
        white = board_with((5, 5, Piece(Color.WHITE, PieceType.ROOK)))
        assert generate_rook_moves(black, 5, 5) == generate_rook_moves(white, 5, 5)

    def test_角にいる飛車は2方向だけ残り盤端で止まる(self):
        # 一一の飛車 → 手前方向8マス + file大方向8マスの計16手（盤外の手が出ない）
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.ROOK)))
        destinations = {
            (move.to_file, move.to_rank) for move in generate_rook_moves(board, 1, 1)
        }
        assert destinations == {(1, r) for r in range(2, 10)} | {
            (f, 1) for f in range(2, 10)
        }


class Test飛車の停止:
    def test_味方駒の手前で止まりそのマスには進めない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 2, Piece(Color.BLACK, PieceType.PAWN)),  # 奥方向の味方
        )
        moves = generate_rook_moves(board, 5, 5)
        assert Move(5, 5, 5, 3) in moves  # 手前までは進める
        assert Move(5, 5, 5, 2) not in moves  # 味方駒のマスは不可
        assert Move(5, 5, 5, 1) not in moves  # その先も不可

    def test_相手駒のマスには進めるがその先には進めない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 7, Piece(Color.WHITE, PieceType.PAWN)),  # 手前方向の相手
        )
        moves = generate_rook_moves(board, 5, 5)
        assert Move(5, 5, 5, 6) in moves
        assert Move(5, 5, 5, 7) in moves  # 相手駒を取る手
        assert Move(5, 5, 5, 8) not in moves  # 相手駒の先へは進めない
        assert Move(5, 5, 5, 9) not in moves

    def test_複数方向のブロッカーが混在しても正しい(self):
        # 奥: 味方（5三）、手前: 相手（5七）、file小: 味方（3五）、file大: 遮り無し
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 3, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 7, Piece(Color.WHITE, PieceType.PAWN)),
            (3, 5, Piece(Color.BLACK, PieceType.SILVER)),
        )
        assert generate_rook_moves(board, 5, 5) == [
            Move(5, 5, 5, 4),  # 奥: 味方の手前まで
            Move(5, 5, 5, 6),  # 手前: 相手のマスまで
            Move(5, 5, 5, 7),
            Move(5, 5, 4, 5),  # file小: 味方の手前まで
            Move(5, 5, 6, 5),  # file大: 盤端まで
            Move(5, 5, 7, 5),
            Move(5, 5, 8, 5),
            Move(5, 5, 9, 5),
        ]

    def test_四方を隣接する味方駒に囲まれると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.ROOK)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (5, 6, Piece(Color.BLACK, PieceType.PAWN)),
            (4, 5, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 5, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_rook_moves(board, 5, 5) == []


class Test飛車の平手初期局面:
    def test_先手の2八飛は横に6マス動ける(self):
        # 縦は2七の歩と2九の桂（ともに味方）に塞がれ、横は1八と3八〜7八
        # （8八の角は味方なので手前まで）
        board = create_hirate_board()
        assert generate_rook_moves(board, 2, 8) == [
            Move(2, 8, 1, 8),
            Move(2, 8, 3, 8),
            Move(2, 8, 4, 8),
            Move(2, 8, 5, 8),
            Move(2, 8, 6, 8),
            Move(2, 8, 7, 8),
        ]


class Test飛車の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_rook_moves(Board(), 5, 5)

    def test_飛車以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.LANCE)))
        with pytest.raises(ValueError):
            generate_rook_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_rook_moves(Board(), 10, 10)


class Test角行の走り:
    def test_中央から斜め4方向へ盤端まで走る(self):
        # 空盤の5五の角 → 各斜め4マスずつの計16手
        # 並び: file小側(rank小→大) → file大側(rank小→大)、各方向とも近い順
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.BISHOP)))
        assert generate_bishop_moves(board, 5, 5) == [
            # file小・rank小方向（4四 → 一一）
            Move(5, 5, 4, 4),
            Move(5, 5, 3, 3),
            Move(5, 5, 2, 2),
            Move(5, 5, 1, 1),
            # file小・rank大方向（4六 → 一九）
            Move(5, 5, 4, 6),
            Move(5, 5, 3, 7),
            Move(5, 5, 2, 8),
            Move(5, 5, 1, 9),
            # file大・rank小方向（6四 → 九一）
            Move(5, 5, 6, 4),
            Move(5, 5, 7, 3),
            Move(5, 5, 8, 2),
            Move(5, 5, 9, 1),
            # file大・rank大方向（6六 → 九九）
            Move(5, 5, 6, 6),
            Move(5, 5, 7, 7),
            Move(5, 5, 8, 8),
            Move(5, 5, 9, 9),
        ]

    def test_後手の角も同じ動きになる(self):
        # 角は全方向対称なので手番で動きが変わらない
        black = board_with((5, 5, Piece(Color.BLACK, PieceType.BISHOP)))
        white = board_with((5, 5, Piece(Color.WHITE, PieceType.BISHOP)))
        assert generate_bishop_moves(black, 5, 5) == generate_bishop_moves(white, 5, 5)

    def test_一一の角にいる角行は対角線1本だけ(self):
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.BISHOP)))
        assert generate_bishop_moves(board, 1, 1) == [
            Move(1, 1, d, d) for d in range(2, 10)
        ]

    def test_盤の辺にいる角行は2方向だけ残る(self):
        # 1筋の5段目 → file小の2方向は盤外、file大の2方向のみ
        board = board_with((1, 5, Piece(Color.BLACK, PieceType.BISHOP)))
        assert generate_bishop_moves(board, 1, 5) == [
            Move(1, 5, 2, 4),
            Move(1, 5, 3, 3),
            Move(1, 5, 4, 2),
            Move(1, 5, 5, 1),
            Move(1, 5, 2, 6),
            Move(1, 5, 3, 7),
            Move(1, 5, 4, 8),
            Move(1, 5, 5, 9),
        ]


class Test角行の停止:
    def test_味方駒の手前で止まりそのマスには進めない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.BISHOP)),
            (3, 3, Piece(Color.BLACK, PieceType.PAWN)),  # file小・rank小方向の味方
        )
        moves = generate_bishop_moves(board, 5, 5)
        assert Move(5, 5, 4, 4) in moves  # 手前までは進める
        assert Move(5, 5, 3, 3) not in moves  # 味方駒のマスは不可
        assert Move(5, 5, 2, 2) not in moves  # その先も不可

    def test_相手駒のマスには進めるがその先には進めない(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.BISHOP)),
            (7, 7, Piece(Color.WHITE, PieceType.PAWN)),  # file大・rank大方向の相手
        )
        moves = generate_bishop_moves(board, 5, 5)
        assert Move(5, 5, 6, 6) in moves
        assert Move(5, 5, 7, 7) in moves  # 相手駒を取る手
        assert Move(5, 5, 8, 8) not in moves  # 相手駒の先へは進めない
        assert Move(5, 5, 9, 9) not in moves

    def test_複数方向のブロッカーが混在しても正しい(self):
        # 4方向: 味方（3三）/ 相手（3七）/ 相手（6四）/ 遮り無し
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.BISHOP)),
            (3, 3, Piece(Color.BLACK, PieceType.PAWN)),
            (3, 7, Piece(Color.WHITE, PieceType.PAWN)),
            (6, 4, Piece(Color.WHITE, PieceType.SILVER)),
        )
        assert generate_bishop_moves(board, 5, 5) == [
            Move(5, 5, 4, 4),  # 味方の手前まで
            Move(5, 5, 4, 6),  # 相手のマスまで
            Move(5, 5, 3, 7),
            Move(5, 5, 6, 4),  # 隣が相手: そのマスだけ
            Move(5, 5, 6, 6),  # 遮り無し: 盤端まで
            Move(5, 5, 7, 7),
            Move(5, 5, 8, 8),
            Move(5, 5, 9, 9),
        ]

    def test_斜め四方を隣接する味方駒に囲まれると候補なし(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.BISHOP)),
            (4, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (4, 6, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 4, Piece(Color.BLACK, PieceType.PAWN)),
            (6, 6, Piece(Color.BLACK, PieceType.PAWN)),
        )
        assert generate_bishop_moves(board, 5, 5) == []


class Test角行の平手初期局面:
    def test_先手の8八角は味方に囲まれて動けない(self):
        # 斜め4方向の隣がすべて味方（7七歩・7九銀・9七歩・9九香）
        board = create_hirate_board()
        assert generate_bishop_moves(board, 8, 8) == []

    def test_後手の2二角も味方に囲まれて動けない(self):
        board = create_hirate_board()
        assert generate_bishop_moves(board, 2, 2) == []


class Test角行の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_bishop_moves(Board(), 5, 5)

    def test_角行以外の駒を指定するとValueError(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.ROOK)))
        with pytest.raises(ValueError):
            generate_bishop_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_bishop_moves(Board(), 0, 10)


# 金系成駒: (生成関数, 成駒の駒種, 成る前の駒種)
GOLD_LIKE_CASES = [
    (generate_promoted_pawn_moves, PieceType.PROMOTED_PAWN, PieceType.PAWN),
    (generate_promoted_lance_moves, PieceType.PROMOTED_LANCE, PieceType.LANCE),
    (generate_promoted_knight_moves, PieceType.PROMOTED_KNIGHT, PieceType.KNIGHT),
    (generate_promoted_silver_moves, PieceType.PROMOTED_SILVER, PieceType.SILVER),
]

GOLD_LIKE_PARAMS = pytest.mark.parametrize(
    ("generate", "piece_type", "base_type"),
    GOLD_LIKE_CASES,
    ids=["と金", "成香", "成桂", "成銀"],
)


class Test金系成駒の6方向:
    @GOLD_LIKE_PARAMS
    def test_先手は金と同じ6方向へ動ける(self, generate, piece_type, base_type):
        # 5五の先手成駒 → 前: 4四 5四 6四、横: 4五 6五、真後ろ: 5六
        board = board_with((5, 5, Piece(Color.BLACK, piece_type)))
        assert generate(board, 5, 5) == [
            Move(5, 5, 4, 4),
            Move(5, 5, 5, 4),
            Move(5, 5, 6, 4),
            Move(5, 5, 4, 5),
            Move(5, 5, 6, 5),
            Move(5, 5, 5, 6),
        ]

    @GOLD_LIKE_PARAMS
    def test_後手は前後が反転する(self, generate, piece_type, base_type):
        board = board_with((5, 5, Piece(Color.WHITE, piece_type)))
        assert generate(board, 5, 5) == [
            Move(5, 5, 4, 6),
            Move(5, 5, 5, 6),
            Move(5, 5, 6, 6),
            Move(5, 5, 4, 5),
            Move(5, 5, 6, 5),
            Move(5, 5, 5, 4),
        ]

    @GOLD_LIKE_PARAMS
    def test_後ろ斜めには動けない(self, generate, piece_type, base_type):
        board = board_with((5, 5, Piece(Color.BLACK, piece_type)))
        destinations = {(move.to_file, move.to_rank) for move in generate(board, 5, 5)}
        assert (4, 6) not in destinations
        assert (6, 6) not in destinations

    @GOLD_LIKE_PARAMS
    def test_同じ配置の金将と完全に同じ手を生成する(self, generate, piece_type, base_type):
        # 金の再利用による挙動一貫性の確認。障害物を混ぜた同一配置で比較する
        obstacles = [
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 前: 味方
            (4, 5, Piece(Color.WHITE, PieceType.PAWN)),  # 横左: 相手
        ]
        promoted_board = board_with((5, 5, Piece(Color.BLACK, piece_type)), *obstacles)
        gold_board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)), *obstacles)
        assert generate(promoted_board, 5, 5) == generate_gold_moves(gold_board, 5, 5)


class Test金系成駒の境界と駒:
    @GOLD_LIKE_PARAMS
    def test_一一の角では横と真後ろの2マスだけ(self, generate, piece_type, base_type):
        board = board_with((1, 1, Piece(Color.BLACK, piece_type)))
        assert generate(board, 1, 1) == [
            Move(1, 1, 2, 1),
            Move(1, 1, 1, 2),
        ]

    @GOLD_LIKE_PARAMS
    def test_味方駒のマスは除外され相手駒のマスは含まれる(
        self, generate, piece_type, base_type
    ):
        board = board_with(
            (5, 5, Piece(Color.BLACK, piece_type)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 前: 味方 → 除外
            (6, 5, Piece(Color.WHITE, PieceType.PAWN)),  # 横右: 相手 → 含む
        )
        moves = generate(board, 5, 5)
        assert Move(5, 5, 5, 4) not in moves
        assert Move(5, 5, 6, 5) in moves  # 相手駒を取る手


class Test金系成駒の異常系:
    @GOLD_LIKE_PARAMS
    def test_空きマスを指定するとValueError(self, generate, piece_type, base_type):
        with pytest.raises(ValueError):
            generate(Board(), 5, 5)

    @GOLD_LIKE_PARAMS
    def test_金将を渡してもValueError(self, generate, piece_type, base_type):
        # 動きは同じでも駒種は別。生成関数は自分の駒種だけを受け付ける
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.GOLD)))
        with pytest.raises(ValueError):
            generate(board, 5, 5)

    @GOLD_LIKE_PARAMS
    def test_成る前の駒を渡してもValueError(self, generate, piece_type, base_type):
        # 例: と金の生成関数に歩を渡す
        board = board_with((5, 5, Piece(Color.BLACK, base_type)))
        with pytest.raises(ValueError):
            generate(board, 5, 5)

    @GOLD_LIKE_PARAMS
    def test_盤外の座標を指定するとValueError(self, generate, piece_type, base_type):
        with pytest.raises(ValueError):
            generate(Board(), 0, 5)


class Test馬の動き:
    def test_中央では斜めの走りと縦横1マスの計20手(self):
        # 空盤の5五の馬 → 角と同じ斜め16手 + 縦横の隣接4マス
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.HORSE)))
        bishop_board = board_with((5, 5, Piece(Color.BLACK, PieceType.BISHOP)))
        expected_sliding = [
            Move(5, 5, move.to_file, move.to_rank)
            for move in generate_bishop_moves(bishop_board, 5, 5)
        ]
        assert generate_horse_moves(board, 5, 5) == expected_sliding + [
            Move(5, 5, 5, 4),  # 縦横1マス
            Move(5, 5, 5, 6),
            Move(5, 5, 4, 5),
            Move(5, 5, 6, 5),
        ]

    def test_先手後手で動きは変わらない(self):
        black = board_with((5, 5, Piece(Color.BLACK, PieceType.HORSE)))
        white = board_with((5, 5, Piece(Color.WHITE, PieceType.HORSE)))
        assert generate_horse_moves(black, 5, 5) == generate_horse_moves(white, 5, 5)

    def test_縦横へは1マスより先に進めない(self):
        # 走りは斜めだけ。縦横の2マス先（空きマス）は候補に含まれない
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.HORSE)))
        moves = generate_horse_moves(board, 5, 5)
        assert Move(5, 5, 5, 3) not in moves
        assert Move(5, 5, 3, 5) not in moves

    def test_斜めの走りは相手駒のマスで停止する(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.HORSE)),
            (7, 7, Piece(Color.WHITE, PieceType.PAWN)),
        )
        moves = generate_horse_moves(board, 5, 5)
        assert Move(5, 5, 7, 7) in moves  # 取る手
        assert Move(5, 5, 8, 8) not in moves  # その先は不可

    def test_縦横1マスも味方は除外され相手は含まれる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.HORSE)),
            (5, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 縦: 味方 → 除外
            (4, 5, Piece(Color.WHITE, PieceType.PAWN)),  # 横: 相手 → 含む
        )
        moves = generate_horse_moves(board, 5, 5)
        assert Move(5, 5, 5, 4) not in moves
        assert Move(5, 5, 4, 5) in moves

    def test_一一の角では対角線1本と縦横2マス(self):
        board = board_with((1, 1, Piece(Color.BLACK, PieceType.HORSE)))
        assert generate_horse_moves(board, 1, 1) == [
            *[Move(1, 1, d, d) for d in range(2, 10)],  # 斜めの走り
            Move(1, 1, 1, 2),  # 縦横1マス
            Move(1, 1, 2, 1),
        ]


class Test馬の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_horse_moves(Board(), 5, 5)

    def test_馬以外の駒を指定するとValueError(self):
        # 成る前の角でも ValueError
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.BISHOP)))
        with pytest.raises(ValueError):
            generate_horse_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_horse_moves(Board(), 10, 5)


class Test竜の動き:
    def test_中央では縦横の走りと斜め1マスの計20手(self):
        # 空盤の5五の竜 → 飛車と同じ縦横16手 + 斜めの隣接4マス
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.DRAGON)))
        rook_board = board_with((5, 5, Piece(Color.BLACK, PieceType.ROOK)))
        expected_sliding = [
            Move(5, 5, move.to_file, move.to_rank)
            for move in generate_rook_moves(rook_board, 5, 5)
        ]
        assert generate_dragon_moves(board, 5, 5) == expected_sliding + [
            Move(5, 5, 4, 4),  # 斜め1マス
            Move(5, 5, 4, 6),
            Move(5, 5, 6, 4),
            Move(5, 5, 6, 6),
        ]

    def test_先手後手で動きは変わらない(self):
        black = board_with((5, 5, Piece(Color.BLACK, PieceType.DRAGON)))
        white = board_with((5, 5, Piece(Color.WHITE, PieceType.DRAGON)))
        assert generate_dragon_moves(black, 5, 5) == generate_dragon_moves(white, 5, 5)

    def test_斜めへは1マスより先に進めない(self):
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.DRAGON)))
        moves = generate_dragon_moves(board, 5, 5)
        assert Move(5, 5, 3, 3) not in moves
        assert Move(5, 5, 7, 7) not in moves

    def test_縦横の走りは味方駒の手前で停止する(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.DRAGON)),
            (5, 2, Piece(Color.BLACK, PieceType.PAWN)),
        )
        moves = generate_dragon_moves(board, 5, 5)
        assert Move(5, 5, 5, 3) in moves  # 手前まで
        assert Move(5, 5, 5, 2) not in moves  # 味方のマスは不可

    def test_斜め1マスも味方は除外され相手は含まれる(self):
        board = board_with(
            (5, 5, Piece(Color.BLACK, PieceType.DRAGON)),
            (4, 4, Piece(Color.BLACK, PieceType.PAWN)),  # 斜め: 味方 → 除外
            (6, 6, Piece(Color.WHITE, PieceType.PAWN)),  # 斜め: 相手 → 含む
        )
        moves = generate_dragon_moves(board, 5, 5)
        assert Move(5, 5, 4, 4) not in moves
        assert Move(5, 5, 6, 6) in moves

    def test_九九の角では縦横2本と斜め1マス(self):
        board = board_with((9, 9, Piece(Color.WHITE, PieceType.DRAGON)))
        assert generate_dragon_moves(board, 9, 9) == [
            *[Move(9, 9, 9, r) for r in range(8, 0, -1)],  # 縦の走り
            *[Move(9, 9, f, 9) for f in range(8, 0, -1)],  # 横の走り
            Move(9, 9, 8, 8),  # 斜め1マス
        ]


class Test竜の異常系:
    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_dragon_moves(Board(), 5, 5)

    def test_竜以外の駒を指定するとValueError(self):
        # 成る前の飛車でも ValueError
        board = board_with((5, 5, Piece(Color.BLACK, PieceType.ROOK)))
        with pytest.raises(ValueError):
            generate_dragon_moves(board, 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_dragon_moves(Board(), 5, 0)


class Testディスパッチャ:
    # 全14駒種と専用生成関数の対応（テスト側で独立に列挙する）
    ALL_PIECE_CASES = [
        (PieceType.PAWN, generate_pawn_moves),
        (PieceType.LANCE, generate_lance_moves),
        (PieceType.KNIGHT, generate_knight_moves),
        (PieceType.SILVER, generate_silver_moves),
        (PieceType.GOLD, generate_gold_moves),
        (PieceType.BISHOP, generate_bishop_moves),
        (PieceType.ROOK, generate_rook_moves),
        (PieceType.KING, generate_king_moves),
        (PieceType.PROMOTED_PAWN, generate_promoted_pawn_moves),
        (PieceType.PROMOTED_LANCE, generate_promoted_lance_moves),
        (PieceType.PROMOTED_KNIGHT, generate_promoted_knight_moves),
        (PieceType.PROMOTED_SILVER, generate_promoted_silver_moves),
        (PieceType.HORSE, generate_horse_moves),
        (PieceType.DRAGON, generate_dragon_moves),
    ]

    @pytest.mark.parametrize(
        ("piece_type", "dedicated"),
        ALL_PIECE_CASES,
        ids=[piece_type.name for piece_type, _ in ALL_PIECE_CASES],
    )
    def test_全14駒種で専用関数と同じ結果を返す(self, piece_type, dedicated):
        board = board_with((5, 5, Piece(Color.BLACK, piece_type)))
        assert generate_piece_moves(board, 5, 5) == dedicated(board, 5, 5)

    def test_空きマスを指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_piece_moves(Board(), 5, 5)

    def test_盤外の座標を指定するとValueError(self):
        with pytest.raises(ValueError):
            generate_piece_moves(Board(), 0, 5)

    def test_平手初期局面の先手の疑似合法手は全体で30手(self):
        # 既知値との突き合わせ: 平手初期局面の先手の手は30手
        # （歩9 + 香2 + 銀4 + 金6 + 玉3 + 飛6。桂と角は動けない）
        board = create_hirate_board()
        moves = []
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = board.get_piece(file, rank)
                if piece is not None and piece.color is Color.BLACK:
                    moves.extend(generate_piece_moves(board, file, rank))
        assert len(moves) == 30

    def test_平手初期局面の後手の疑似合法手も30手(self):
        board = create_hirate_board()
        moves = []
        for file in range(1, 10):
            for rank in range(1, 10):
                piece = board.get_piece(file, rank)
                if piece is not None and piece.color is Color.WHITE:
                    moves.extend(generate_piece_moves(board, file, rank))
        assert len(moves) == 30
