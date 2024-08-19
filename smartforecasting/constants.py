from typing import Final

BASE_PATH: Final[str] = '/api/v1'
DB_CONFIG_FILENAME: Final[str] = 'db.json'
MODULE: Final[str] = 'app'
CELERY_BROKER_URL: Final[str] = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND: Final[str] = 'redis://localhost:6379/0'

SWAGGER_TEMPLATE: Final[str] = {
    "swagger": "2.0",
    "info": {
        "title": "SmartForecasting API",
        "description": "API designed to forecast product consumption and sales trends, empowering businesses to make data-driven decisions and stay ahead of the competition.",
        "version": "0.1.0"
    },
}