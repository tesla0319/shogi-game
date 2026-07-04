"""SFEN 表記の入出力。

このモジュールに SFEN 関連の変換を集約する（Board は表記を知らないままにする）。
現在は「盤面部」の出力（board_to_sfen）と読み込み（board_from_sfen）のみ。
手番・持ち駒・手数を含む完全な SFEN は Position 概念の導入後に扱う。

SFEN 盤面部の規則:
- 段（rank）1 から 9 の順に、各段を "/" で区切って並べる
- 各段の中は file=9（先手から見て左端）から file=1 の順に書く
- 駒は1文字（歩=P 香=L 桂=N 銀=S 金=G 角=B 飛=R 玉=K）。
  先手は大文字・後手は小文字。成駒は頭に "+" を付ける（と金=+P、馬=+b など）
- 連続する空きマスはその個数の数字1文字に圧縮する（例: 空きマス5個 → "5"）
"""

from shogi.board import BOARD_SIZE, Board
from shogi.piece import Color, Piece, PieceType

# 駒種 → SFEN 文字（先手側・大文字）。後手は小文字に変換して使う
_SFEN_LETTERS = {
    PieceType.PAWN: "P",
    PieceType.LANCE: "L",
    PieceType.KNIGHT: "N",
    PieceType.SILVER: "S",
    PieceType.GOLD: "G",
    PieceType.BISHOP: "B",
    PieceType.ROOK: "R",
    PieceType.KING: "K",
    PieceType.PROMOTED_PAWN: "+P",
    PieceType.PROMOTED_LANCE: "+L",
    PieceType.PROMOTED_KNIGHT: "+N",
    PieceType.PROMOTED_SILVER: "+S",
    PieceType.HORSE: "+B",
    PieceType.DRAGON: "+R",
}


# SFEN 文字 → 駒種（_SFEN_LETTERS の逆引き）
_LETTER_TO_PIECE_TYPE = {letter: piece_type for piece_type, letter in _SFEN_LETTERS.items()}

# 空きマス数として許す文字。str.isdigit() は全角数字（"５" など）も True になるため使わない
_EMPTY_COUNT_DIGITS = "123456789"


def board_to_sfen(board: Board) -> str:
    """盤面を SFEN の盤面部の文字列にして返す。

    盤面部のみを返す（手番・持ち駒・手数は含めない）。
    例: 平手初期局面 → "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL"
    """
    rows = []
    for rank in range(1, BOARD_SIZE + 1):
        rows.append(_rank_to_sfen(board, rank))
    return "/".join(rows)


def _rank_to_sfen(board: Board, rank: int) -> str:
    """1つの段を SFEN の1行分（空きマス圧縮済み）にして返す。"""
    row = ""
    empty_count = 0
    for file in range(BOARD_SIZE, 0, -1):  # file=9 から 1 の順
        piece = board.get_piece(file, rank)
        if piece is None:
            empty_count += 1
            continue
        if empty_count > 0:
            row += str(empty_count)
            empty_count = 0
        letter = _SFEN_LETTERS[piece.piece_type]
        row += letter if piece.color is Color.BLACK else letter.lower()
    if empty_count > 0:  # 段の末尾（file=1 側）が空きマスで終わる場合
        row += str(empty_count)
    return row


def board_from_sfen(sfen: str) -> Board:
    """SFEN の盤面部の文字列から Board を復元して返す。

    盤面部のみを受け取る（手番・持ち駒・手数を含む完全な SFEN は対象外）。
    不正な入力は ValueError を送出する:
    - "/" 区切りの段数が9でない
    - 1つの段のマス数（駒 + 空きマス数の合計）が9でない
    - 許可されていない文字（駒文字・1〜9・"+" 以外、"0"、成れない駒への "+" など）
    """
    rows = sfen.split("/")
    if len(rows) != BOARD_SIZE:
        raise ValueError(f"段数が{BOARD_SIZE}ではありません: {len(rows)}段 ({sfen!r})")
    board = Board()
    for rank, row in enumerate(rows, start=1):
        _parse_rank_into(board, rank, row)
    return board


def _parse_rank_into(board: Board, rank: int, row: str) -> None:
    """SFEN の1段分の文字列を解釈し、board の rank 段目に駒を配置する。"""
    file = BOARD_SIZE  # file=9（段の先頭）から 1 に向かって埋めていく
    i = 0
    while i < len(row):
        char = row[i]
        if char in _EMPTY_COUNT_DIGITS:
            file -= int(char)  # 空きマスはスキップ（Board の初期値が None のため）
            i += 1
            continue
        if char == "+":
            letter = row[i : i + 2]  # "+P" のような2文字で1駒
            i += 2
        else:
            letter = char
            i += 1
        piece_type = _LETTER_TO_PIECE_TYPE.get(letter.upper())
        if piece_type is None:
            raise ValueError(f"{rank}段目に不正な文字があります: {letter!r} ({row!r})")
        if file < 1:
            raise ValueError(f"{rank}段目のマス数が{BOARD_SIZE}を超えています: {row!r}")
        # 駒の手番は文字の大小で決まる（大文字=先手、小文字=後手）
        color = Color.BLACK if letter[-1].isupper() else Color.WHITE
        board.set_piece(file, rank, Piece(color, piece_type))
        file -= 1
    if file != 0:
        raise ValueError(f"{rank}段目のマス数が{BOARD_SIZE}ではありません: {row!r}")
