import mysql.connector

def get_cursor():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MYSqL@4869,260126$#",   # your password
        database="loan_db",
        autocommit=True
    )
    return db, db.cursor()