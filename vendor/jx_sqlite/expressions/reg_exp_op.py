# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http:# mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from jx_base.expressions import RegExpOp as RegExpOp_
from jx_sqlite.expressions._utils import check, SQLang, SqlScript, OrOp
from mo_sqlite import TextSQL, ConcatSQL
from mo_json import JX_BOOLEAN


class RegExpOp(RegExpOp_):
    @check
    def to_sql(self, schema):
        pattern = self.pattern.partial_eval(SQLang).to_sql(schema)
        expr = self.expr.partial_eval(SQLang).to_sql(schema)
        return SqlScript(
            jx_type=JX_BOOLEAN,
            expr=ConcatSQL(expr.expr, TextSQL(" REGEXP "), pattern.expr),
            frum=self,
            miss=OrOp(expr.missing(SQLang), pattern.missing(SQLang)),
            schema=schema,
        )
