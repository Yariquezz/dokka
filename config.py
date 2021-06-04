
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = './upload_folder'
DISTANCE_MATRIX = "https://maps.googleapis.com/maps/api/distancematrix/json"


class Configuration(object):
    DEBUG = os.environ.get('DEBUG', default=1)
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', default=0)
    DB_USER = os.environ.get('DB_USER', default='username')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', default='password')
    DB_HOST = os.environ.get('DB_HOST', default='localhost')
    DB_PORT = os.environ.get('DB_PORT', default='5432')
    DB_NAME = os.environ.get('DB_NAME', default='dokka_test')
    DB_DRIVER = os.environ.get('DB_DRIVER', default='postgresql')
    API_KEY = os.environ.get('API_KEY', default='')
    SQLALCHEMY_DATABASE_URI = f'{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', default='redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

