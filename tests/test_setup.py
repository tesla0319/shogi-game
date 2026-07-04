"""pytest 環境の動作確認用サンプルテスト（将棋ロジックは含まない）。

src/ レイアウトのパッケージを pytest が解決できることだけを検証する。
"""

import shogi


def test_shogi_package_is_importable():
    # pyproject.toml の pythonpath 設定で src/shogi が import できれば成功
    assert shogi is not None
