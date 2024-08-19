from smartforecasting.celery_config import make_celery
from celery.result import AsyncResult
from flask import Flask, request, jsonify, Blueprint
from config import Config
from constants import BASE_PATH

bp = Blueprint('status', __name__)
celery = Config.celery

@bp.route(f'{BASE_PATH}/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    file: ../../docs/get_status.yaml
    """
    task = AsyncResult(task_id, app=celery)
    if task.state == 'PENDING':
        response = {"status": task.state}
    elif task.state == 'PROGRESS':
        percent_complete = (
            (task.info.get('current model', 0) + task.info.get('current', 0) / task.info.get('total', 1)) 
            / task.info.get('total models', 1) * 100
        )
        response = {
            "status": "In Progress",
            # "current": task.info.get('current', 0),
            # "total": task.info.get('total', 1),
            "progress": f"{percent_complete:.0f}%"
        }
    else:
        response = {"status": task.state, "result": str(task.result)}
    return jsonify(response)