"""局面のテキスト表示（SHOGI-4j）。

盤面・両者の持ち駒・手番を、人間がターミナルで読める1つの文字列に変換する。
CLI 対局で現局面を表示するための表示専用モジュールで、print などの副作用は持たず、
同じ局面なら常に同じ文字列を返す純関数として実装する（テスト可能性のため）。

駒の文字表現は SFEN（sfen.py）に合わせる:
- 大文字＝先手、小文字＝後手。成駒は先頭に "+"（と金＝+P、馬＝+B など）
- 空きマスは "."
これにより ASCII で等幅に整列でき、テストで文字列を厳密に照合できる。sfen.py の
内部辞書は使わず、表示用に必要な形（2文字固定のセル）で display.py に独立して持つ。

盤の向きは先手視点固定（先手が下・後手が上、右端が1筋）。手番によって盤を反転する
表示は MVP では行わない（対局ループの表示要件が固まってから判断する）。
"""

from shogi.board import BOARD_SIZE, Board
from shogi.hand import Hand
from shogi.piece import Color, Piece, PieceType

# 駒種 → 盤マス表示の2文字トークン（先手＝大文字の形）。成駒は先頭 "+"、非成駒は先頭空白で
# 幅を2に揃える。後手は .lower() で小文字化する（"+" は小文字化しても変わらない）。
# 全マスを幅2にすることで、成駒（+P）が混じっても筋ヘッダと桁がずれない。
_CELL_TOKENS = {
    PieceType.PAWN: " P",
    PieceType.LANCE: " L",
    PieceType.KNIGHT: " N",
    PieceType.SILVER: " S",
    PieceType.GOLD: " G",
    PieceType.BISHOP: " B",
    PieceType.ROOK: " R",
    PieceType.KING: " K",
    PieceType.PROMOTED_PAWN: "+P",
    PieceType.PROMOTED_LANCE: "+L",
    PieceType.PROMOTED_KNIGHT: "+N",
    PieceType.PROMOTED_SILVER: "+S",
    PieceType.HORSE: "+B",
    PieceType.DRAGON: "+R",
}

# 空きマスの2文字トークン（先頭空白 + "."）。駒トークンと同じ幅で桁を揃える。
_EMPTY_CELL = " ."

# 段番号 1〜9 → 段ラベル（USI と同じ a〜i）。盤の各行の右端に付けて段を示す。
_RANK_LABELS = "abcdefghi"

# 持ち駒の表示順。将棋で慣用の「飛 角 金 銀 桂 香 歩」の順に並べる。
# 表示順を実装から切り離して読みやすくするため定数化する。
_HAND_ORDER = [
    PieceType.ROOK,
    PieceType.BISHOP,
    PieceType.GOLD,
    PieceType.SILVER,
    PieceType.KNIGHT,
    PieceType.LANCE,
    PieceType.PAWN,
]

# 手番 → 表示ラベル。
_COLOR_LABELS = {Color.BLACK: "先手", Color.WHITE: "後手"}


def position_to_text(
    board: Board, black_hand: Hand, white_hand: Hand, side_to_move: Color
) -> str:
    """局面（盤面・両者の持ち駒・手番）を人間可読な1つの文字列にして返す。

    Position 概念は導入せず、盤面・先手持ち駒・後手持ち駒・手番を明示的な引数で受け取る。
    出力は改行区切りで、上から「後手持ち駒 → 盤面（後手が上・先手が下）→ 先手持ち駒 →
    手番」の順に並べる。print はせず文字列を返すだけ（表示先は呼び出し側が決める）。
    """
    lines = [f"後手持ち駒: {_format_hand(white_hand)}"]
    lines.append(_format_file_header())
    for rank in range(1, BOARD_SIZE + 1):
        lines.append(_format_rank_row(board, rank))
    lines.append(f"先手持ち駒: {_format_hand(black_hand)}")
    lines.append(f"手番: {_COLOR_LABELS[side_to_move]}")
    return "\n".join(lines)


def _format_file_header() -> str:
    """筋番号のヘッダ行（9〜1）を返す。各筋を幅2にして盤マスと桁を揃える。"""
    return "".join(f"{file:>2}" for file in range(BOARD_SIZE, 0, -1))


def _format_rank_row(board: Board, rank: int) -> str:
    """1段分の行（各マスの2文字トークン + 右端に段ラベル）を返す。

    筋は SFEN と同じく 9 から 1 の順に左から並べる。
    """
    cells = "".join(
        _format_cell(board.get_piece(file, rank))
        for file in range(BOARD_SIZE, 0, -1)
    )
    return f"{cells} {_RANK_LABELS[rank - 1]}"


def _format_cell(piece: Piece | None) -> str:
    """1マスの2文字トークンを返す。空マスは " ."、先手は大文字・後手は小文字。"""
    if piece is None:
        return _EMPTY_CELL
    token = _CELL_TOKENS[piece.piece_type]
    return token if piece.color is Color.BLACK else token.lower()


def _format_hand(hand: Hand) -> str:
    """持ち駒を "R B2 P3" のような文字列にして返す。持ち駒が無ければ "なし"。

    駒種は _HAND_ORDER の順に並べ、枚数が2枚以上のときだけ駒文字の後ろに枚数を付ける
    （1枚は駒文字のみ。将棋の「歩」「歩二」のような慣用に合わせて読みやすくする）。
    """
    parts = []
    for piece_type in _HAND_ORDER:
        count = hand.count(piece_type)
        if count == 0:
            continue
        letter = _CELL_TOKENS[piece_type].strip()  # " R" → "R"（持ち駒は非成駒のみ）
        parts.append(letter if count == 1 else f"{letter}{count}")
    return " ".join(parts) if parts else "なし"
