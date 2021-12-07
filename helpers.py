import os
import requests
import urllib.parse
import sqlite3

from datetime import date
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

# generates and returns player information when searched
def generate_card(playerID, command):
    if command == 1:
        cur.execute("SELECT * FROM Batting WHERE playerID = ?", (playerID,))
        players = list(cur.fetchall())
        return render_template("batter.html", players=players)
    else:
        cur.execute("SELECT * FROM Pitching WHERE playerID = ?", (playerID,))
        players = list(cur.fetchall())
        return render_template("pitcher.html", players=players)
    

# generates and returns list of searched user's owned player cards
def generate_user(username):
    players = []

    cur.execute("SELECT playerID FROM Cards WHERE username = ?", (username,))
    rows = cur.fetchall()

    for i in range(len(rows)):
        cur.execute("SELECT * FROM People WHERE playerID = ?", (rows[i][0],))
        info = cur.fetchall()
        players.append(info)

    return render_template("batter.html", players=players)

# converts amount into usd format
def usd(amount):
    """Format value as USD."""
    value = float(amount)
    return f"${value:,.2f}"

# command 0 creates a random list of 8 players and stores that group until called with command 0 again
# command 1 returns the currently stored list
def market():
    # initialize players
    cur.execute("SELECT * FROM People WHERE status = '0' ORDER BY RANDOM() LIMIT 8")
    group = list(cur.fetchall())

    # make a two-step code: create and exit, create and save
    return group
   
        


        


    

