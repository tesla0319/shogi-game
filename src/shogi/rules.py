"""合法手判定の基盤（SHOGI-3）。

疑似合法手の生成（movegen）とは別の責務。SHOGI-3a で「ある手を指した後の
盤面」を作るシミュレート（board_after_move）、SHOGI-3b で王手検出
（find_king / is_attacked / is_in_check）、SHOGI-3c で合法手の確定
（generate_legal_moves）を提供する。

駒打ちは SHOGI-4 で position_after_move（着手適用）と generate_legal_moves
（合法手への統合）が扱う。ただし駒取りに伴う持ち駒への加算はここでは行わない
（取った駒は盤から除去するだけ）。取った駒種が必要な処理（持ち駒への追加）は、
着手適用の前に移動先マスを読めば取得できるため、これらの関数には持たせない。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.hand import Hand
from shogi.move import Move
from shogi.movegen import generate_drop_moves, generate_piece_moves
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

# 取った駒を持ち駒に加えるときの駒種変換（成駒 → 素の駒）。_PROMOTED_TYPE の逆写像。
# 成って取られた駒（と金・成香…）は素の駒（歩・香…）として持ち駒に入る連盟ルール用。
# 素の駒種（歩・金・角など）は変換不要なので、参照時は .get のデフォルトで自分自身を
# 返す（この辞書には成駒6種だけを入れておく）。玉は持ち駒にできないので別途弾く。
_UNPROMOTED_TYPE = {promoted: base for base, promoted in _PROMOTED_TYPE.items()}


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


def position_after_move(
    board: Board, hand: Hand, color: Color, move: Move
) -> tuple[Board, Hand]:
    """`move`（盤上移動または駒打ち）を指した後の (盤面, 手番 color の持ち駒) を、
    元の board / hand を壊さずに新しく作って返す。

    盤上移動（move.is_drop が False）のときは盤面更新を board_after_move に委譲し、
    移動先に相手駒があればそれを取って color の持ち駒に加える。取った駒が成駒
    （と金・成香・成桂・成銀・馬・竜）なら素の駒（歩・香・桂・銀・角・飛）として
    加える。玉を取った場合は持ち駒に加えない（持ち駒にできないため）。
    駒打ち（move.is_drop が True）のときは、打つ駒種を color の駒として
    move.to_file / move.to_rank に置き、hand から1枚減らす。

    Position 概念は導入せず、手番は color 引数で受け取る。合法性（持ち駒が足りるか・
    打つ先が空か・二歩・行き所のない駒・打ち歩詰め・王手放置）はここでは検証しない。
    持ち駒が0枚の駒種を打つ手を渡した場合のみ、Hand.remove が ValueError を送出する。
    """
    if not move.is_drop:
        # 盤面更新は既存関数に委譲。取った駒の判定は「適用前の移動先マス」を読む
        # （board_after_move 適用後は上書き済みで取った駒が分からなくなるため）。
        next_board = board_after_move(board, move)
        next_hand = hand.copy()
        captured = board.get_piece(move.to_file, move.to_rank)
        if captured is not None and captured.piece_type is not PieceType.KING:
            # 成駒は素の駒に戻して加える。素の駒種はそのまま（.get のデフォルト）
            base_type = _UNPROMOTED_TYPE.get(captured.piece_type, captured.piece_type)
            next_hand.add(base_type)
        return next_board, next_hand

    next_board = board.copy()
    next_hand = hand.copy()
    dropped = Piece(color, move.drop_piece_type)
    next_board.set_piece(move.to_file, move.to_rank, dropped)
    next_hand.remove(move.drop_piece_type)
    return next_board, next_hand


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


def _is_uchifuzume(board_after_drop: Board, move: Move, color: Color) -> bool:
    """歩打ち move が相手玉を詰ませている（打ち歩詰め＝反則）かを返す。

    打ち歩詰めは「歩を打って相手を詰ます」ことのみを禁じる反則。歩以外の打ち・
    盤上移動は対象外なので、まず「歩打ちか」で早期に False を返す。歩打ちでも、
    相手玉が王手でなければ詰みではないので False。王手のときだけ相手に回避手が
    あるかを調べ、1つも無ければ打ち歩詰めと判定する。

    MVP の割り切り: 相手の回避手は「盤上移動のみ」で判定する（generate_legal_moves を
    hand なしで呼ぶ）。相手の持ち駒による合駒は、着手後の正確な持ち駒管理が未実装の
    ため今回は網羅しない。この分だけ判定は「打ち歩詰めと見なしすぎる」側に倒れうる。
    """
    if not (move.is_drop and move.drop_piece_type is PieceType.PAWN):
        return False

    opponent = Color.WHITE if color is Color.BLACK else Color.BLACK
    if not is_in_check(board_after_drop, opponent):
        return False  # そもそも王手でなければ詰みではない

    # 相手の回避手を数える。check_uchifuzume=False で「相手の応手の打ち歩詰め判定」を
    # 止め、無限再帰を防ぐ（回避手が1つでもあれば打ち歩詰めではない）。
    escapes = generate_legal_moves(
        board_after_drop, opponent, check_uchifuzume=False
    )
    return len(escapes) == 0


def generate_legal_moves(
    board: Board,
    color: Color,
    hand: Hand | None = None,
    *,
    check_uchifuzume: bool = True,
) -> list[Move]:
    """color の合法手を返す。hand を渡すと駒打ちの合法手も含める。

    盤上移動: 盤上の color の各駒の疑似合法手（movegen.generate_piece_moves、
    成り込み）から、指した後に自玉が王手になる手を除外する。「指した後に王手か」の
    単一フィルタで、王手放置・自殺手・ピンによる自己王手をまとめて除外する（王手中か
    どうかで処理を分けない）。王手駒を取る手・合駒で遮る手は王手が解消されるので残る。

    駒打ち: hand が None のときは生成しない（従来どおり盤上移動のみ。既存の呼び出しと
    完全互換にするためのデフォルト）。hand を渡したときは generate_drop_moves の各手
    （二歩・行き所のない駒は生成側で除外済み）を、打った後に自玉が王手になる手と、
    歩打ちのうち打ち歩詰めになる手を除外する。

    check_uchifuzume は打ち歩詰め判定の内部制御用。通常は True。打ち歩詰め判定は
    相手の回避手を generate_legal_moves で数える（再帰する）ため、その相手側の呼び出しでは
    False にして再帰を1段で止める（相手の応手がさらに打ち歩詰めかは問わないでよい）。

    戻り値は Move の列挙のみで、持ち駒の状態は含めない。駒取りに伴う持ち駒への加算や
    着手後の持ち駒は position_after_move が別途返すため、この関数は持たせない。
    手番は color、持ち駒は hand 引数で受け取り、Position 概念は導入しない。
    """
    legal = []
    for rank in range(1, BOARD_SIZE + 1):
        for file in range(1, BOARD_SIZE + 1):
            piece = board.get_piece(file, rank)
            if piece is None or piece.color is not color:
                continue
            for move in generate_piece_moves(board, file, rank):
                next_board = board_after_move(board, move)
                if not is_in_check(next_board, color):
                    legal.append(move)

    # hand 未指定なら駒打ちは一切生成しない（従来挙動を1バイトも変えない）
    if hand is not None:
        for move in generate_drop_moves(board, hand, color):
            # 打った後の盤面だけで王手判定する。position_after_move は次の持ち駒も
            # 返すが、合法手列挙では使わない（戻り値に持ち駒を含めないため破棄する）
            next_board, _ = position_after_move(board, hand, color, move)
            if is_in_check(next_board, color):
                continue  # 自玉が王手になる駒打ち（王手放置）は除外
            if check_uchifuzume and _is_uchifuzume(next_board, move, color):
                continue  # 打ち歩詰めは反則なので除外
            legal.append(move)

    return legal
