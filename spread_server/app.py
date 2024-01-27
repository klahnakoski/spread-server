# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import os
import threading

import flask
from flask import Flask, Response
from werkzeug.serving import make_server

from mo_files import File
from mo_future import text
from mo_kwargs import override
from mo_logs import Log, constants, machine_metadata, startup
from mo_threads import stop_main_thread
from mo_threads.threads import MAIN_THREAD, register_thread, wait_for_shutdown_signal
from pyLibrary.env.flask_wrappers import cors_wrapper, add_version, setup_flask_ssl
from spread_server.actions import static, response, query

APP_NAME = "SpreadServer"
OVERVIEW = "Simple message"

config = None


class SpreadServerApp(Flask):
    def run(self, *args, **kwargs):
        # ENSURE THE LOGGING IS CLEANED UP
        try:
            Flask.run(self, *args, **kwargs)
        except BaseException as e:  # MUST CATCH BaseException BECAUSE argparse LIKES TO EXIT THAT WAY, AND gunicorn WILL NOT REPORT
            if e.args and not e.args[0]:
                pass  # ASSUME NORMAL EXIT
            else:
                Log.warning(
                    "Serious problem with SpreadServer service construction!  Shutdown!",
                    cause=e,
                )
        finally:
            Log.stop()
            stop_main_thread()

    def process_response(self, response):
        del response.headers["Date"]
        del response.headers["Server"]
        return response


def setup_flask(flask_app, flask_config):
    @flask_app.route("/", defaults={"path": ""}, methods=["OPTIONS", "HEAD"])
    @flask_app.route("/<path:path>", methods=["OPTIONS", "HEAD"])
    @cors_wrapper
    def _head(path):
        return Response(b"", status=200)

    @flask_app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
    @flask_app.route("/<path:path>", methods=["GET", "POST"])
    @cors_wrapper
    @register_thread
    def _default(path):
        return Response(OVERVIEW, status=200, headers={"Content-Type": "text/html"})

    flask_app.add_url_rule("/query/sql", None, query.sql)
    flask_app.add_url_rule("/response/<path:filename>", None, response.download)
    flask_app.add_url_rule("/favicon.ico", None, static.send_favicon)

    add_version(flask_app, "https://github.com/klahnakoski/spread-server/tree")

    if flask_config.port and config.args.process_num:
        flask_config.port += config.args.process_num

    # TURN ON /exit FOR WINDOWS DEBUGGING
    if flask_config.debug or flask_config.allow_exit:
        flask_config.allow_exit = None
        Log.warning("SpreadServer is in debug mode")
        flask_app.add_url_rule("/exit", "exit", _exit)

    if flask_config.ssl_context:
        if config.args.process_num:
            Log.error("can not serve ssl and multiple Flask instances at once")
        setup_flask_ssl(APP_NAME, flask_app, flask_config)

    # ENSURE MAIN THREAD SHUTDOWN TRIGGERS Flask SHUTDOWN
    MAIN_THREAD.stopped.then(exit)


@register_thread
def _exit():
    Log.note("Got request to shutdown")
    try:
        return Response(OVERVIEW, status=400, headers={"Content-Type": "text/html"})
    finally:
        shutdown = flask.request.environ.get("werkzeug.server.shutdown")
        if shutdown:
            shutdown()
        else:
            Log.warning("werkzeug.server.shutdown does not exist")


class ServerThread(threading.Thread):

    def __init__(self, host, port, app, **kwargs):
        threading.Thread.__init__(self)
        self.srv = override(make_server)(host, port, app, **kwargs)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.srv.serve_forever()
        Log.note("shutdown of server on port {{port}}", port=self.srv.port)

    def stop(self):
        try:
            self.srv.shutdown()
        except Exception:
            pass


if __name__ in ("__main__", "spread_server.app"):
    try:
        config = startup.read_config(
            default_filename=os.environ.get("SPREAD_SERVER_CONFIG"),
            defs=[{
                "name": ["--process_num", "--process"],
                "help": "Additional port offset (for multiple Flask processes",
                "type": int,
                "dest": "process_num",
                "default": 0,
                "required": False,
            }],
        )

        constants.set(config.constants)
        Log.start(config.debug)

        File.new_instance(f"{APP_NAME}.pid").write(text(machine_metadata().pid))

        # MAKE FLASK TALK LESS TO logging
        import logging

        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        if config.flask:
            flask_app = SpreadServerApp(__name__)
            setup_flask(flask_app, config.flask)

            server_thread = ServerThread(app=flask_app, **config.flask)
            server_thread.start()
            wait_for_shutdown_signal(allow_exit=True)
            server_thread.stop()
    except BaseException as cause:  # MUST CATCH BaseException BECAUSE argparse LIKES TO EXIT THAT WAY, AND gunicorn WILL NOT REPORT
        Log.error(
            "Serious problem with SpreadServer service construction!  Shutdown!", cause=cause
        )
        stop_main_thread()

