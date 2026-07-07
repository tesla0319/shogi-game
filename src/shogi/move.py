"""指し手のデータモデル。

盤上の駒の移動（移動元 → 移動先）と成り/不成の区別に加え、
持ち駒を打つ手（駒打ち）を表す。合法性の判定（二歩・打ち歩詰め等）は
別 Phase で扱い、Move 自身は手の「形」だけを保持する。
"""

from dataclasses import dataclass

from shogi.piece import PieceType

# 駒打ちの Move は移動元マスを持たないため、from_file / from_rank に番兵値を入れる。
# 盤の座標は 1〜9 なので、範囲外の 0 を使えば通常移動の座標と決して衝突しない。
# この値は Move.drop() 内部でのみ使い、外部からは is_drop で判別させる。
_DROP_SENTINEL = 0


@dataclass(frozen=True)
class Move:
    """1手を表す。座標は Board と同じ file（筋）/ rank（段）で表す。

    通常移動と駒打ちの両方をこの1クラスで表す。駒打ち専用クラスを作らないのは、
    「指し手」という1概念を型で分割せず、生成・比較・保持を統一的に扱うため。

    - 通常移動: from_file/from_rank から to_file/to_rank へ動かす。drop_piece_type は None。
    - 駒打ち  : Move.drop() で生成し、drop_piece_type に打つ駒種を持つ。

    is_promotion はこの移動で成るかどうか。デフォルトを False にしているのは、
    成りが発生しない手（および成りを導入する前の既存コード）が4引数の
    コンストラクタのままで正しく動くようにするため。成れる駒種・成れる位置か
    どうかの正当性は Move 自身は保証せず、生成側（movegen）が保証する。

    drop_piece_type はデフォルトを None にしているのは、既存の通常移動 Move の
    生成コードに手を入れずそのまま使えるようにするため。
    """

    from_file: int
    from_rank: int
    to_file: int
    to_rank: int
    is_promotion: bool = False
    drop_piece_type: PieceType | None = None

    @classmethod
    def drop(cls, piece_type: PieceType, to_file: int, to_rank: int) -> "Move":
        """持ち駒 piece_type を (to_file, to_rank) に打つ手を生成する。

        移動元がないため from_file/from_rank は番兵値になるが、呼び出し側は
        番兵値を意識せず、打つ駒種と打つ先だけを指定すればよい。
        """
        return cls(
            from_file=_DROP_SENTINEL,
            from_rank=_DROP_SENTINEL,
            to_file=to_file,
            to_rank=to_rank,
            drop_piece_type=piece_type,
        )

    @property
    def is_drop(self) -> bool:
        """この手が駒打ちなら True、通常移動なら False。"""
        return self.drop_piece_type is not None
