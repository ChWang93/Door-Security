import pymysql
import mail
import sys

def ReplicatedDB():
    try:
        conn = pymysql.connect(
            db='inventory',
            user='root',
            passwd='Karamay54',
            host='127.0.0.1',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except:
        return False


def Server():
    try:
        conn = pymysql.connect(
            db='inventory',
            user='root',
            passwd='95U3GYNb5uDN;yVb.q',
            host='db-server.d3.diam-int.com',
            connect_timeout= 5
        )
        return conn
    except:
        conn = ReplicatedDB()
        return conn
