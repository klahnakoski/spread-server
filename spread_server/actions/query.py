# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from __future__ import absolute_import, division, unicode_literals

from flask import Response
from mo_json import value2json

from mo_files import File, mimetype, URL
from mo_math import randoms
from mo_threads.threads import register_thread
from pyLibrary.env.flask_wrappers import cors_wrapper
from mo_sql_parsing import parse

from spread_server.dispatch import execute

HOST = URL("http://localhost:5000/responses")
RESPONSE_DIRECTORY = File("spread_server/responses")


@cors_wrapper
@register_thread
def sql(content):
    # validate
    try:
        parse(content)
    except Exception as cause:
        return Response(value2json(cause), 400, headers={"Content-Type": mimetype.JSON})

    name = f"{randoms.base64(20)}.sqlite"
    # define new database file
    output_file = RESPONSE_DIRECTORY / name
    execute(content, output_file)

    return Response(None, 201, headers={"Location": HOST/name})
