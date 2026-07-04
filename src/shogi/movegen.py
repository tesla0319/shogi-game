"""駒の疑似合法手の生成（SHOGI-2）。現在は歩・香車のみ。

疑似合法手 = 駒の動きとして可能な移動先のうち、盤外と味方駒のあるマスを
除いたもの。王手放置・二歩などの反則の除外（合法手判定）は SHOGI-3 の
責務のため、ここでは行わない。成り・駒打ちも後続で扱う。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.move import Move
from shogi.piece import Color, PieceType

# 前方向（rank の増減）。先手は奥（rank が小さい方）へ、後手は手前へ。歩・香で共用
_FORWARD = {Color.BLACK: -1, Color.WHITE: +1}


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
