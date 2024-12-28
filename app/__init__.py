from flask import Flask
import mysql.connector
from config import SECRET_KEY, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

app = Flask(__name__)
app.secret_key = SECRET_KEY

def get_db_connection():
    mydb = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )
    return mydb

from app import routes