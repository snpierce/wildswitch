import os
import requests
import urllib.parse
import sqlite3

from flask import redirect, render_template, request, session
from functools import wraps

con = sqlite3.connect("wildswitch.sqlite", check_same_thread=False)
cur = con.cursor()

# Copied and pasted from PSet9 Finance
def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# I guess we'll keep for now while we're working, but we can change it.
def apology(message, code=400):
    return render_template("apology.html", message=message), code

def generate_card(playerID):
    cur.execute("SELECT * FROM People WHERE playerID = ?", (playerID,))
    info = list(cur.fetchall())

    return render_template("market.html", info=info)

def generate_user(username):
    players = []
    cur.execute("SELECT * FROM Cards WHERE username = ?", (username,))
    cards = list(cur.fetchall())

    cur.execute("SELECT playerID FROM Cards WHERE username = ?", (username,))
    rows = cur.fetchall()

    for i in range(len(rows)):
        cur.execute("SELECT * FROM People WHERE playerID = ?", (rows[i][0],))
        info = cur.fetchall()
        players.append(info)
    
    length = len(players)

    return render_template("user.html", players=players, length=length)

    

