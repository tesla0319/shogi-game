"""合法手判定の基盤（SHOGI-3）。

疑似合法手の生成（movegen）とは別の責務。SHOGI-3a で「ある手を指した後の
盤面」を作るシミュレート（board_after_move）、SHOGI-3b で王手検出
（find_king / is_attacked / is_in_check）を提供する。自殺手の除外・合法手の
確定（generate_legal_moves）は後続のサブフェーズ（3c）で追加する。

持ち駒・駒打ちは扱わない（SHOGI-4 の責務）。取った駒は盤から除去するだけで、
持ち駒には加えない。取った駒種が必要な処理（持ち駒への追加）は、着手適用の
前に移動先マスを読めば取得できるため、この関数には持たせない。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.move import Move
from shogi.movegen import generate_piece_moves
from shogi.piece import Color, Piece, PieceType

# 成る前の駒種 → 成った後の駒種。board_after_move で is_promotion=True の手を
# 適用する際に使う。金・玉・成駒6種は成れないので含めない（movegen はそれらの
# 成り手を生成しないため通常は到達しないが、渡された場合は不正な手として弾く）。
_PROMOTED_TYPE = {
    PieceType.PAWN: PieceType.PROMOTED_PAWN,
    PieceType.LANCE: PieceType.PROMOTED_LANCE,
    PieceType.KNIGHT: PieceType.PROMOTED_KNIGHT,
    PieceType.SILVER: PieceType.PROMOTED_SILVER,
    PieceType.BISHOP: PieceType.HORSE,
    PieceType.ROOK: PieceType.DRAGON,
}


def board_after_move(board: Board, move: Move) -> Board:
    """`move` を指した後の盤面を、元の盤面を壊さずに新しく作って返す。

    移動先に相手駒があれば取り（盤から除去するだけで持ち駒には加えない。
    持ち駒は SHOGI-4 の責務）。move.is_promotion が True なら、移動する駒を
    成った駒種に置き換える。

    「この手を指すと自玉が王手になるか」を調べるためのシミュレート専用。
    手番の正当性・成れる位置かどうかは検証しない（movegen が生成した疑似
    合法手を渡すことを前提とする）。

    移動元が空きマスの場合、または成れない駒種の手に is_promotion=True が
    指定された場合は ValueError を送出する。
    """
    piece = board.get_piece(move.from_file, move.from_rank)
    if piece is None:
        raise ValueError(f"移動元 ({move.from_file}, {move.from_rank}) は空きマスです")

    moved = piece
    if move.is_promotion:
        promoted_type = _PROMOTED_TYPE.get(piece.piece_type)
        if promoted_type is None:
            raise ValueError(f"成れない駒種です: {piece.piece_type}")
        moved = Piece(piece.color, promoted_type)

    next_board = board.copy()
    next_board.set_piece(move.from_file, move.from_rank, None)
    # 移動先に相手駒があれば上書き＝取り（味方駒のマスへは movegen が手を作らない）
    next_board.set_piece(move.to_file, move.to_rank, moved)
    return next_board


def find_king(board: Board, color: Color) -> tuple[int, int] | None:
    """color の玉の座標 (file, rank) を返す。盤上に無ければ None を返す。

    王手判定の起点。通常の対局では両者の玉が常に盤上にあるが、駒落ちや
    途中局面のフィクスチャでは無いこともあるため、None を返せるようにする。
    """
    for rank in range(1, BOARD_SIZE + 1):
        for file in range(1, BOARD_SIZE + 1):
            piece = board.get_piece(file, rank)
            if (
                piece is not None
                and piece.color is color
                and piece.piece_type is PieceType.KING
            ):
                return (file, rank)
    return None


def is_attacked(board: Board, file: int, rank: int, by_color: Color) -> bool:
    """(file, rank) が by_color の駒に攻撃されているかを返す。

    by_color の各駒の疑似合法手（movegen.generate_piece_moves）の着地点に
    (file, rank) が含まれるかで判定する。将棋は「動ける先＝利き」なので、
    攻撃判定専用のロジックを別に作らず疑似合法手の生成を流用できる。
    走り駒の遮断・桂の跳び越えも generate_piece_moves 側が正しく扱う。
    成り込みで着地点が重複しても、含まれるか否かの判定には影響しない。
    """
    for f in range(1, BOARD_SIZE + 1):
        for r in range(1, BOARD_SIZE + 1):
            piece = board.get_piece(f, r)
            if piece is None or piece.color is not by_color:
                continue
            for move in generate_piece_moves(board, f, r):
                if move.to_file == file and move.to_rank == rank:
                    return True
    return False


def is_in_check(board: Board, color: Color) -> bool:
    """color の玉が王手されているかを返す。玉が盤上に無ければ False を返す。"""
    king_square = find_king(board, color)
    if king_square is None:
        return False
    king_file, king_rank = king_square
    opponent = Color.WHITE if color is Color.BLACK else Color.BLACK
    return is_attacked(board, king_file, king_rank, opponent)
