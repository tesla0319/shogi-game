"""平手初期局面の生成。

空盤の Board に平手の40枚を配置して返すことだけを扱う。
手番・持ち駒・SFEN 入出力は後続 Phase の責務のため、ここでは扱わない。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.piece import Color, Piece, PieceType

# 自陣一番奥の段（先手なら九段目、後手なら一段目）の並び。file=1 から 9 の順。
# 香 桂 銀 金 玉 金 銀 桂 香 で左右対称
_BACK_RANK_ORDER = (
    PieceType.LANCE,
    PieceType.KNIGHT,
    PieceType.SILVER,
    PieceType.GOLD,
    PieceType.KING,
    PieceType.GOLD,
    PieceType.SILVER,
    PieceType.KNIGHT,
    PieceType.LANCE,
)


def create_hirate_board() -> Board:
    """平手の初期局面（40枚配置済み）の Board を返す。"""
    board = Board()
    # 後手（上側）: 飛車は8二、角は2二
    _place_side(board, Color.WHITE, back_rank=1, pawn_rank=3, rook=(8, 2), bishop=(2, 2))
    # 先手（下側）: 飛車は2八、角は8八
    _place_side(board, Color.BLACK, back_rank=9, pawn_rank=7, rook=(2, 8), bishop=(8, 8))
    return board


def _place_side(
    board: Board,
    color: Color,
    back_rank: int,
    pawn_rank: int,
    rook: tuple[int, int],
    bishop: tuple[int, int],
) -> None:
    """片方の陣営の20枚（奥の段9枚 + 飛角2枚 + 歩9枚）を配置する。"""
    for file, piece_type in enumerate(_BACK_RANK_ORDER, start=1):
        board.set_piece(file, back_rank, Piece(color, piece_type))
    board.set_piece(rook[0], rook[1], Piece(color, PieceType.ROOK))
    board.set_piece(bishop[0], bishop[1], Piece(color, PieceType.BISHOP))
    for file in range(1, BOARD_SIZE + 1):
        board.set_piece(file, pawn_rank, Piece(color, PieceType.PAWN))
