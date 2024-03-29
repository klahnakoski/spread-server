# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


import datetime
import types
import unittest
from unittest import SkipTest, TestCase

from mo_collections.unique_index import UniqueIndex
import mo_dots
from mo_dots import coalesce, is_container, is_list, literal_field, from_data, to_data, is_data, is_many
from mo_future import is_text, zip_longest, first, get_function_name
from mo_logs import Except, Log, suppress_exception
from mo_logs.strings import expand_template, quote
import mo_math
from mo_math import is_number, log10
from mo_times import dates


class FuzzyTestCase(unittest.TestCase):
    """
    COMPARE STRUCTURE AND NUMBERS!

    ONLY THE ATTRIBUTES IN THE expected STRUCTURE ARE TESTED TO EXIST
    EXTRA ATTRIBUTES ARE IGNORED.

    NUMBERS ARE MATCHED BY ...
    * places (UP TO GIVEN SIGNIFICANT DIGITS)
    * digits (UP TO GIVEN DECIMAL PLACES, WITH NEGATIVE MEANING LEFT-OF-UNITS)
    * delta (MAXIMUM ABSOLUTE DIFFERENCE FROM expected)
    """

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.default_places=15


    def set_default_places(self, places):
        """
        WHEN COMPARING float, HOW MANY DIGITS ARE SIGNIFICANT BY DEFAULT
        """
        self.default_places=places

    def assertAlmostEqual(self, test_value, expected, msg=None, digits=None, places=None, delta=None):
        if delta or digits:
            assertAlmostEqual(test_value, expected, msg=msg, digits=digits, places=places, delta=delta)
        else:
            assertAlmostEqual(test_value, expected, msg=msg, digits=digits, places=coalesce(places, self.default_places), delta=delta)

    def assertEqual(self, test_value, expected, msg=None, digits=None, places=None, delta=None):
        self.assertAlmostEqual(test_value, expected, msg=msg, digits=digits, places=places, delta=delta)

    def assertRaises(self, problem=None, function=None, *args, **kwargs):
        if function is None:
            return RaiseContext(self, problem=problem or Exception)

        with RaiseContext(self, problem=problem):
            function(*args, **kwargs)


class RaiseContext(object):

    def __init__(self, testcase, problem=Exception):
        self.testcase = testcase
        self.problem = problem

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_val:
            Log.error("Expecting an error")
        f = Except.wrap(exc_val)

        if isinstance(self.problem, (list, tuple)):
            problems = self.problem
        else:
            problems = [self.problem]

        causes = []
        for problem in problems:
            if isinstance(problem, object.__class__) and issubclass(problem, BaseException) and isinstance(exc_val, problem):
                return True
            try:
                self.testcase.assertIn(problem, f)
                return True
            except Exception as cause:
                causes.append(cause)
        Log.error("problem is not raised", cause=first(causes))


def assertAlmostEqual(test, expected, digits=None, places=None, msg=None, delta=None):
    show_detail = True
    test = from_data(test)
    expected = from_data(expected)
    try:
        if test is None and (is_null_op(expected) or expected is None):
            return
        elif test is expected:
            return
        elif is_text(expected):
            assertAlmostEqualValue(test, expected, msg=msg, digits=digits, places=places, delta=delta)
        elif isinstance(test, UniqueIndex):
            if test ^ expected:
                Log.error("Sets do not match")
        elif is_data(expected) and is_data(test):
            for k, e in from_data(expected).items():
                t = test.get(k)
                assertAlmostEqual(t, e, msg=coalesce(msg, "")+"key "+quote(k)+": ", digits=digits, places=places, delta=delta)
        elif is_data(expected):
            if is_many(test):
                test = list(test)
                if len(test) != 1:
                    Log.error("Expecting data, not a list")
                test = test[0]
            for k, e in expected.items():
                try:
                    t = test[k]
                    assertAlmostEqual(t, e, msg=msg, digits=digits, places=places, delta=delta)
                    continue
                except:
                    pass

                t = mo_dots.get_attr(test, literal_field(k))
                assertAlmostEqual(t, e, msg=msg, digits=digits, places=places, delta=delta)
        elif is_container(test) and isinstance(expected, set):
            test = set(to_data(t) for t in test)
            if len(test) != len(expected):
                Log.error(
                    "Sets do not match, element count different:\n{{test|json|indent}}\nexpecting{{expectedtest|json|indent}}",
                    test=test,
                    expected=expected
                )

            try:
                if len(test|expected) != len(test):
                    raise Exception()
            except:
                for e in expected:
                    for t in test:
                        try:
                            assertAlmostEqual(t, e, msg=msg, digits=digits, places=places, delta=delta)
                            break
                        except Exception as _:
                            pass
                    else:
                        Log.error("Sets do not match. {{value|json}} not found in {{test|json}}", value=e, test=test)
            return   # ok
        elif isinstance(expected, types.FunctionType):
            return expected(test)
        elif hasattr(test, "__iter__") and hasattr(expected, "__iter__"):
            if test.__class__.__name__ == "ndarray":  # numpy
                test = test.tolist()
            elif test.__class__.__name__ == "DataFrame":  # pandas
                test = test[test.columns[0]].values.tolist()
            elif test.__class__.__name__ == "Series":  # pandas
                test = test.values.tolist()

            if not expected and test == None:
                return
            if expected == None:
                expected = []  # REPRESENT NOTHING
            for t, e in zip_longest(test, expected):
                assertAlmostEqual(t, e, msg=msg, digits=digits, places=places, delta=delta)
        else:
            assertAlmostEqualValue(test, expected, msg=msg, digits=digits, places=places, delta=delta)
    except Exception as cause:
        Log.error(
            "{{test|json|limit(10000)}} does not match expected {{expected|json|limit(10000)}}",
            test=test if show_detail else "[can not show]",
            expected=expected if show_detail else "[can not show]",
            cause=cause
        )


def assertAlmostEqualValue(test, expected, digits=None, places=None, msg=None, delta=None):
    """
    Snagged from unittest/case.py, then modified (Aug2014)
    """
    if is_null_op(expected):
        if test == None:  # pandas dataframes reject any comparision with an exception!
            return
        else:
            raise AssertionError(expand_template("{{test|json}} != NULL", locals()))

    if expected == None:  # None has no expectations
        return
    if test == expected:
        # shortcut
        return
    if isinstance(expected, (dates.Date, datetime.datetime, datetime.date)):
        return assertAlmostEqualValue(
            dates.Date(test).unix,
            dates.Date(expected).unix,
            msg=msg,
            digits=digits,
            places=places,
            delta=delta
        )

    if not is_number(expected):
        # SOME SPECIAL CASES, EXPECTING EMPTY CONTAINERS IS THE SAME AS EXPECTING NULL
        if is_list(expected) and len(expected) == 0 and test == None:
            return
        if is_data(expected) and not expected.keys() and test == None:
            return
        if test != expected:
            raise AssertionError(expand_template("{{test|json}} != {{expected|json}}", locals()))
        return
    elif not is_number(test):
        try:
            # ASSUME IT IS A UTC DATE
            test = dates.parse(test).unix
        except Exception as e:
            raise AssertionError(expand_template("{{test|json}} != {{expected}}", locals()))

    # WE NOW ASSUME test IS A NUMBER
    test = float(test)

    num_param = 0
    if digits != None:
        num_param += 1
    if places != None:
        num_param += 1
    if delta != None:
        num_param += 1
    if num_param > 1:
        raise TypeError("specify only one of digits, places or delta")

    if digits is not None:
        with suppress_exception:
            diff = log10(abs(test-expected))
            if diff < digits:
                return

        standardMsg = expand_template("{{test|json}} != {{expected|json}} within {{digits}} decimal places", locals())
    elif delta is not None:
        if abs(test - expected) <= delta:
            return

        standardMsg = expand_template("{{test|json}} != {{expected|json}} within {{delta}} delta", locals())
    else:
        if places is None:
            places = 15

        with suppress_exception:
            diff = mo_math.log10(abs(test-expected))
            if diff == None:
                return  # Exactly the same
            if diff < mo_math.ceiling(mo_math.log10(abs(test)))-places:
                return

        standardMsg = expand_template("{{test|json}} != {{expected|json}} within {{places}} places", locals())

    raise AssertionError(coalesce(msg, "") + ": (" + standardMsg + ")")


def is_null_op(v):
    return v.__class__.__name__ == "NullOp"


_original_assertEqual = TestCase.assertEqual


def assertEqual(self, test, expected, *args, **kwargs):
    return _original_assertEqual(self, expected, test, *args, **kwargs)


TestCase.assertEqual = assertEqual


def add_error_reporting(suite):
    """
    Both unittest and pytest have become sophisticated enough to hide
    the problems cause by a test failure. Making debugging difficult.
    This method ensures a detailed error message is logged
    :param suite: The TestCase class (as @decorator)
    """
    def add_handler(function):
        test_name = get_function_name(function)
        def error_hanlder(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except SkipTest as cause:
                raise cause
            except Exception as cause:
                Log.warning(f"{test_name} failed", cause)
                raise cause

        return error_hanlder

    if not hasattr(suite, "FuzzyTestCase.__modified__"):
        setattr(suite, "FuzzyTestCase.__modified__", True)
        # find all methods, and wrap in exceptin handler
        for name, func in vars(suite).items():
            if name.startswith("test"):
                h = add_handler(func)
                h.__name__ = get_function_name(func)
                setattr(suite, name, h)
    return suite
