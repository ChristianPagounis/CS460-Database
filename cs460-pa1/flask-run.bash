#!/bin/bash

echo -n Setting Flask app...
export FLASK_APP=app.py
echo " Done"

echo -n Setting Flask to debug mode...
export FLASK_ENV=development
echo " Done"

echo Starting ${FLASK_APP}...
flask run
