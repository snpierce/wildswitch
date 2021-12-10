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
        batters = list(cur.fetchall())
        
        return render_template("batter.html", batters=batters)
    else:
        cur.execute("SELECT * FROM Pitching WHERE playerID = ?", (playerID,))
        pitchers = list(cur.fetchall())

        return render_template("pitcher.html", pitchers=pitchers)
    

# generates and returns list of searched user's owned player cards
def generate_user(username):
        batters = []
        pitchers = []

        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 1", (username,))
        batterInfo = list(cur.fetchall())

        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 0", (username,))
        pitcherInfo = list(cur.fetchall())

        for i in range(len(batterInfo)):
            cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (batterInfo[i][0], batterInfo[i][1],))
            batters.append(list(cur.fetchall()))

        
        for i in range(len(pitcherInfo)):
            cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (pitcherInfo[i][0], pitcherInfo[i][1],))
            pitchers.append(list(cur.fetchall()))

        cur.execute("SELECT cash FROM Users WHERE username = ?", (username,))
        cash = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ?", (username,))
        cardCount = int(cur.fetchone()[0])
        
        return render_template("mycards.html", batters=batters, pitchers=pitchers, cash=cash, cardCount=cardCount, username=username)

# converts amount into usd format
def usd(amount):
    """Format value as USD."""
    value = float(amount)
    return f"${value:,.2f}"

# command 0 creates a random list of 8 players and stores that group until called with command 0 again
# command 1 returns the currently stored list
def build_market():
     # clears previous market
    cur.execute("DELETE FROM Market")
    con.commit()

    # initialize players
    cur.execute("SELECT * FROM Pitching WHERE status = '0' ORDER BY RANDOM() LIMIT 4")
    pitcherGroup = list(cur.fetchall())

    cur.execute("SELECT * FROM Batting WHERE status = '0' ORDER BY RANDOM() LIMIT 4")
    batterGroup = list(cur.fetchall())
    # make a two-step code: create and exit, create and save
    for i in range(4):
        cur.execute("INSERT INTO Market (playerID, fullName, year, position, status, value) VALUES (?, ?, ?, 0, ?, ?)", (pitcherGroup[i][0], pitcherGroup[i][2], pitcherGroup[i][1], pitcherGroup[i][24], pitcherGroup[i][23],))

    for i in range(4):
        cur.execute("INSERT INTO Market (playerID, fullName, year, position, status, value) VALUES (?, ?, ?, 1, ?, ?)", (batterGroup[i][0], batterGroup[i][2], batterGroup[i][1], batterGroup[i][18], batterGroup[i][17],))

    con.commit()


        


    

