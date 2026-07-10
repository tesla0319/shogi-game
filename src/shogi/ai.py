"""AI の手選択（SHOGI-5a）。

合法手の一覧から1手を選ぶだけの最小の AI。まずは「合法手からランダムに選ぶ」ことに
限定し、局面評価・探索は後続 Phase に分ける。合法手の生成はこのモジュールの責務では
なく、呼び出し側（対局ループ）が `generate_legal_moves` で用意した一覧を渡す前提。

再現性のため、乱数はモジュールグローバルの random ではなく、呼び出し側が渡す
`random.Random` インスタンス（rng）だけを使う。同じ合法手一覧と同じシードの rng を
渡せば、必ず同じ手を返す（テストや対局の再現に使う）。
"""

import random
from collections.abc import Sequence

from shogi.move import Move


def choose_move(legal_moves: Sequence[Move], rng: random.Random) -> Move:
    """合法手の一覧から1手をランダムに選んで返す。

    選択には渡された `rng`（random.Random）だけを使う。グローバル乱数を使わないのは、
    同じシードの rng を渡せば同じ手を返す再現性を保証するため。合法性の判定はしない
    （渡された一覧はすべて合法である前提。生成は呼び出し側の責務）。

    合法手が無い（空の一覧）場合は ValueError を送出する。合法手が無い局面は終局
    （詰み・行き詰まり）であり、AI が手を選ぶ場面ではないため、呼び出し側の想定外の
    使い方として早期に弾く。入力の一覧は読み取るだけで変更しない。
    """
    if not legal_moves:
        raise ValueError("合法手がありません（空の一覧からは手を選べません）")
    return rng.choice(legal_moves)
