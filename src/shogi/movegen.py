"""駒の疑似合法手の生成（SHOGI-2）。

基本8駒種（歩・香・桂・銀・金・玉・飛・角）と金系成駒4種
（と金・成香・成桂・成銀）に対応。馬・竜・成り候補・駒打ちは未対応。

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


def _sliding_moves(
    board: Board,
    file: int,
    rank: int,
    color: Color,
    directions: list[tuple[int, int]],
) -> list[Move]:
    """走り駒の候補を返す。方向ごとに遮られるまで進む（各方向とも近い順）。

    それぞれの方向 (file差分, rank差分) について、盤外に出る手前で停止する。
    味方駒の手前で停止し、そのマスは含めない。相手駒のマスで停止し、
    そのマスは含める（取る手になる）。香車の走りと同じ規則の多方向版。
    """
    moves = []
    for dfile, drank in directions:
        to_file, to_rank = file + dfile, rank + drank
        while 1 <= to_file <= BOARD_SIZE and 1 <= to_rank <= BOARD_SIZE:
            target = board.get_piece(to_file, to_rank)
            if target is not None and target.color is color:
                break  # 味方駒の手前で停止（そのマスは含めない）
            moves.append(Move(file, rank, to_file, to_rank))
            if target is not None:
                break  # 相手駒のマスで停止（そのマスまでは含める）
            to_file += dfile
            to_rank += drank
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


def _gold_like_moves(board: Board, file: int, rank: int, color: Color) -> list[Move]:
    """金と同じ6方向（前・前斜め左右・横左右・真後ろ）の候補を返す。

    金将と、金と同じ動きをする成駒4種（と金・成香・成桂・成銀）で共用する。
    駒種チェックは呼び出し側の各 generate_*_moves が行う。
    """
    forward = _FORWARD[color]
    # 前の3マス（file の小さい側から）→ 横の2マス → 真後ろ
    offsets = [
        (-1, forward),
        (0, forward),
        (+1, forward),
        (-1, 0),
        (+1, 0),
        (0, -forward),
    ]
    return _step_moves(board, file, rank, color, offsets)


def generate_gold_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの金将の疑似合法手を返す。

    動ける方向は6つ: 前・前斜め左右・横左右・真後ろ（後ろ斜めには動けない）。
    盤外と味方駒のあるマスは候補に含めない（空きマスと相手駒のマスは含める）。
    指定マスが空きマス、または金将以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.GOLD:
        raise ValueError(f"({file}, {rank}) に金将がありません: {piece!r}")

    return _gold_like_moves(board, file, rank, piece.color)


# 玉将の8方向。全方向対称で手番に依存しないため、file の小さい側から順の固定リスト
_KING_OFFSETS = [
    (-1, -1),
    (-1, 0),
    (-1, +1),
    (0, -1),
    (0, +1),
    (+1, -1),
    (+1, 0),
    (+1, +1),
]


def generate_king_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの玉将の疑似合法手を返す。

    隣接する8方向へ1マス動ける（全方向対称のため先手・後手で同じ）。
    盤外と味方駒のあるマスは候補に含めない（空きマスと相手駒のマスは含める）。
    相手の利きがあるマスへの移動（自殺手）もここでは候補に含める。
    その除外は合法手判定（SHOGI-3）の責務。
    指定マスが空きマス、または玉将以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.KING:
        raise ValueError(f"({file}, {rank}) に玉将がありません: {piece!r}")

    return _step_moves(board, file, rank, piece.color, _KING_OFFSETS)


# 飛車の走り4方向。縦（rank の小さい側 → 大きい側）→ 横（file の小さい側 → 大きい側）
_ROOK_DIRECTIONS = [(0, -1), (0, +1), (-1, 0), (+1, 0)]


def generate_rook_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの飛車の疑似合法手を返す。

    縦横4方向へ、盤端または駒に当たるまで進める（全方向対称のため
    先手・後手で同じ）。味方駒の手前で停止し、そのマスは含めない。
    相手駒のマスで停止し、そのマスは含める（その先へは進めない）。
    指定マスが空きマス、または飛車以外の駒の場合は ValueError を送出する。
    成って竜になった後の動きは成駒対応の Phase で扱う。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.ROOK:
        raise ValueError(f"({file}, {rank}) に飛車がありません: {piece!r}")

    return _sliding_moves(board, file, rank, piece.color, _ROOK_DIRECTIONS)


# 角行の走り4方向（斜め）。file の小さい側から、同じ file 側では rank の小さい側から
_BISHOP_DIRECTIONS = [(-1, -1), (-1, +1), (+1, -1), (+1, +1)]


def generate_bishop_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの角行の疑似合法手を返す。

    斜め4方向へ、盤端または駒に当たるまで進める（全方向対称のため
    先手・後手で同じ）。味方駒の手前で停止し、そのマスは含めない。
    相手駒のマスで停止し、そのマスは含める（その先へは進めない）。
    指定マスが空きマス、または角行以外の駒の場合は ValueError を送出する。
    成って馬になった後の動きは成駒対応の Phase で扱う。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.BISHOP:
        raise ValueError(f"({file}, {rank}) に角行がありません: {piece!r}")

    return _sliding_moves(board, file, rank, piece.color, _BISHOP_DIRECTIONS)


def generate_promoted_pawn_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスのと金の疑似合法手を返す。動きは金将と同じ6方向。

    指定マスが空きマス、またはと金以外の駒（金将や歩を含む）の場合は
    ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PROMOTED_PAWN:
        raise ValueError(f"({file}, {rank}) にと金がありません: {piece!r}")

    return _gold_like_moves(board, file, rank, piece.color)


def generate_promoted_lance_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの成香の疑似合法手を返す。動きは金将と同じ6方向。

    指定マスが空きマス、または成香以外の駒（金将や香車を含む）の場合は
    ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PROMOTED_LANCE:
        raise ValueError(f"({file}, {rank}) に成香がありません: {piece!r}")

    return _gold_like_moves(board, file, rank, piece.color)


def generate_promoted_knight_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの成桂の疑似合法手を返す。動きは金将と同じ6方向。

    指定マスが空きマス、または成桂以外の駒（金将や桂馬を含む）の場合は
    ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PROMOTED_KNIGHT:
        raise ValueError(f"({file}, {rank}) に成桂がありません: {piece!r}")

    return _gold_like_moves(board, file, rank, piece.color)


def generate_promoted_silver_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの成銀の疑似合法手を返す。動きは金将と同じ6方向。

    指定マスが空きマス、または成銀以外の駒（金将や銀将を含む）の場合は
    ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.PROMOTED_SILVER:
        raise ValueError(f"({file}, {rank}) に成銀がありません: {piece!r}")

    return _gold_like_moves(board, file, rank, piece.color)
