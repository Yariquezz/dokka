
import pandas as pd
import aiohttp
from config import DISTANCE_MATRIX
import asyncio
import json
import uuid
import os
from flask import Flask
from flask import request, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Configuration
from celery import Celery
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER
import logging

# initialize the Flask app
app = Flask(__name__)
# initialize logs
logging.basicConfig(
    filename='dokka_test.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)
logger = logging.getLogger(__name__)

logger.debug("Init application")
# import configs
app.config.from_object(Configuration)
# initialize database
db = SQLAlchemy(app)
# setup Celery as broker
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


# Database Model
class Addresses(db.Model):
    task_id = db.Column(   # primary key as task_id
        db.String,
        primary_key=True
    )
    status = db.Column(    # task status (running, done, failed)
        db.String(20),
        nullable=False
    )
    data = db.Column(     # Text field where saved JSON file as string. In case not all databases support JSON field.
        db.Text
    )

    def __init__(self, task_id, status, data):
        self.task_id = task_id
        self.status = status
        self.data = data

    def __repr__(self):
        return f'Task {self.task_id} Status: {self.status}'


def allowed_file(filename):
    """
    Support method for check filename from request. If filename not csv return FALSE
    :param filename: filename get from POST request.
    :return: True or False
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


# API
@app.route("/api/calculateDistance", methods=["POST"])
def calculate_distance():
    """
    API endpoint expecting csv file with POINTS and locations
    :return: JSON response with task id and task status or errors
    """
    results = []

    # check is file exist in request
    if 'file' not in request.files:
        results.append(
            {
                'error': 'Not found expected csv file'
            }
        )
        logger.error('Not found expected csv file')
        return jsonify(results), 400

    # check is filename not empty
    file = request.files['file']
    if file.filename == '':
        # return error with no selected
        results.append(
            {
                'error': 'No selected file'
            }
        )
        logger.debug("No selected file")

    # check is a file exist and file extension is allowed
    if file and allowed_file(file.filename):
        # temporary save file to the upload folder
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(str(uuid.uuid4())))
        file.save(file_path)
        task = links_points.apply_async([file_path])
        results.append(
            {
                "task_id": task.id,
                "status": "running",
            }
        )
        logger.debug("File is allowed")
        logger.info(f"Task {task.id} is running")
    else:
        # returns error with file not allowed
        results.append(
            {
                'error': 'File not allowed'
            }
        )
        logger.debug("File not allowed")
        return jsonify(results), 400

    return jsonify(results), 200


@app.route("/api/getResult", methods=["GET"])
def get_result():
    """
    API to retrieve a single stored task result object identified by “result_id”
    :return: JSON with task_id, status and points and links with distances or error
    """
    results = []
    # check is 'result_id' in GET params
    if 'result_id' in request.args:
        task_id = request.args['result_id']
        logger.debug(f"Task {task_id} requested")
        # Send query to DB to search task by task id
        data = Addresses.query.get(task_id)
        # check is task exists
        if data:
            # return task wih data
            results.append(
                {
                    "task_id": data.task_id,
                    "status": data.status,
                    "data": json.loads(data.data),  # export string data to json and add to response
                }
            )
            logger.debug(f"Task {task_id} requested")
        else:
            # return task not found error
            results.append(
                {
                    'error': 'Task not found'
                }
            )
            logger.debug(f"Task {task_id} not found")
            return jsonify(results), 404

    else:
        # return error 'cause results_id not found in parameters
        results.append(
            {
                'error': 'Not found expecting result_id parameter'
            }
        )
        return jsonify(results), 400

    return jsonify(results), 200


async def reverse_gecode(file):
    """
    Async method pasre csv file and send async request to Gecode API
    :param file: path to folder where temporary saved csv file
    :return: dict with points and points
    """
    data = {
        "points": [],
        "links": [],
    }
    names = []
    # try to parse csv file to pandas dataframe and remove temp file
    try:
        dataframe = pd.read_csv(file)
        os.remove(file)
    except Exception as err:
        logger.error("Failed to parse csv file via %s" % err)
        return data
    logger.debug("Starts aiohttp session")
    # run aiohttp session
    async with aiohttp.ClientSession() as session:
        # iterate by dataframe rows
        for index, row in dataframe.iterrows():
            for inner_index, inner_row in dataframe.iterrows():
                # pass same points and or reverse directions
                if row['Point'] == inner_row['Point'] or (str(row['Point']) + str(inner_row['Point']))[::-1] in names:
                    pass
                else:
                    # create request to Gecode API to get distance and location address
                    names.append(str(row['Point']) + str(inner_row['Point']))
                    params = {
                        "origins": f"{row['Latitude']}, {row['Longitude']}",
                        "destinations": f"{inner_row['Latitude']}, {inner_row['Longitude']}",
                        "units": "metric",
                        "key": app.config['API_KEY'],
                    }
                    logger.debug("Send request to %s" % DISTANCE_MATRIX)
                    async with session.get(
                        url=DISTANCE_MATRIX,
                        params=params,
                    ) as response:
                        resp = await response.json()
                        try:
                            data["points"].append(
                                {
                                    "name": row['Point'],
                                    "address": resp['origin_addresses'],
                                }
                            )
                            data["links"].append(
                                {
                                    "name": f"{row['Point']}{inner_row['Point']}",
                                    "distance": resp['rows'][0]['elements'][0]['distance']['value']
                                }
                            )
                        except Exception as err:
                            logger.error("Can not connect to API via %s" % err)
                            logger.debug("Return empty response")
                            data = {}
    return data


@celery.task(bind=True)
def links_points(self, file):
    """
    Celery task get file path and call async fuction to send reqests on Geocode API
    :param file: path to file from POST request.
    :return: dict with task status
    """
    data = {}
    try:
        task_id = self.request.id
        logger.info("Run task %s" % task_id)
        task_status = "STARTING"
        data_to_save = json.dumps(data)
        task = Addresses(
            task_id,
            task_status,
            data_to_save
        )
        db.session.add(task)
        db.session.commit()
        # get pandas dataframe from csv file
        data = asyncio.run(reverse_gecode(file))
        # update state to PROGRESS and status to running
        self.update_state(
            state="PROGRESS",
            meta={
                # 'current': 50,
                # 'total': 100,
                'status': 'running'
            }
        )
        logger.info("Task %s running" % task_id)
    except Exception as err:
        logger.warning("Task %s failed" % task_id)
        logger.error("Task failed via " % err)
        results = {
            "Error": err
        }
        # save failed status to database
        task_id = self.request.id
        db.session.query(Addresses).filter(Addresses.task_id == task_id).update(
            {
                'status': "failed",
                'data': "{}",
            },
            synchronize_session='evaluate'
        )
        db.session.commit()
        self.update_state(
            state="FAILURE",
            meta={
                'current': 0,
                'total': 100,
                'status': 'failed'
            }
        )
    else:
        # update task status on database
        task_id = self.request.id
        db.session.query(Addresses).filter(Addresses.task_id == task_id).update(
            {
                'status': "done",
                'data': json.dumps(data),
            },
            synchronize_session='evaluate'
        )
        db.session.commit()
        results = {
            "Success": "Ok"
        }
        self.update_state(
            state="SUCCESS",
            meta={
                'current': 100,
                'total': 100,
                'status': 'done'
            }
        )
        logger.info("Task %s done" % task_id)
    return {
        'current': 100,
        'total': 100,
        'status': 'done',
        'result': results
    }
