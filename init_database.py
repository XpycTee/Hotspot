# init_db.py
from flask import Flask
from app.database import db
from settings import Config

app = Flask("DB Initiator")

Config.init_db(app, db)
