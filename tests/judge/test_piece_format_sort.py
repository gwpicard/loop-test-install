# Intent: `tally --top N` takes `--format` (csv, json or table) and `--sort` (count or alpha), in any order, and rejects unknown values.
import itertools
import json


def run(tmp_path, capsys, content, *options):
    from tally.cli import main

    path = tmp_path / "in.txt"
    path.write_bytes(content)
    capsys.readouterr()
    code = main([*options, str(path)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


PEAR = b"pear apple pear fig kiwi pear apple\n"


def test_D1_format_csv_prints_header_and_rows(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"b a b c a b\n", "--top", "2", "--format", "csv"
    )
    assert out == "word,count\nb,3\na,2\n"
    assert err == ""
    assert code == 0


def test_D2_format_json_prints_one_line_array(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"don't don't stop\n", "--top", "2", "--format", "json"
    )
    assert out.endswith("\n")
    assert out.count("\n") == 1
    assert json.loads(out) == [
        {"word": "don't", "count": 2},
        {"word": "stop", "count": 1},
    ]
    assert err == ""
    assert code == 0


def test_D3_format_table_aligns_columns(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"apple apple banana\n", "--top", "2", "--format", "table"
    )
    assert out == (
        "word    count\n"
        "------  -----\n"
        "apple       2\n"
        "banana      1\n"
    )
    assert err == ""
    assert code == 0


def test_D4_sort_alpha_orders_top_words_by_word(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, PEAR, "--top", "3", "--sort", "alpha")
    assert out == "apple 2\nfig 1\npear 3\n"
    assert err == ""
    assert code == 0


def test_D5_sort_count_matches_default_order(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, PEAR, "--top", "3", "--sort", "count")
    assert out == "pear 3\napple 2\nfig 1\n"
    assert err == ""
    assert code == 0


def test_D6_options_work_in_any_order(tmp_path, capsys):
    options = [["--top", "3"], ["--sort", "alpha"], ["--format", "csv"]]
    for order in itertools.permutations(options):
        args = [arg for option in order for arg in option]
        code, out, err = run(tmp_path, capsys, PEAR, *args)
        assert out == "word,count\napple,2\nfig,1\npear,3\n", args
        assert err == "", args
        assert code == 0, args


def test_D7_unknown_format_is_an_error(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"b a b c\n", "--top", "2", "--format", "xml"
    )
    assert out == ""
    assert err == "tally: unknown --format value: xml (use csv, json or table)\n"
    assert code == 2


def test_D8_unknown_sort_is_an_error(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"b a b c\n", "--top", "2", "--sort", "size"
    )
    assert out == ""
    assert err == "tally: unknown --sort value: size (use count or alpha)\n"
    assert code == 2


def test_D9_top_alone_keeps_plain_output(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, b"b a b c\n", "--top", "2")
    assert out == "b 2\na 1\n"
    assert err == ""
    assert code == 0


def test_D10_no_words_error_with_format(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, b"123 !!!\n", "--top", "2", "--format", "json"
    )
    assert out == ""
    assert err == f"tally: {tmp_path / 'in.txt'}: no words\n"
    assert code == 1
