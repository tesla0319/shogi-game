"""持ち駒のデータモデル（SHOGI-4a）。

取った駒を手番ごとに保持する Hand を定義する。持ち駒にできるのは成っていない
基本7駒種（歩・香・桂・銀・金・角・飛）のみ。玉は取れず、成駒は取ったときに
素の駒種へ戻るため、持ち駒として成駒・玉が入ることはない。

盤面（Board）や手番管理（対局進行の Phase）とは分離し、枚数の増減だけを扱う。
取った駒の駒種変換（成駒→素・色反転）や、どちらの手番の持ち駒かの対応付けは
このモジュールの責務ではなく、着手適用（対局進行）側で扱う。
"""

from shogi.piece import PieceType

# 持ち駒にできる駒種。成っていない基本7種のみ（玉は取れない、成駒は素に戻る）。
# movegen の _PROMOTABLE_TYPES（成れる6種）とは別概念（金を含み、角飛も含む）
_HAND_PIECE_TYPES = frozenset(
    {
        PieceType.PAWN,
        PieceType.LANCE,
        PieceType.KNIGHT,
        PieceType.SILVER,
        PieceType.GOLD,
        PieceType.BISHOP,
        PieceType.ROOK,
    }
)


class Hand:
    """片方の手番の持ち駒。駒種ごとの枚数だけを保持する。

    保持できるのは基本7駒種のみで、成駒・玉を渡すと ValueError を送出する。
    Board と同様に可変（駒を取ったら add、打ったら remove する想定）。
    """

    def __init__(self) -> None:
        # 生成直後は持ち駒なし。保持できる駒種を 0 枚で初期化しておく
        self._counts: dict[PieceType, int] = {pt: 0 for pt in _HAND_PIECE_TYPES}

    def count(self, piece_type: PieceType) -> int:
        """指定駒種の所持枚数を返す。"""
        self._validate_type(piece_type)
        return self._counts[piece_type]

    def add(self, piece_type: PieceType, count: int = 1) -> None:
        """指定駒種を count 枚加える（既定は1枚）。"""
        self._validate_type(piece_type)
        self._validate_count(count)
        self._counts[piece_type] += count

    def remove(self, piece_type: PieceType, count: int = 1) -> None:
        """指定駒種を count 枚減らす（既定は1枚）。

        所持枚数が足りない場合は減算せず ValueError を送出する
        （持っていない駒を打つ・二重に打つといった不整合を早期に弾くため）。
        """
        self._validate_type(piece_type)
        self._validate_count(count)
        if self._counts[piece_type] < count:
            raise ValueError(
                f"持ち駒が不足しています: {piece_type} を {count} 枚減らせません"
                f"（所持 {self._counts[piece_type]} 枚）"
            )
        self._counts[piece_type] -= count

    def _validate_type(self, piece_type: PieceType) -> None:
        """持ち駒にできない駒種（成駒・玉）なら ValueError を送出する。"""
        if piece_type not in _HAND_PIECE_TYPES:
            raise ValueError(f"持ち駒にできない駒種です: {piece_type}")

    def _validate_count(self, count: int) -> None:
        """加算・減算の枚数が1未満なら ValueError を送出する。"""
        if count < 1:
            raise ValueError(f"枚数は1以上を指定してください: {count}")
