# DOKKA. Hands-on test 
# Usage
_____
Clone the repository:

    git clone https://github.com/Yariquezz/dokka.git
    cd dokka

Create virtualenv:

    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

Install databases:
By default, I am using Postgresql, but you can use whatever you want!

    sudo apt install postgresql
    sudo -u postgres psql
    postgres=# create database dokka_test;
    postgres=# create user username with encrypted password 'password';
    postgres=# grant all privileges on database mydb to myuser;

Install Redis for Celery:

    sudo apt install redis

Export environment variables:

    export DEBUG=1
or use 0 or False for exit from DEBUG mode

In configs used settings for Postgres. Do not forget change if you are using different DB:

    export DB_USER=username
    export DB_PASSWORD=password
    export DB_HOST=localhost
    export DB_PORT=5432
    export DB_NAME=dokka_test
    export DB_DRIVER=postgresql

Set redis settings for Celery:

    export CELERY_BROKER_URL='redis://localhost:6378'
    exportCELERY_RESULT_BACKEND='redis://localhost:6378/1

As geocoding service used Google Maps API. For successful responses you need to register in Google and add API key to environment variables. 

    export API_KEY="paste_your_google_maps_api_key_here"

Init database:
    
    python database.py

Run the sample server:
    
    python main.py
Run Celery 
    
    celery -A application.celery worker -I application --pool=solo -E

Send request to test API server 
    
    curl GET 'http://localhost:5000/api/getResult?result_id=818b47fa-8956-4568-846d-846215070963' -vvv 
    curl -F 'file=@/path/to/file' http://localhost:5000/api/calculateDistance -vvv
  

