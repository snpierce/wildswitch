import sqlite3

from flask import redirect, render_template, session, g
from functools import wraps


# also taken from https://flask.palletsprojects.com/en/2.0.x/patterns/sqlite3/ as helper 
# function to either open or check if connection is open
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("wildswitch.sqlite", check_same_thread=False)
    return db

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

# apology template that prints parameter message
def apology(message, code=400):
    return render_template("apology.html", message=message), code
    

# converts amount into usd format (from finance)
def usd(amount):
    """Format value as USD."""
    value = float(amount)
    return f"${value:,.2f}"


# command 0 creates a random list of 8 players and stores that group until called with command 0 again
# command 1 returns the currently stored list
def build_market():
    cur = get_db().cursor()

     # clears previous market
    cur.execute("DELETE FROM Market")
    get_db().commit()

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

    get_db().commit()


        


    

