"""駒の疑似合法手の生成（SHOGI-2 / 駒打ち候補は SHOGI-4）。

盤上の全14駒種（基本8種 + 成駒6種）と成り/不成の候補に対応。持ち駒からの
駒打ち候補は generate_drop_moves が空きマスへの Move.drop として生成する。

疑似合法手 = 駒の動きとして可能な移動先のうち、盤外と味方駒のあるマスを
除いたもの。盤上移動については王手放置などの反則除外（合法手判定）は SHOGI-3 の
責務のため、ここでは行わない。駒打ち候補は二歩・行き所のない駒までは除外するが、
打ち歩詰め・王手放置は判定しない（後続の責務）。

成り候補は駒種ごとの generate_*_moves ではなく、ディスパッチャ
generate_piece_moves が _expand_promotions で付与する。駒の動きのパターンと
成りの規則を別の責務として分け、成りロジックを1箇所に集約するため。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.hand import Hand
from shogi.move import Move
from shogi.piece import Color, Piece, PieceType

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

    # 前方向1本の走り。停止規則は他の走り駒と共通
    return _sliding_moves(board, file, rank, piece.color, [(0, _FORWARD[piece.color])])


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


def generate_horse_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの馬（角の成り）の疑似合法手を返す。

    動きは「角の走り（斜め4方向）」+「縦横4方向への1マス」。
    走り部分の停止規則は角と同じ。1マス部分は盤外と味方駒のマスを除外する。
    候補は「斜めの走り → 縦横の1マス」の順に並ぶ。
    指定マスが空きマス、または馬以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.HORSE:
        raise ValueError(f"({file}, {rank}) に馬がありません: {piece!r}")

    # 縦横1マスのオフセットは飛車の走り方向と同じタプルなので定数を共用する
    return _sliding_moves(
        board, file, rank, piece.color, _BISHOP_DIRECTIONS
    ) + _step_moves(board, file, rank, piece.color, _ROOK_DIRECTIONS)


def generate_dragon_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの竜（飛車の成り）の疑似合法手を返す。

    動きは「飛車の走り（縦横4方向）」+「斜め4方向への1マス」。
    走り部分の停止規則は飛車と同じ。1マス部分は盤外と味方駒のマスを除外する。
    候補は「縦横の走り → 斜めの1マス」の順に並ぶ。
    指定マスが空きマス、または竜以外の駒の場合は ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None or piece.piece_type is not PieceType.DRAGON:
        raise ValueError(f"({file}, {rank}) に竜がありません: {piece!r}")

    # 斜め1マスのオフセットは角の走り方向と同じタプルなので定数を共用する
    return _sliding_moves(
        board, file, rank, piece.color, _ROOK_DIRECTIONS
    ) + _step_moves(board, file, rank, piece.color, _BISHOP_DIRECTIONS)


# 成れる駒種。金・玉と成駒6種は成れない
_PROMOTABLE_TYPES = {
    PieceType.PAWN,
    PieceType.LANCE,
    PieceType.KNIGHT,
    PieceType.SILVER,
    PieceType.BISHOP,
    PieceType.ROOK,
}

# 不成だと行き所がなくなる駒種 → 最奥から数えた段数（歩・香=1段、桂=2段）。
# 3分岐をベタ書きせず「不成だと動けなくなる深さ」という1つの概念に揃えるため辞書にする
_DEAD_END_DEPTH = {
    PieceType.PAWN: 1,
    PieceType.LANCE: 1,
    PieceType.KNIGHT: 2,
}


def _in_promotion_zone(color: Color, rank: int) -> bool:
    """敵陣（先手は rank 1〜3、後手は rank 7〜9）かどうかを返す。"""
    if color is Color.BLACK:
        return rank <= 3
    return rank >= BOARD_SIZE - 2  # 7〜9


def _must_promote(piece_type: PieceType, color: Color, to_rank: int) -> bool:
    """不成だと行き所がなくなる移動先か（= 強制成りか）を返す。

    強制成りになる移動先は必ず敵陣内なので、成り可能かどうかの判定を
    済ませた手に対して to_rank だけ見れば十分（from_rank は不要）。
    """
    depth = _DEAD_END_DEPTH.get(piece_type)
    if depth is None:
        return False  # 銀・角・飛は最奥でも不成のまま動けるので強制されない
    if color is Color.BLACK:
        return to_rank <= depth
    return to_rank >= BOARD_SIZE + 1 - depth


def _expand_promotions(piece: Piece, moves: list[Move]) -> list[Move]:
    """疑似合法手のリストに成り候補を付与する後処理。

    成りは「成れる駒種で、移動元または移動先が敵陣」のとき選べる。
    移動元基準を含めるのは、敵陣内から敵陣外へ引く手でも成れるという
    連盟ルールに合わせるため。走り駒は1回の生成で敵陣内外の両方に
    移動先を持ちうるので、リスト単位ではなく手単位で判定する。

    成れない手はそのまま1件、任意成りは [不成, 成] の2件（不成が先）、
    強制成り（歩・香の最終段、桂の奥2段）は成のみ1件に展開する。
    「行き所のない駒」の反則チェック（SHOGI-3）は駒打ちのみを対象とし、
    盤上の移動の強制成りはこの関数が担う。
    """
    expanded = []
    for move in moves:
        can_promote = piece.piece_type in _PROMOTABLE_TYPES and (
            _in_promotion_zone(piece.color, move.from_rank)
            or _in_promotion_zone(piece.color, move.to_rank)
        )
        if not can_promote:
            expanded.append(move)
            continue
        promotion = Move(
            move.from_file,
            move.from_rank,
            move.to_file,
            move.to_rank,
            is_promotion=True,
        )
        if _must_promote(piece.piece_type, piece.color, move.to_rank):
            expanded.append(promotion)  # 不成は候補に含めない
        else:
            expanded.append(move)
            expanded.append(promotion)
    return expanded


# 駒種 → 疑似合法手の生成関数。全14駒種を網羅する
_MOVE_GENERATORS = {
    PieceType.PAWN: generate_pawn_moves,
    PieceType.LANCE: generate_lance_moves,
    PieceType.KNIGHT: generate_knight_moves,
    PieceType.SILVER: generate_silver_moves,
    PieceType.GOLD: generate_gold_moves,
    PieceType.BISHOP: generate_bishop_moves,
    PieceType.ROOK: generate_rook_moves,
    PieceType.KING: generate_king_moves,
    PieceType.PROMOTED_PAWN: generate_promoted_pawn_moves,
    PieceType.PROMOTED_LANCE: generate_promoted_lance_moves,
    PieceType.PROMOTED_KNIGHT: generate_promoted_knight_moves,
    PieceType.PROMOTED_SILVER: generate_promoted_silver_moves,
    PieceType.HORSE: generate_horse_moves,
    PieceType.DRAGON: generate_dragon_moves,
}


def generate_piece_moves(board: Board, file: int, rank: int) -> list[Move]:
    """指定マスの駒の疑似合法手を、成り/不成の候補込みで返す。

    呼び出し側が駒種で分岐しなくて済むようにするためのディスパッチャ。
    合法手判定（SHOGI-3）で相手の全駒の利きを列挙する際もここを使う。
    駒種ごとの generate_*_moves は成り候補を含まない（動きのパターンのみ）
    ため、疑似合法手の列挙には専用関数ではなくこの関数を使うこと。
    指定マスが空きマスの場合、または対応する生成関数がない駒種の場合は
    ValueError を送出する。
    """
    piece = board.get_piece(file, rank)
    if piece is None:
        raise ValueError(f"({file}, {rank}) は空きマスです")
    generator = _MOVE_GENERATORS.get(piece.piece_type)
    if generator is None:
        raise ValueError(f"未対応の駒種です: {piece.piece_type}")
    return _expand_promotions(piece, generator(board, file, rank))


# 打てる駒種の列挙順。持ち駒にできる基本7種を PieceType の定義順で固定し、
# 生成される駒打ち候補の並びを決定的にする（Hand の内部は順序を持たない集合のため、
# hand を走査すると順序が不定になる）。
_DROPPABLE_TYPES = (
    PieceType.PAWN,
    PieceType.LANCE,
    PieceType.KNIGHT,
    PieceType.SILVER,
    PieceType.GOLD,
    PieceType.BISHOP,
    PieceType.ROOK,
)


def _has_own_unpromoted_pawn(board: Board, color: Color, file: int) -> bool:
    """指定ファイルに color の未成の歩があるか（二歩判定用）。

    二歩の対象は「未成の歩」のみ。と金（PROMOTED_PAWN）は歩ではないので数えず、
    相手の歩も自分の二歩には関係しないため、color 一致かつ PAWN のみを数える。
    """
    for rank in range(1, BOARD_SIZE + 1):
        piece = board.get_piece(file, rank)
        if (
            piece is not None
            and piece.color is color
            and piece.piece_type is PieceType.PAWN
        ):
            return True
    return False


def _can_drop_on(
    board: Board, piece_type: PieceType, color: Color, file: int, rank: int
) -> bool:
    """(file, rank) へ piece_type を打てるか（二歩・行き所のない駒の除外）を返す。

    - 行き所のない駒: 打った先で二度と動けない段には打てない。駒打ちは成って
      打てないので「盤上移動なら強制成りになる段（_must_promote）＝打てない段」と
      一致する。深さ規則（歩香=最奥1段・桂=最奥2段）を1箇所に保つため流用する。
    - 二歩: 歩を打つとき、同じファイルに自分の未成の歩があれば打てない。

    打ち歩詰め・王手放置は本フェーズ対象外（判定しない）。
    """
    if _must_promote(piece_type, color, rank):
        return False
    if piece_type is PieceType.PAWN and _has_own_unpromoted_pawn(board, color, file):
        return False
    return True


def generate_drop_moves(board: Board, hand: Hand, color: Color) -> list[Move]:
    """color 側が hand の持ち駒を空きマスへ打つ疑似合法手（駒打ち候補）を返す。

    持ち駒のある駒種それぞれについて、盤上の空きマスのうち二歩・行き所のない駒に
    ならないマスへの Move.drop を作る。同じ駒を複数枚持っていても、1マスにつき
    候補は1つ（打つのは1枚なので枚数分は増やさない）。生成順は _DROPPABLE_TYPES の
    順 × (rank 昇順, file 昇順)。

    除外する反則は二歩と行き所のない駒のみ。打ち歩詰め・王手放置は判定しない
    （後続の責務）。手番 color は二歩（自分の歩か）と行き所（先後で禁段が反転）の
    判定に使う。
    """
    moves = []
    for piece_type in _DROPPABLE_TYPES:
        # 枚数は「打てるか否か（1枚以上か）」だけ見る。候補数は枚数に依らない
        if hand.count(piece_type) == 0:
            continue
        for rank in range(1, BOARD_SIZE + 1):
            for file in range(1, BOARD_SIZE + 1):
                if board.get_piece(file, rank) is not None:
                    continue  # 空きマスにしか打てない
                if not _can_drop_on(board, piece_type, color, file, rank):
                    continue  # 二歩・行き所のない駒を除外
                moves.append(Move.drop(piece_type, file, rank))
    return moves
