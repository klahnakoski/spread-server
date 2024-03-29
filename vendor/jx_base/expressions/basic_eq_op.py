# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http:# mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from jx_base.expressions.base_inequality_op import BaseInequalityOp


class BasicEqOp(BaseInequalityOp):
    """
    PLACEHOLDER FOR BASIC `==` OPERATOR (CAN NOT DEAL WITH NULLS)
    """
    op = "basic.eq"


    def __call__(self, row, rownum=None, rows=None):
        return self.lhs(row, rownum, rows) == self.rhs(row, rownum, rows)