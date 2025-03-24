from flask import Flask

from . import tomologger
tomo_logger = tomologger.tomologger

from . import routes

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.register_blueprint(routes.bp_main)
    app.register_blueprint(routes.bp_tomograph)

    return app
