import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="divya@4257",  # ⚠️ change this
        database="PLANNERIA"
    )
    return conn