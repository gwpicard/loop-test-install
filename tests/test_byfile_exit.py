from tally.byfile import exit_code


def test_no_statuses_exit_zero():
    assert exit_code([]) == 0


def test_all_ok_exit_zero():
    assert exit_code([0, 0]) == 0


def test_no_words_exit_one():
    assert exit_code([0, 1, 0]) == 1


def test_read_error_exit_two():
    assert exit_code([0, 2]) == 2


def test_read_error_beats_no_words():
    assert exit_code([1, 2, 1]) == 2
    assert exit_code([2, 1]) == 2
