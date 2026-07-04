"""駒の疑似合法手の生成（SHOGI-2）。現在は歩・香車・桂馬・銀将・金将のみ。

疑似合法手 = 駒の動きとして可能な移動先のうち、盤外と味方駒のあるマスを
除いたもの。王手放置・二歩などの反則の除外（合法手判定）は SHOGI-3 の
責務のため、ここでは行わない。成り・駒打ちも後続で扱う。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.move import Move
from shogi.piece import Color, PieceType

# 前方向（rank の増減）。先手は奥（rank が小さい方）へ、後手は手前へ。歩・香・桂で共用
_FORWARD = {Color.BLACK: -1, Color.WHITE: +1}


def _step_moves(
    board: Board,
    file: int,
    rank: int,
    color: Color,
    offsets: list[tuple[int, int]],
) -> list[Move]:
    """固定オフセット (file差分, rank差分) への1歩移動の候補を返す。

    盤外と味方駒のあるマスは除外する。途中のマスは見ない（桂馬のように
    駒を飛び越える動きに対応）。走り駒（香・飛・角）はこのヘルパーではなく
    「遮られるまで進む」ループで扱う。
    """
    moves = []
    for dfile, drank in offsets:
        to_file, to_rank = file + dfile, rank + drank
        if not (1 <= to_file <= BOARD_SIZE and 1 <= to_rank <= BOARD_SIZE):
            continue  # 盤外
        target = board.get_piece(to_file, to_rank)
        if target is not None and target.color is color:
            continue  # 味方駒のあるマス
        moves.append(Move(file, rank, to_file, to_rank))
    return moves


def generate_pawn_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの歩の疑似合法手を返す。

    移動先が盤外・味方駒のあるマスの場合は候補に含めない
    （空きマスと相手駒のマスだけが候補）。
    指定マスが空きマス、または歩以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PAWN:
        raise ValueError(f"({file}, {rank}) に歩がありません: {piece!r}")

    to_rank = rank + _FORWARD[piece.color]
    if not 1 <= to_rank <= BOARD_SIZE:
        return []  # 盤外（最奥の段にいる歩）。行き所のない駒の反則扱いは SHOGI-3
    target = board.get_piece(file, to_rank)
    if target is not None and target.color is piece.color:
        return []  # 移動先に味方駒がある
    return [Move(file, rank, file, to_rank)]


def generate_lance_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの香車の疑似合法手を、移動元に近い順で返す。

    前方向（先手は rank が小さい方、後手は大きい方）へ連続で進む。
    盤外に出る手前で停止する。味方駒の手前で停止し、そのマスは含めない。
    相手駒のマスで停止し、そのマスは含める（取る手になる）。
    指定マスが空きマス、または香車以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.LANCE:
        raise ValueError(f"({file}, {rank}) に香車がありません: {piece!r}")

    moves = []
    to_rank = rank + _FORWARD[piece.color]
    while 1 <= to_rank <= BOARD_SIZE:
        target = board.get_piece(file, to_rank)
        if target is not None and target.color is piece.color:
            break  # 味方駒の手前で停止（そのマスは含めない）
        moves.append(Move(file, rank, file, to_rank))
        if target is not None:
            break  # 相手駒のマスで停止（そのマスまでは含める）
        to_rank += _FORWARD[piece.color]
    return moves


def generate_knight_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの桂馬の疑似合法手を返す。

    前方向へ2段・左右いずれかへ1筋のマス（最大2箇所）へ跳ぶ。
    途中のマスに駒があっても飛び越えられる（遮断されない）。
    盤外と味方駒のあるマスは候補に含めない（空きマスと相手駒のマスは含める）。
    指定マスが空きマス、または桂馬以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.KNIGHT:
        raise ValueError(f"({file}, {rank}) に桂馬がありません: {piece!r}")

    two_forward = 2 * _FORWARD[piece.color]
    offsets = [(-1, two_forward), (+1, two_forward)]  # file の小さい側から
    return _step_moves(board, file, rank, piece.color, offsets)


def generate_silver_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの銀将の疑似合法手を返す。

    動ける方向は5つ: 前・前斜め左右・後ろ斜め左右（横と真後ろには動けない）。
    盤外と味方駒のあるマスは候補に含めない（空きマスと相手駒のマスは含める）。
    指定マスが空きマス、または銀将以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.SILVER:
        raise ValueError(f"({file}, {rank}) に銀将がありません: {piece!r}")

    forward = _FORWARD[piece.color]
    # 前の3マス（file の小さい側から）→ 後ろ斜めの2マス
    offsets = [
        (-1, forward),
        (0, forward),
        (+1, forward),
        (-1, -forward),
        (+1, -forward),
    ]
    return _step_moves(board, file, rank, piece.color, offsets)


def generate_gold_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの金将の疑似合法手を返す。

    動ける方向は6つ: 前・前斜め左右・横左右・真後ろ（後ろ斜めには動けない）。
    盤外と味方駒のあるマスは候補に含めない（空きマスと相手駒のマスは含める）。
    指定マスが空きマス、または金将以外の駒の場合は ValueError を送出する。
    と金・成香・成桂・成銀も同じ動きだが、成駒対応の Phase で扱う。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.GOLD:
        raise ValueError(f"({file}, {rank}) に金将がありません: {piece!r}")

    forward = _FORWARD[piece.color]
    # 前の3マス（file の小さい側から）→ 横の2マス → 真後ろ
    offsets = [
        (-1, forward),
        (0, forward),
        (+1, forward),
        (-1, 0),
        (+1, 0),
        (0, -forward),
    ]
    return _step_moves(board, file, rank, piece.color, offsets)
