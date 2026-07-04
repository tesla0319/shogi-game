"""駒の疑似合法手の生成（SHOGI-2）。現在は歩のみ。

疑似合法手 = 駒の動きとして可能な移動先のうち、盤外と味方駒のあるマスを
除いたもの。王手放置・二歩などの反則の除外（合法手判定）は SHOGI-3 の
責務のため、ここでは行わない。成り・駒打ちも後続で扱う。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.move import Move
from shogi.piece import Color, PieceType

# 歩が進む方向（rank の増減）。先手は奥（rank が小さい方）へ、後手は手前へ
_PAWN_DIRECTION = {Color.BLACK: -1, Color.WHITE: +1}


def generate_pawn_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの歩の疑似合法手を返す。

    移動先が盤外・味方駒のあるマスの場合は候補に含めない
    （空きマスと相手駒のマスだけが候補）。
    指定マスが空きマス、または歩以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PAWN:
        raise ValueError(f"({file}, {rank}) に歩がありません: {piece!r}")

    to_rank = rank + _PAWN_DIRECTION[piece.color]
    if not 1 <= to_rank <= BOARD_SIZE:
        return []  # 盤外（最奥の段にいる歩）。行き所のない駒の反則扱いは SHOGI-3
    target = board.get_piece(file, to_rank)
    if target is not None and target.color is piece.color:
        return []  # 移動先に味方駒がある
    return [Move(file, rank, file, to_rank)]
