import requests
import pytest
import time

# Example POST request with JSON payload
url = 'http://127.0.0.1:5000'
csv_filepath = '../tests/01.csv'
datasource_id = None
process_file_task_id = None
training_task_id = None

def test_create_datasource():
    global datasource_id
    endpoint = '/api/data-sources'
    headers = {'Content-Type': 'application/json'}

    payload = {'name': 'db-001', 'period': {'type': 'day', 'value': 1}}
    print(payload)
    response = requests.post(url + endpoint, json=payload, headers=headers)
    print(response.json())
    assert response.status_code == 200
    assert 'id' in response.json()
    datasource_id = response.json()['id']

def test_create_datasource_wrong_period_type():
    global datasource_id
    endpoint = '/api/data-sources'
    headers = {'Content-Type': 'application/json'}

    payload = {'name': 'db-001', 'period': {'type': 'thour', 'value': 1}}
    response = requests.post(url + endpoint, json=payload, headers=headers)

    assert response.status_code == 400

def test_upload_file():
    global process_file_task_id, datasource_id
    print(datasource_id)
    endpoint = f'/api/data-sources/{datasource_id}/initialization'

    with open(csv_filepath, 'r') as file:  # Open in binary mode 'rb'
        files = {'file': file}
        response = requests.post(url + endpoint, files=files)
    print(response.json())
    print(response.status_code)
    process_file_task_id = response.json()['task_id']
    assert response.status_code == 202

def test_progress_upload_file():
    global process_file_task_id
    endpoint = f'/api/status/{process_file_task_id}'
    print('task_id:', process_file_task_id)
    response = requests.get(url + endpoint)
    print(response.json())
    assert response.json()['status'] == 'PENDING'
    time.sleep(3)

    response = requests.get(url + endpoint)
    print(response.json())
    print(response.status_code)

    assert response.json()['status'] == 'SUCCESS'

def test_upload_file_no_file_part():
    endpoint = f'/api/data-sources/{datasource_id}/initialization'

    response = requests.post(url + endpoint)
    print(response.json())

    assert response.status_code == 400

def test_upload_file_wrong_id():
    endpoint = f'/api/data-sources/{datasource_id}h/initialization'

    with open(csv_filepath, 'r') as file:  # Open in binary mode 'rb'
        files = {'file': file}
        response = requests.post(url + endpoint, files=files)
        print(response.json())

    assert response.status_code == 404

def test_add_data_point():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    payload = {"ts": "2023-05-05", "value": 197}

    response = requests.post(url + endpoint, json=payload)
    assert response.status_code == 200

def test_add_data_point_wrong_date():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    payload = {"ts": "2023-05-55", "value": 197}

    response = requests.post(url + endpoint, json=payload)
    assert response.status_code == 400

def test_add_data_point_wrong_value_type():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    payload = {"ts": "2023-05-05", "value": 'one'}

    response = requests.post(url + endpoint, json=payload)
    assert response.status_code == 400

def test_add_data_point_wrong_id():
    endpoint = f'/api/data-sources/{datasource_id}h/data-points'

    payload = {"ts": "2023-05-05", "value": 197}

    response = requests.post(url + endpoint, json=payload)
    assert response.status_code == 404


def test_get_data_point():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    params = {"ts": "2023-01-11"}
    print(url + endpoint)
    response = requests.get(url + endpoint, params=params)
    print(response.json())
    assert response.status_code == 200

def test_get_data_point_no_data_point_match():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    params = {"ts": "2022-01-11"}
    print(url + endpoint)
    response = requests.get(url + endpoint, params=params)
    print(response.json())
    assert response.status_code == 500

def test_update_data_point():
    endpoint = f'/api/data-sources/{datasource_id}/data-points'

    payload = {"ts": "2023-01-11", "value": 197}

    response = requests.put(url + endpoint, json=payload)
    assert response.status_code == 200

    response = requests.get(url + endpoint, params={'ts': payload.get('ts')})
    print(response.json())
    assert response.json()['value'] == 197


def test_train_datasource():
    global training_task_id, datasource_id
    endpoint = f'/api/data-sources/{datasource_id}/training'

    payload = {"models": ['auto-regression']}

    response = requests.post(url + endpoint, json=payload)
    print(response.json())
    print(response.status_code)
    training_task_id = response.json()['task_id']
    assert response.status_code == 202

def test_train_datasource_wrong_algorithm():
    global training_task_id, datasource_id
    endpoint = f'/api/data-sources/{datasource_id}/training'

    payload = {"models": ['auto-ression']}

    response = requests.post(url + endpoint, json=payload)
    assert response.status_code == 400

def test_progress_train_datasource():
    global training_task_id
    endpoint = f'/api/status/{training_task_id}'
    print('task_id:', training_task_id)
    response = requests.get(url + endpoint)
    print(response.json())
    assert response.json()['status'] in ['PENDING', 'SUCCESS']
    time.sleep(5)

    response = requests.get(url + endpoint)
    print(response.json())
    print(response.status_code)

    assert response.json()['status'] == 'SUCCESS'

def test_get_forecast():
    endpoint = f'/api/data-sources/{datasource_id}/forecasting'
    
    # Use query parameters instead of JSON payload
    params = {"date": "2024-01-02", "steps": 2}
    
    print(url + endpoint)
    response = requests.get(url + endpoint, params=params)
    print(response.json())
    assert response.status_code == 200
