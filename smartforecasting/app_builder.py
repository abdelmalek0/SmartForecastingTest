from flask import Flask
from flasgger import Swagger
from flask_cors import CORS
from config import Config
from constants import SWAGGER_TEMPLATE


def create_app():
    app = Flask(__name__)
    CORS(app)
    swagger = Swagger(app, template=SWAGGER_TEMPLATE)

    # Setting up Redis and Celery and DB
    Config.initialize(app)

    # Register blueprints
    from routes import status, datasources, datapoints, forecasting
    app.register_blueprint(status.bp)
    app.register_blueprint(datasources.bp)
    app.register_blueprint(datapoints.bp)
    app.register_blueprint(forecasting.bp)
    
    return app, Config.celery