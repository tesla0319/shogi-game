"""盤面のデータモデル。

9x9 の盤面の状態保持（各マスは Piece または None）と、空盤での初期化のみを扱う。
初期局面の配置・SFEN 入出力・駒の移動ルールは後続 Phase で扱う。

座標系（CLAUDE.md「将棋ドメインの取り決め」参照）:
- file（筋）: 1〜9。先手から見て右端が 1、左端が 9
- rank（段）: 1〜9。先手から見て一番奥（上）が 1、手前（下）が 9
  （USI の段 a〜i に 1〜9 がこの順で対応する）
"""

from shogi.piece import Piece

BOARD_SIZE = 9  # 将棋盤は 9x9


class Board:
    """将棋盤。各マスに Piece または None（空きマス）を保持する。

    内部は 9x9 のリストのリスト。_squares[rank - 1][file - 1] でアクセスする。
    生成直後は全マスが None の空盤とする（初期局面の配置は後続 Phase）。
    """

    def __init__(self) -> None:
        # 行ごとに新しいリストを作る（[[None] * 9] * 9 だと同じ行が共有されてしまう）
        self._squares: list[list[Piece | None]] = [
            [None] * BOARD_SIZE for _ in range(BOARD_SIZE)
        ]

    def copy(self) -> "Board":
        """盤面の複製を返す。元の盤面とマスの状態を共有しない。

        各マスの Piece は不変（frozen）なので、マスのリストだけを新しく
        作れば安全に複製できる（Piece 自体は共有してよい）。
        合法手判定（SHOGI-3）で「ある手を指した後の盤面」を、元の盤面を
        壊さずに作るために使う。
        """
        clone = Board()
        clone._squares = [row[:] for row in self._squares]
        return clone

    def get_piece(self, file: int, rank: int) -> Piece | None:
        """指定マスの駒を返す。空きマスなら None を返す。"""
        self._validate_square(file, rank)
        return self._squares[rank - 1][file - 1]

    def set_piece(self, file: int, rank: int, piece: Piece | None) -> None:
        """指定マスに駒を置く。None を渡すとそのマスを空にする。"""
        self._validate_square(file, rank)
        self._squares[rank - 1][file - 1] = piece

    def _validate_square(self, file: int, rank: int) -> None:
        """盤外の座標なら ValueError を送出する。"""
        if not (1 <= file <= BOARD_SIZE and 1 <= rank <= BOARD_SIZE):
            raise ValueError(f"盤外の座標です: file={file}, rank={rank}")
