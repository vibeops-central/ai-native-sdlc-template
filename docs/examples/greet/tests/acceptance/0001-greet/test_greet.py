import pytest

from example.greet import greet


def test_greets_by_name():
    assert greet("Ada") == "Hello, Ada!"


def test_trims_spaces():
    assert greet("  Ada  ") == "Hello, Ada!"


def test_keeps_inner_spaces():
    assert greet("Ada Lovelace") == "Hello, Ada Lovelace!"


@pytest.mark.parametrize("name", ["", "   "])
def test_rejects_blank_names(name):
    with pytest.raises(ValueError):
        greet(name)
