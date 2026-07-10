"""`python -m shogi` で CLI 対局を起動するエントリポイント（SHOGI-4l）。

対局ロジック本体は cli.run_game にあり、ここは標準入出力で起動するだけに留める。
"""

from shogi.cli import run_game


def main() -> None:
    """既定の入出力（input / print）で人対人の CLI 対局を開始する。"""
    run_game()


if __name__ == "__main__":
    main()
