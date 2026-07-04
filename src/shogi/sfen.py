"""SFEN 表記の入出力。

このモジュールに SFEN 関連の変換を集約する（Board は表記を知らないままにする）。
SHOGI-1e-1 では「盤面部の出力」のみ。読み込み・手番・持ち駒・手数は後続で扱う。

SFEN 盤面部の規則:
- 段（rank）1 から 9 の順に、各段を "/" で区切って並べる
- 各段の中は file=9（先手から見て左端）から file=1 の順に書く
- 駒は1文字（歩=P 香=L 桂=N 銀=S 金=G 角=B 飛=R 玉=K）。
  先手は大文字・後手は小文字。成駒は頭に "+" を付ける（と金=+P、馬=+b など）
- 連続する空きマスはその個数の数字1文字に圧縮する（例: 空きマス5個 → "5"）
"""

from shogi.board import BOARD_SIZE, Board
from shogi.piece import Color, PieceType

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
