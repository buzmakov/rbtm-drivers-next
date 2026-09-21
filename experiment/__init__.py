from flask import Flask

from hwrpc import configure_logging

# Корневой логгер → logs/hwrpc_main.log (RPC-клиент и всё, что пишет через logging.*)
configure_logging('main')

from . import tomologger  # noqa: E402
tomo_logger = tomologger.tomologger

from . import routes

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.register_blueprint(routes.bp_main)
    app.register_blueprint(routes.bp_tomograph)

    return app
