# SPDX-License-Identifier: MIT

"""
Tests for `attr.converters`.
"""

import pickle

import pytest

import attr

from attr import Converter, Factory, attrib
from attr.converters import default_if_none, optional, pipe, to_bool


class TestConverter:
    @pytest.mark.parametrize("takes_self", [True, False])
    @pytest.mark.parametrize("takes_field", [True, False])
    def test_pickle(self, takes_self, takes_field):
        """
        Wrapped converters can be pickled.
        """
        c = Converter(int, takes_self=takes_self, takes_field=takes_field)

        new_c = pickle.loads(pickle.dumps(c))

        assert c == new_c
        assert takes_self == new_c.takes_self
        assert takes_field == new_c.takes_field

    @pytest.mark.parametrize(
        "scenario",
        [
            ((False, False), "__attr_converter_le_name(le_value)"),
            (
                (True, True),
                "__attr_converter_le_name(le_value, self, attr_dict['le_name'])",
            ),
            (
                (True, False),
                "__attr_converter_le_name(le_value, self)",
            ),
            (
                (False, True),
                "__attr_converter_le_name(le_value, attr_dict['le_name'])",
            ),
        ],
    )
    def test_fmt_converter_call(self, scenario):
        """
        _fmt_converter_call determines the arguments to the wrapped converter
        according to `takes_self` and `takes_field`.
        """
        (takes_self, takes_field), expect = scenario

        c = Converter(None, takes_self=takes_self, takes_field=takes_field)

        assert expect == c._fmt_converter_call("le_name", "le_value")


class TestOptional:
    """
    Tests for `optional`.
    """

    def test_success_with_type(self):
        """
        Wrapped converter is used as usual if value is not None.
        """
        c = optional(int)

        assert c("42") == 42

    def test_success_with_none(self):
        """
        Nothing happens if None.
        """
        c = optional(int)

        assert c(None) is None

    def test_fail(self):
        """
        Propagates the underlying conversion error when conversion fails.
        """
        c = optional(int)

        with pytest.raises(ValueError):
            c("not_an_int")


class TestDefaultIfNone:
    def test_missing_default(self):
        """
        Raises TypeError if neither default nor factory have been passed.
        """
        with pytest.raises(TypeError, match="Must pass either"):
            default_if_none()

    def test_too_many_defaults(self):
        """
        Raises TypeError if both default and factory are passed.
        """
        with pytest.raises(TypeError, match="but not both"):
            default_if_none(True, lambda: 42)

    def test_factory_takes_self(self):
        """
        Raises ValueError if passed Factory has takes_self=True.
        """
        with pytest.raises(ValueError, match="takes_self"):
            default_if_none(Factory(list, takes_self=True))

    @pytest.mark.parametrize("val", [1, 0, True, False, "foo", "", object()])
    def test_not_none(self, val):
        """
        If a non-None value is passed, it's handed down.
        """
        c = default_if_none("nope")

        assert val == c(val)

        c = default_if_none(factory=list)

        assert val == c(val)

    def test_none_value(self):
        """
        Default values are returned when a None is passed.
        """
        c = default_if_none(42)

        assert 42 == c(None)

    def test_none_factory(self):
        """
        Factories are used if None is passed.
        """
        c = default_if_none(factory=list)

        assert [] == c(None)

        c = default_if_none(default=Factory(list))

        assert [] == c(None)


class TestPipe:
    def test_success(self):
        """
        Succeeds if all wrapped converters succeed.
        """
        c = pipe(str, Converter(to_bool), bool)

        assert (
            True
            is c.converter("True", None, None)
            is c.converter(True, None, None)
        )

    def test_fail(self):
        """
        Fails if any wrapped converter fails.
        """
        c = pipe(str, to_bool)

        # First wrapped converter fails:
        with pytest.raises(ValueError):
            c.converter(33, None, None)

        # Last wrapped converter fails:
        with pytest.raises(ValueError):
            c.converter("33", None, None)

    def test_sugar(self):
        """
        `pipe(c1, c2, c3)` and `[c1, c2, c3]` are equivalent.
        """

        @attr.s
        class C:
            a1 = attrib(default="True", converter=pipe(str, to_bool, bool))
            a2 = attrib(default=True, converter=[str, to_bool, bool])

        c = C()
        assert True is c.a1 is c.a2

    def test_empty(self):
        """
        Empty pipe returns same value.
        """
        o = object()

        assert o is pipe().converter(o, None, None)


class TestToBool:
    def test_unhashable(self):
        """
        Fails if value is unhashable.
        """
        with pytest.raises(ValueError, match="Cannot convert value to bool"):
            to_bool([])

    def test_truthy(self):
        """
        Fails if truthy values are incorrectly converted.
        """
        assert to_bool("t")
        assert to_bool("yes")
        assert to_bool("on")

    def test_falsy(self):
        """
        Fails if falsy values are incorrectly converted.
        """
        assert not to_bool("f")
        assert not to_bool("no")
        assert not to_bool("off")
