import pytest

from ninja.utils import replace_path_param_notation


@pytest.mark.parametrize(
    "input,expected_output",
    [
        ("abc/{def}", "abc/<def>"),
        ("abc/<def>", "abc/<def>"),
        ("abc", "abc"),
        ("<abc>", "<abc>"),
        ("{abc}", "<abc>"),
        ("{abc}/{def}", "<abc>/<def>"),
    ],
)
def test_replace_path_param_notation(input, expected_output):
    assert replace_path_param_notation(input) == expected_output
