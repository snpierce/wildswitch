import os, csv
import datetime
import sqlite3
import jinja2


from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, generate_card, generate_user, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

con = sqlite3.connect("wildswitch.sqlite", check_same_thread=False)
cur = con.cursor()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/buy")
@login_required
def buy():
    if request.method == "POST":
         cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
         cash = int(cur.fetchone())
         
    else:
        cur.execute("SELECT playerID FROM People ORDER BY RAND() LIMIT 5")
        players = list(cur.fetchall())

        return render_template("buy.html", players=players)


@app.route("/")
@login_required
def index():
    text = cur.execute("SELECT * FROM People WHERE playerID = 'aardsd01a'")
    return render_template("index.html", text=text)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        search = request.form.get("search")
        option = int(request.form.get("criteria"))

        if option == 1:
            cur.execute("SELECT COUNT(*) FROM People WHERE LOWER(playerID) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT playerID FROM People WHERE LOWER(playerID) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]
                return generate_card(playerID)
            else:
                return apology("Not a valid player ID.")
        elif option == 2:
            cur.execute("SELECT COUNT(*) FROM People WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT playerID FROM People WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]
                return generate_card(playerID)
            else:
                return apology("Not a valid player name.")
        else:
            cur.execute("SELECT COUNT(*) FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT username FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
                username = cur.fetchone()[0]

                return generate_user(username)
            else:
                return apology("Not a valid player name.")
    else:
        return render_template("search.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username.", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password.", 403)

        # Query database for username
        cur.execute("SELECT * FROM Users WHERE username = ?", (request.form.get("username"),))
        rows = list(cur.fetchall())

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # when register button is clicked
    if request.method == "POST":

        # checks that all forms have valid input
        if not request.form.get("username"):
            return apology("Please enter username.")
        elif not request.form.get("password"):
            return apology("Please enter password.")
        elif not request.form.get("confirmation"):
            return apology("Please enter confirmation.")

        # checks if username is already in users table, stores 1 if found, 0 if not
        cur.execute("SELECT COUNT(*) AS 'count' FROM Users WHERE username = ?", (request.form.get("username"),))
        count = float(cur.fetchone()[0])

        # if username already in users table, return apology message 
        if 0.0 != count:
            return apology("Username taken.")
        
        # checks if password and confirmation match, return apology if don't
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match.")

        # hash password
        hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # if passes all the checks, add username+hash to users table
        cur.execute("INSERT INTO Users (username, password, cash) VALUES (?, ?, 0.00)", (request.form.get("username"), hash,))
        con.commit()

        # return users info for now registered user by searching for username
        cur.execute("SELECT * FROM Users WHERE username = ?", (request.form.get("username"),))
        rows = list(cur.fetchall())

        # log user into session by id
        session["user_id"] = rows[0]

        # redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")
