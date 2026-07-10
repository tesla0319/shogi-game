"""USI 指し手表記の入出力（SHOGI-4i）。

CLAUDE.md「将棋ドメインの取り決め」のとおり、指し手の外部表記は USI 形式を正とする。
このモジュールに USI 指し手の変換を集約し、Move 自身は表記を知らないままにする
（sfen.py が Board と SFEN の変換を集約しているのと同じ役割分担）。

USI 指し手の規則:
- 筋（file）は 1〜9 の数字、段（rank）は a〜i の英小文字（a=1, b=2, …, i=9）
- 通常移動: 移動元 + 移動先。例 "7g7f"（7筋7段 → 7筋6段）
- 成り    : 通常移動の末尾に "+"。例 "8h2b+"（8筋8段 → 2筋2段で成る）
- 駒打ち  : 駒種1文字 + "*" + 打つ先。例 "P*5e"（歩を5筋5段に打つ）。
  駒種文字は打てる7種のみ（歩=P 香=L 桂=N 銀=S 金=G 角=B 飛=R）で、先後に関わらず大文字

盤面上の合法性（二歩・行き所のない駒・王手放置など）はこのモジュールでは判定しない。
判定するのは「USI として表記の形が正しいか」だけで、不正な形は ValueError を送出する。
"""

from shogi.move import Move
from shogi.piece import PieceType

# 段（rank）の数字 1〜9 と USI の英字 a〜i の対応。インデックス0が段1（"a"）。
# 先手/後手で反転しない（USI の段は盤の絶対座標）。
_RANK_LETTERS = "abcdefghi"

# 打てる駒種 → USI の駒打ち文字（大文字）。玉・成駒は打てないので含めない。
# sfen.py の _SFEN_LETTERS とは別に持つ: あちらは盤上の全14駒種（成駒の "+X" を含む）用で、
# こちらは「駒打ちで使える7種のみ」という別の制約を表すため、流用せず独立させる。
_DROP_LETTERS = {
    PieceType.PAWN: "P",
    PieceType.LANCE: "L",
    PieceType.KNIGHT: "N",
    PieceType.SILVER: "S",
    PieceType.GOLD: "G",
    PieceType.BISHOP: "B",
    PieceType.ROOK: "R",
}

# USI の駒打ち文字 → 駒種（_DROP_LETTERS の逆引き）
_LETTER_TO_DROP = {letter: piece_type for piece_type, letter in _DROP_LETTERS.items()}


def move_from_usi(usi: str) -> Move:
    """USI 指し手文字列を Move に変換して返す。

    通常移動・成り・駒打ちを判別する。判別は "*" の有無で行い、"*" を含めば駒打ち、
    含まなければ通常移動（末尾の "+" で成りを表す）として解釈する。

    盤面を参照しないため、その手が実際に指せるか（駒があるか・合法か）は検証しない。
    表記の形が不正な場合は ValueError を送出する:
    - 空文字列、長さが規定と異なる
    - 筋が 1〜9 でない、段が a〜i でない
    - "+" が末尾以外にある、駒打ちに "+"（成り）が付いている
    - 駒打ちの駒種文字が打てる7種（P L N S G B R）でない
    """
    if not usi:
        raise ValueError("USI 文字列が空です")
    # "*" を含む手は駒打ち。通常移動は「筋段筋段(+)」で "*" を含まないため確実に判別できる
    if "*" in usi:
        return _parse_drop(usi)
    return _parse_normal(usi)


def _parse_drop(usi: str) -> Move:
    """駒打ちの USI 文字列（例 "P*5e"）を Move に変換する。

    形式はちょうど4文字「駒種 '*' 筋 段」に限る。成り（"+"）は付かない
    （打った駒は成れないため、"P*5e+" のような表記は不正として弾く）。
    """
    if len(usi) != 4 or usi[1] != "*":
        raise ValueError(f"駒打ちの形式が不正です: {usi!r}（例: 'P*5e'）")
    letter = usi[0]
    piece_type = _LETTER_TO_DROP.get(letter)
    if piece_type is None:
        # 玉(K)・成駒(+P 等)・小文字・未知の文字はここで弾く
        raise ValueError(f"打てない駒種です: {letter!r}（打てるのは P L N S G B R）")
    to_file = _parse_file(usi[2])
    to_rank = _parse_rank(usi[3])
    return Move.drop(piece_type, to_file, to_rank)


def _parse_normal(usi: str) -> Move:
    """通常移動の USI 文字列（例 "7g7f" / "8h2b+"）を Move に変換する。

    末尾の "+" のみを成りとして扱う。"+" が末尾以外にあると本体長が4にならず、
    下の長さチェックで ValueError になる（暗黙に補正しない）。
    """
    is_promotion = usi.endswith("+")
    body = usi[:-1] if is_promotion else usi
    if len(body) != 4:
        raise ValueError(f"通常移動の形式が不正です: {usi!r}（例: '7g7f' / '8h2b+'）")
    from_file = _parse_file(body[0])
    from_rank = _parse_rank(body[1])
    to_file = _parse_file(body[2])
    to_rank = _parse_rank(body[3])
    return Move(from_file, from_rank, to_file, to_rank, is_promotion=is_promotion)


def _parse_file(char: str) -> int:
    """USI の筋文字（"1"〜"9"）を筋番号 1〜9 に変換する。範囲外は ValueError。

    str.isdigit() は全角数字や "0" も拾うため使わず、許可文字を明示的に照合する。
    """
    if char not in "123456789":
        raise ValueError(f"不正な筋です: {char!r}（1〜9 で指定）")
    return int(char)


def _parse_rank(char: str) -> int:
    """USI の段文字（"a"〜"i"）を段番号 1〜9 に変換する。範囲外・大文字は ValueError。"""
    index = _RANK_LETTERS.find(char)
    if index == -1:
        raise ValueError(f"不正な段です: {char!r}（a〜i で指定）")
    return index + 1


def move_to_usi(move: Move) -> str:
    """Move を USI 指し手文字列に変換して返す。

    駒打ちは "駒種*筋段"、通常移動は "筋段筋段"（成りなら末尾に "+"）にする。
    盤面や合法手生成には依存しない（Move の内容だけで一意に定まる変換）。

    Move が USI として表現できない場合は ValueError を送出する:
    - 打てない駒種（玉・成駒）を持つ駒打ち Move
    - 筋・段が 1〜9 の範囲外の座標を持つ Move
    """
    if move.is_drop:
        letter = _DROP_LETTERS.get(move.drop_piece_type)
        if letter is None:
            raise ValueError(f"USI で表現できない駒打ちの駒種です: {move.drop_piece_type}")
        return f"{letter}*{_file_to_str(move.to_file)}{_rank_to_letter(move.to_rank)}"

    usi = (
        f"{_file_to_str(move.from_file)}{_rank_to_letter(move.from_rank)}"
        f"{_file_to_str(move.to_file)}{_rank_to_letter(move.to_rank)}"
    )
    if move.is_promotion:
        usi += "+"
    return usi


def _file_to_str(file: int) -> str:
    """筋番号 1〜9 を USI の筋文字に変換する。範囲外は ValueError。"""
    if not (1 <= file <= 9):
        raise ValueError(f"USI で表現できない筋です: {file}（1〜9 のみ）")
    return str(file)


def _rank_to_letter(rank: int) -> str:
    """段番号 1〜9 を USI の段文字（"a"〜"i"）に変換する。範囲外は ValueError。"""
    if not (1 <= rank <= 9):
        raise ValueError(f"USI で表現できない段です: {rank}（1〜9 のみ）")
    return _RANK_LETTERS[rank - 1]
