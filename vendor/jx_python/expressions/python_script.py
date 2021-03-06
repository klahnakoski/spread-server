# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http:# mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from __future__ import absolute_import, division, unicode_literals

from jx_base.expressions import (
    FALSE,
    NULL,
    ONE,
    PythonScript as PythonScript_,
    TRUE,
    ZERO,
    Expression,
)
from jx_base.utils import coalesce
from jx_python.expressions import _utils, Python
from mo_logs import Log


class PythonScript(PythonScript_):
    __slots__ = ("miss", "data_type", "expr", "frum", "many")

    def __init__(self, type, expr, frum, miss=None, many=False):
        Expression.__init__(self, None)
        if miss not in [None, NULL, FALSE, TRUE, ONE, ZERO]:
            if frum.lang != miss.lang:
                Log.error("logic error")

        self.miss = coalesce(miss, FALSE)
        self.data_type = type
        self.expr = expr
        self.many = many  # True if script returns multi-value
        self.frum = frum  # THE ORIGINAL EXPRESSION THAT MADE expr

    def __str__(self):
        missing = self.miss.partial_eval(Python)
        if missing is FALSE:
            return self.partial_eval(Python).to_python().expr
        elif missing is TRUE:
            return "None"

        return "None if (" + missing.to_python().expr + ") else (" + self.expr + ")"

    def __add__(self, other):
        return str(self) + str(other)

    def __radd__(self, other):
        try:
            a = str(other)
            b = str(self)
            return a + b
        except Exception as cause:
            b = str(self)
            return ""

    def to_python(self, not_null=False, boolean=False):
        return self

    def missing(self, lang):
        return self.miss

    def __data__(self):
        return {"script": self.script}

    def __eq__(self, other):
        if not isinstance(other, PythonScript_):
            return False
        elif self.expr == other.frum:
            return True
        else:
            return False


_utils.PythonScript = PythonScript
