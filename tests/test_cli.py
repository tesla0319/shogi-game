"""CLI 対局ループ（SHOGI-4l）のテスト。

run_game に入出力を注入し、投了・入力終了（EOF）・不正入力・非合法手・正常な着手の
各フローを検証する。標準入出力を使わず、入力はキュー、出力は収集リストで再現する。
"""

from shogi.cli import run_game


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
