"""CLI 対局ループ（SHOGI-4l）・自動終局判定（SHOGI-4m）・人対AI接続（SHOGI-5b）のテスト。

run_game に入出力を注入し、投了・入力終了（EOF）・不正入力・非合法手・正常な着手・
自動終局（詰み／合法手なし／着手後の詰み）・人対AI（AI手番の自動着手）の各フローを検証する。
標準入出力を使わず、入力はキュー、出力は収集リストで再現する。
"""

import random

from shogi.cli import run_game
from shogi.hand import Hand
from shogi.piece import Color
from shogi.position import Position
from shogi.sfen import board_from_sfen
from shogi.usi import move_from_usi


def make_io(lines):
    """入力キューと出力収集リストを持つ (input_fn, output_fn, outputs) を作る。

    input_fn はキューを1行ずつ返し、尽きたら EOFError を送出する（EOF を模す）。
    output_fn は渡された文字列を outputs に貯める。
    """
    queue = iter(lines)
    outputs = []

    def input_fn():
        try:
            return next(queue)
        except StopIteration:
            raise EOFError

    def output_fn(text):
        outputs.append(text)

    return input_fn, output_fn, outputs


def joined(outputs):
    """出力を1つの文字列に連結する（部分文字列での照合を簡単にする）。"""
    return "\n".join(outputs)


class TestResign:
    """投了での終局。"""

    def test_先手が投了すると後手の勝ち(self):
        input_fn, output_fn, outputs = make_io(["resign"])
        run_game(input_fn, output_fn)
        assert "先手が投了しました。後手の勝ちです。" in joined(outputs)

    def test_一手指してから後手が投了すると先手の勝ち(self):
        # 先手 7g7f を指すと手番が後手に移り、後手の resign で先手の勝ち
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn)
        assert "後手が投了しました。先手の勝ちです。" in joined(outputs)


class TestEndOfInput:
    """入力終了（EOF）での中断。"""

    def test_入力がなければ穏やかに終了する(self):
        # 例外を送出せず、終了メッセージを出して返る
        input_fn, output_fn, outputs = make_io([])
        run_game(input_fn, output_fn)  # 例外が飛ばないこと
        assert "入力が終了したため、対局を終了します。" in joined(outputs)


class TestInvalidInput:
    """不正入力（USI形式・非合法手）は再入力を促し、局面・手番を変えない。"""

    def test_USI形式が不正なら再入力を促す(self):
        input_fn, output_fn, outputs = make_io(["hello", "resign"])
        run_game(input_fn, output_fn)
        text = joined(outputs)
        assert "USI形式として解釈できません。もう一度入力してください。" in text
        # 手番は先手のまま（先手が投了）
        assert "先手が投了しました。後手の勝ちです。" in text

    def test_非合法手なら再入力を促す(self):
        # 1a1a は USI として正しいが平手初期局面の先手の合法手ではない
        input_fn, output_fn, outputs = make_io(["1a1a", "resign"])
        run_game(input_fn, output_fn)
        text = joined(outputs)
        assert "非合法手です。もう一度入力してください。" in text
        assert "先手が投了しました。後手の勝ちです。" in text


class TestCompositeSequence:
    """不正形式 → 非合法手 → 合法手 → 相手の投了、の複合フロー。"""

    def test_エラー後に合法手を指せて対局が進む(self):
        input_fn, output_fn, outputs = make_io(["++", "1a1a", "7g7f", "resign"])
        run_game(input_fn, output_fn)
        text = joined(outputs)
        # 2種類のエラーメッセージが出ている
        assert "USI形式として解釈できません。もう一度入力してください。" in text
        assert "非合法手です。もう一度入力してください。" in text
        # 合法手 7g7f が適用され、手番が後手に移った局面が表示されている
        assert "手番: 後手" in text
        # その後の後手投了で先手の勝ち（＝先手の手番が正しく回復・進行した）
        assert "後手が投了しました。先手の勝ちです。" in text

    def test_合法手の適用後に盤面が更新される(self):
        # 7g の先手歩が消え、7f に先手歩が来た局面が出力に含まれる
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn)
        # 適用後の表示（最後の局面表示）を確認する。7筋6段(f)に先手歩、7筋7段(g)は空
        applied = [o for o in outputs if "手番: 後手" in o]
        assert applied, "着手適用後の局面表示が見つからない"
        board_text = applied[-1]
        # 筋は 9→1 の並び。7筋は左から3番目
        assert " . . P . . . . . . f" in board_text  # 先手歩が7筋6段(f)に繰り上がった
        assert " P P . P P P P P P g" in board_text  # 7筋7段(g)が空いた


class TestInitialDisplay:
    """対局開始時に初期局面と手番プロンプトが表示される。"""

    def test_開始時に平手初期局面と先手プロンプトが出る(self):
        input_fn, output_fn, outputs = make_io(["resign"])
        run_game(input_fn, output_fn)
        text = joined(outputs)
        assert "手番: 先手" in text  # 初期局面表示に含まれる
        assert "先手の手を入力してください（USI形式、投了は resign）:" in text


class TestCheckmateTermination:
    """合法手0件かつ王手中 → 詰みで相手の勝ち（SHOGI-4m）。"""

    def test_開始局面が詰みなら入力を求めず終局する(self):
        # 5一後手玉／5二先手金／5九先手香。後手玉は詰み（王手・逃げ場なし・金は香に守られ取れない）
        #   5b の金は 5a を王手し、逃げ場 4a/6a/4b/6b をすべて利かせる。
        #   玉が 5b の金を取ると 5i の香に取られるため取れない → 詰み。後手番。
        board = board_from_sfen("4k4/4G4/9/9/9/9/9/9/4L4")
        pos = Position(board, Hand(), Hand(), Color.WHITE)
        input_fn, output_fn, outputs = make_io([])  # 入力しない（求められないはず）
        run_game(input_fn, output_fn, start_position=pos)
        text = joined(outputs)
        assert "後手は詰みです。先手の勝ちです。" in text
        # 詰みなので手番側（後手）へのプロンプトは出ない
        assert "後手の手を入力してください（USI形式、投了は resign）:" not in text


class TestNoLegalMovesTermination:
    """合法手0件かつ王手なし → 合法手なしで手番側の負け（SHOGI-4m）。"""

    def test_ステイルメイトは手番側の負けで終局する(self):
        # 1一後手玉のみ。3二先手金が2一/2二を、2三先手金が1二/2二を利かせる。
        #   玉は王手されていないが 2a/1b/2b すべて相手の利きで動けない → 合法手なし。後手番。
        board = board_from_sfen("8k/6G2/7G1/9/9/9/9/9/9")
        pos = Position(board, Hand(), Hand(), Color.WHITE)
        input_fn, output_fn, outputs = make_io([])
        run_game(input_fn, output_fn, start_position=pos)
        text = joined(outputs)
        assert "後手に合法手がありません。先手の勝ちです。" in text
        assert "後手は詰みです" not in text  # 王手ではないので「詰み」表記にはしない


class TestCheckmateAfterMove:
    """着手後に相手が詰めば、その手番でプロンプトを出さず自動終局する（SHOGI-4m）。"""

    def test_詰ます手を指すと相手番で自動終局する(self):
        # 5一後手玉／5三先手金／5九先手香。先手が 5c5b と金を上がると後手が詰む。
        board = board_from_sfen("4k4/9/4G4/9/9/9/9/9/4L4")
        pos = Position(board, Hand(), Hand(), Color.BLACK)
        input_fn, output_fn, outputs = make_io(["5c5b"])  # 詰ます手のみ入力
        run_game(input_fn, output_fn, start_position=pos)
        text = joined(outputs)
        assert "後手は詰みです。先手の勝ちです。" in text


class TestHumanVsAI:
    """ai_side を渡したときの人対AI進行（SHOGI-5b）。既定は人先手・AI後手。"""

    def test_人の着手後にAIが自動で指す(self):
        # 先手（人）7g7f → 後手（AI）が自動着手 → 先手（人）resign で終局
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn, ai_side=Color.WHITE, rng=random.Random(0))
        text = joined(outputs)
        assert "後手AI: " in text  # AI が自動で指した
        assert "先手が投了しました。後手の勝ちです。" in text  # 人の手番に戻り投了できた

    def test_AI手番は人の入力を消費しない(self):
        # 入力キューは人の2手番（7g7f と resign）分だけ。AI が入力を消費すると
        # 2手目の resign が AI 手番で消え、次の人手番で EOF になってしまう。
        calls = {"n": 0}
        queue = iter(["7g7f", "resign"])
        outputs = []

        def input_fn():
            calls["n"] += 1
            try:
                return next(queue)
            except StopIteration:
                raise EOFError

        def output_fn(text):
            outputs.append(text)

        run_game(input_fn, output_fn, ai_side=Color.WHITE, rng=random.Random(0))
        text = "\n".join(outputs)
        assert calls["n"] == 2  # 人の2手番でのみ入力を求めた
        assert "入力が終了したため" not in text  # EOF に落ちていない
        assert "先手が投了しました。後手の勝ちです。" in text

    def test_AIの手はUSI形式で表示される(self):
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn, ai_side=Color.WHITE, rng=random.Random(0))
        ai_lines = [o for o in outputs if o.startswith("後手AI: ")]
        assert ai_lines, "AI の着手表示が見つからない"
        usi = ai_lines[-1].removeprefix("後手AI: ")
        move_from_usi(usi)  # USI として解釈できる（不正なら ValueError で失敗する）

    def test_AI着手後は人の手番に戻る(self):
        # 初期表示（先手）＋ AI 着手後の表示（先手）で「手番: 先手」の局面が2回以上出る
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn, ai_side=Color.WHITE, rng=random.Random(0))
        black_renders = [o for o in outputs if "手番: 先手" in o]
        assert len(black_renders) >= 2

    def test_同じシードならAIの手は再現する(self):
        in1, out1, outputs1 = make_io(["7g7f", "resign"])
        run_game(in1, out1, ai_side=Color.WHITE, rng=random.Random(0))
        in2, out2, outputs2 = make_io(["7g7f", "resign"])
        run_game(in2, out2, ai_side=Color.WHITE, rng=random.Random(0))
        assert outputs1 == outputs2

    def test_ai_sideがNoneなら従来の人対人を維持する(self):
        # 明示的に ai_side=None。AI 分岐を通らず、両手番とも人の入力で進む
        input_fn, output_fn, outputs = make_io(["7g7f", "resign"])
        run_game(input_fn, output_fn, ai_side=None)
        text = joined(outputs)
        assert "AI" not in text  # AI 表示は一切出ない
        # 先手 7g7f → 後手（人）resign → 先手の勝ち
        assert "後手が投了しました。先手の勝ちです。" in text
