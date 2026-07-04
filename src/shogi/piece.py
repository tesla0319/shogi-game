"""駒のデータモデル。

Color（先手/後手）・PieceType（駒種）・Piece（手番付きの1枚の駒）を定義する。
盤面・SFEN 入出力・駒の動きは後続 Phase で扱うため、このモジュールには含めない。
"""

from dataclasses import dataclass
from enum import Enum, auto, unique


@unique
class Color(Enum):
    """手番（先手/後手）。

    外部表記との対応は CLAUDE.md「将棋ドメインの取り決め」のとおり
    先手=b / 後手=w だが、文字への変換は SFEN を扱う Phase で実装する。
    """

    BLACK = auto()  # 先手
    WHITE = auto()  # 後手


@unique
class PieceType(Enum):
    """駒種。成駒は独立した駒種として定義する。

    Piece に成りフラグを持たせる案ではなくこの形にしたのは、
    「金・玉の成り」のような不正な状態を型の段階で作れなくするためと、
    成駒ごとに動きが違うので Phase 2（移動生成）で駒種→動きの対応が
    素直に書けるため。
    """

    PAWN = auto()  # 歩
    LANCE = auto()  # 香
    KNIGHT = auto()  # 桂
    SILVER = auto()  # 銀
    GOLD = auto()  # 金
    BISHOP = auto()  # 角
    ROOK = auto()  # 飛
    KING = auto()  # 玉
    PROMOTED_PAWN = auto()  # と金
    PROMOTED_LANCE = auto()  # 成香
    PROMOTED_KNIGHT = auto()  # 成桂
    PROMOTED_SILVER = auto()  # 成銀
    HORSE = auto()  # 馬（角の成り）
    DRAGON = auto()  # 竜（飛の成り）


@dataclass(frozen=True)
class Piece:
    """1枚の駒。どちらの手番の駒か（color）と駒種（piece_type）だけを持つ。

    不変（frozen）にしているのは、将来複数の局面から同じ駒オブジェクトを
    安全に共有できるようにするため。位置は駒ではなく盤面側が持つ予定。
    """

    color: Color
    piece_type: PieceType
