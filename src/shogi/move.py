"""指し手のデータモデル。

盤上の駒の移動（移動元 → 移動先）だけを表す最小構成。
成り/不成の区別と駒打ちは、それらを実装する Phase でフィールドを拡張する。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """盤上の駒の移動1手。座標は Board と同じ file（筋）/ rank（段）で表す。"""

    from_file: int
    from_rank: int
    to_file: int
    to_rank: int
