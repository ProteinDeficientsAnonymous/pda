import pytest

from users._name_parsing import parse_display_name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ("", "")),
        ("   ", ("", "")),
        ("Cher", ("Cher", "")),
        ("Ada Lovelace", ("Ada", "Lovelace")),
        ("Mary Jane Watson", ("Mary Jane", "Watson")),
        ("  extra   spaces  here ", ("extra spaces", "here")),
    ],
)
def test_parse_display_name(raw, expected):
    assert parse_display_name(raw) == expected
