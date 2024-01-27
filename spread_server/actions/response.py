# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

import flask
from flask import send_from_directory

from mo_files import File
from mo_logs import Log
from mo_threads.threads import register_thread
from pyLibrary.env.flask_wrappers import cors_wrapper
from spread_server.actions import record_request

RESPONSE_DIRECTORY = File("spread_server/responses")


@cors_wrapper
@register_thread
def download(filename):
    """
    DOWNLOAD FILE CONTENTS
    :param filename:  URL PATH
    :return: Response OBJECT WITH FILE CONTENT
    """
    try:
        record_request(flask.request, None, flask.request.get_data(), None)
        return send_from_directory(
            RESPONSE_DIRECTORY.abs_path, filename, as_attachment=True
        )
    except Exception as cause:
        Log.error("Could not get file {{file}}", file=filename, cause=cause)
