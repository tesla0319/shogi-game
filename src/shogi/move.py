"""指し手のデータモデル。

盤上の駒の移動（移動元 → 移動先）と成り/不成の区別を表す最小構成。
駒打ちは、それを実装する Phase でフィールドを拡張する。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """盤上の駒の移動1手。座標は Board と同じ file（筋）/ rank（段）で表す。

    is_promotion はこの移動で成るかどうか。デフォルトを False にしているのは、
    成りが発生しない手（および成りを導入する前の既存コード）が4引数の
    コンストラクタのままで正しく動くようにするため。成れる駒種・成れる位置か
    どうかの正当性は Move 自身は保証せず、生成側（movegen）が保証する。
    """

    from_file: int
    from_rank: int
    to_file: int
    to_rank: int
    is_promotion: bool = False
