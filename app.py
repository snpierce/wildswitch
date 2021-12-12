import os, csv
import datetime
import sqlite3
import jinja2

from flask import Flask, flash, redirect, render_template, request, session, url_for, g
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, generate_user, usd, build_market, get_db

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    cur = get_db().cursor()

    if request.method == "POST":

        if 'sell' in request.form:

            # Ensure player name was submitted
            if not request.form.get("playersell"):
                return apology("Must provide player name.")

            # Ensure year was submitted
            if not request.form.get("yearsell"):
                return apology("Must provide year.")

            # Check if card exists with their username, playername, and year
            cur.execute("SELECT COUNT(playerID) FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playersell"), request.form.get("yearsell"),))
            if int(cur.fetchone()[0]) == 0:
                return apology("You do not own this card.")

            #Get value of card
            cur.execute("SELECT cardValue, position FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playersell"), request.form.get("yearsell"),)) 
            temp = list(cur.fetchall())
            value = temp[0][0]
            position = temp[0][1]

            #Get user's old cash
            cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
            cash = cur.fetchone()[0]

            #Update user's cash
            cur.execute("UPDATE Users SET cash = ? WHERE username = ?", (cash + value, session["user_id"],))

            #Delete card from cards
            cur.execute("DELETE FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playersell"), request.form.get("yearsell"),))
            get_db().commit()

            #Update status in pitching/batting
            if position == 0:
                cur.execute("UPDATE Pitching SET status = 0, auctionValue = 'For Sale' WHERE fullName=? AND yearID=?", (request.form.get("playersell"), request.form.get("yearsell"),))
                get_db().commit()
            else:
                cur.execute("UPDATE Batting SET status = 0, auctionValue = 'For Sale' WHERE fullName=? AND yearID=?", (request.form.get("playersell"), request.form.get("yearsell"),))
                get_db().commit()

            return redirect("/mycards")

        else:
            # Ensure player name was submitted
            if not request.form.get("playerauction"):
                return apology("Must provide player name.")

            # Ensure year was submitted
            if not request.form.get("yearauction"):
                return apology("Must provide year.")

            if not request.form.get("value"):
                return apology("Must provide value.")

            # Check if card exists with their username, playername, and year
            cur.execute("SELECT COUNT(playerID) FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            if int(cur.fetchone()[0]) == 0:
                return apology("You do not own this card.")

            cur.execute("UPDATE Cards SET auctionPrice = ?, status = '1' WHERE username = ? AND fullName = ? AND year = ?", (request.form.get("value"), session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            get_db().commit()

            cur.execute("SELECT position FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            position = int(cur.fetchone()[0])

            if position == 1:
                # batting
                cur.execute("UPDATE Batting SET auctionValue = 'For Auction: ' || PRINTF('$%.2f', ?) WHERE fullName = ? AND yearID = ?", (request.form.get("value"), request.form.get("playerauction"), request.form.get("yearauction"),))
                get_db().commit()
            else:
                # pitching
                cur.execute("UPDATE Pitching SET auctionValue = 'For Auction: ' || PRINTF('$%.2f', ?) WHERE fullName = ? AND yearID = ?", (request.form.get("value"), request.form.get("playerauction"), request.form.get("yearauction"),))
                get_db().commit()

            return redirect("/mycards")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        batters = []
        pitchers = []

        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 1", (session["user_id"],))
        batterInfo = list(cur.fetchall())

        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 0", (session["user_id"],))
        pitcherInfo = list(cur.fetchall())

        for i in range(len(batterInfo)):
            cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (batterInfo[i][0], batterInfo[i][1],))
            batters.append(list(cur.fetchall()))

            
        for i in range(len(pitcherInfo)):
            cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (pitcherInfo[i][0], pitcherInfo[i][1],))
            pitchers.append(list(cur.fetchall()))

        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ?", (session["user_id"],))
        cardCount = int(cur.fetchone()[0])


        return render_template("sell.html", batters=batters, pitchers=pitchers, cash=cash, cardCount=cardCount, username=session["user_id"])



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    cur = get_db().cursor()

    if request.method == "POST":

         cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
         cash = int(cur.fetchone()[0])

         player = int(request.form.get("buy"))

         cur.execute("SELECT * FROM Market")
         players = list(cur.fetchall())
         selected = players[player]

         if selected[5] > cash:
             return apology("Can't afford - please add money to account.")
         elif selected[4] == 1:
             return apology("Already purchased!")
         else:
             # adds bought card into cards table
             cur.execute("INSERT INTO Cards (username, playerID, cardValue, status, position, year, fullName) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], selected[0], selected[5], '0', selected[3], selected[2], selected[1]))
             # subtracts card cost from users total cash supply
             cur.execute("UPDATE Users SET cash = (cash - ?) WHERE username = ?", (selected[5], session["user_id"],))
             # updates status in market to mean bought
             cur.execute("UPDATE Market SET status = '1' WHERE playerID = ?", (selected[0],))

             # updates status to mean owned for whichever table the card resides in
             if selected[3] == 1:
                 cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             else:
                 cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             get_db().commit()

             return redirect("/mycards")

    else:
        batters = []
        pitchers = []

        cur.execute("SELECT playerID, year, position FROM Market")
        market = list(cur.fetchall())

        for i in range(len(market)):
            if market[i][2] == 1:
                cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (market[i][0], market[i][1],))
                batters.append(cur.fetchone())
            else:
                cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (market[i][0], market[i][1],))
                pitchers.append(cur.fetchone())
        

        return render_template("buy.html", batters=batters, pitchers=pitchers)


@app.route("/mycards")
@login_required
def mycards():
        cur = get_db().cursor()

        batters = []
        pitchers = []

        cur.execute("SELECT playerID, year, status FROM Cards WHERE username = ? AND position = 1", (session["user_id"],))
        batterInfo = list(cur.fetchall())

        cur.execute("SELECT playerID, year, status FROM Cards WHERE username = ? AND position = 0", (session["user_id"],))
        pitcherInfo = list(cur.fetchall())

        for i in range(len(batterInfo)):
            cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (batterInfo[i][0], batterInfo[i][1],))
            batters.append(list(cur.fetchall()))
        
        for i in range(len(pitcherInfo)):
            cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (pitcherInfo[i][0], pitcherInfo[i][1],))
            pitchers.append(list(cur.fetchall()))

        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ?", (session["user_id"],))
        cardCount = int(cur.fetchone()[0])


        return render_template("mycards.html", batters=batters, pitchers=pitchers, cash=cash, cardCount=cardCount, username=session["user_id"])


@app.route("/")
@login_required
def index():
    
    return render_template("index.html")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    cur = get_db().cursor()
    
    if request.method == "POST":
        search = request.form.get("search")
        option = int(request.form.get("criteria"))

        if option == 1:
            cur.execute("SELECT COUNT(*) FROM Batting WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT playerID FROM Batting WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]
                return redirect(url_for('search_player', playerID=playerID, position = '1'))
            else:
                return apology("Not a valid full name or incorrect position.")

        elif option == 2:
            cur.execute("SELECT COUNT(*) FROM Pitching WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT playerID FROM Pitching WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]
                return redirect(url_for('search_player', playerID=playerID, position = '0'))
            else:
                return apology("Not a valid full name or incorrect position.")
        else:
            cur.execute("SELECT COUNT(*) FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            if count != 0.0:
                cur.execute("SELECT username FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
                username = cur.fetchone()[0]
                return redirect(url_for('search_user', username=username))
            else:
                return apology("Not a valid username.")
    else:
        
        cur.execute("DELETE FROM Search")
        cur.execute("DELETE FROM SearchUser")
        get_db().commit()

        return render_template("search.html")


@app.route("/search/<username>", methods=["GET", "POST"])
def search_user(username):
    cur = get_db().cursor()
    
    if request.method == "POST":

        return redirect("/mycards")
    else:
        cur.execute("INSERT INTO SearchUser (username) VALUES (?)", (username,))
        get_db().commit()

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

        return render_template("usersearch.html", batters=batters, pitchers=pitchers, username=username)


@app.route("/search/<playerID>/<position>", methods=["GET", "POST"])
def search_player(playerID, position):
    cur = get_db().cursor()

    if request.method == "POST":

        cur.execute("SELECT * FROM Search")
        rows = cur.fetchall()
        player_id = rows[0][0]
        pos = int(rows[0][1])

        if not request.form.get("year"):
            return apology("Please enter year.")
        
        year = request.form.get("year")

        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])

        if pos == 0:
            cur.execute("SELECT COUNT(*) FROM Pitching WHERE playerID = ? AND yearID = ?", (player_id, year,))
            count = int(cur.fetchone()[0])
            cur.execute("SELECT playerID, value, yearID, fullName FROM Pitching WHERE playerID = ? AND yearID = ?", (player_id, year,))
            selected = cur.fetchone()
        else:
            cur.execute("SELECT COUNT(*) FROM Batting WHERE playerID = ? AND yearID = ?", (player_id, year,))
            count = int(cur.fetchone()[0])
            cur.execute("SELECT playerID, value, yearID, fullName FROM Batting WHERE playerID = ? AND yearID = ?", (player_id, year,))
            selected = cur.fetchone()

        if count == 0:
            return apology("Not a valid year.")

        cur.execute("SELECT COUNT(*), auctionPrice, status FROM Cards WHERE playerID = ? AND year = ?", (player_id, year,))
        check_owned = cur.fetchone()[0]
 
        if check_owned == 1:
            cur.execute("SELECT auctionPrice, status, username FROM Cards WHERE playerID = ? AND year = ?", (player_id, year,))
            info = cur.fetchall()
            username = info[0][2]
            if username == session["user_id"]:
                return apology("You own this card.")

            if info[0][1] == 0:
                return apology("This card is not for sale.")
            else:
                value = info[0][0]
                if value > cash:
                    return apology("Can't afford - please add money to account.")
                else:
                    # adds bought card into cards table
                    cur.execute("UPDATE Cards SET username = ?, status = 0, auctionPrice = NULL WHERE playerID = ? AND year = ?", (session["user_id"], player_id, year,))
                    # subtracts card cost from users total cash supply
                    cur.execute("UPDATE Users SET cash = (cash - ?) WHERE username = ?", (value, session["user_id"],))

                    # updates status to mean owned for whichever table the card resides in
                    if pos== 1:
                        cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
                    else:
                        cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))

                    cur.execute("UPDATE Users SET cash = (cash + ?) WHERE username = ?", (value, info[0][2],))

                    get_db().commit()

                    return redirect("/mycards")
        else:
            value = selected[1]


        if value > cash:
            return apology("Can't afford - please add money to account.")
        else:
             # adds bought card into cards table
             cur.execute("INSERT INTO Cards (username, playerID, cardValue, status, position, year, fullName) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], selected[0], value, '0', pos, selected[2], selected[3]))
             # subtracts card cost from users total cash supply
             cur.execute("UPDATE Users SET cash = (cash - ?) WHERE username = ?", (value, session["user_id"],))

             # updates status to mean owned for whichever table the card resides in
             if pos== 1:
                 cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             else:
                 cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             
             get_db().commit()

             return redirect("/mycards")

    else:

        cur.execute("INSERT INTO Search (playerID, position) VALUES (?, ?)", (playerID, position,))
        get_db().commit()

        if position == 0:
            cur.execute("SELECT * FROM Pitching WHERE playerID = ?", (playerID,))
            pitchers = list(cur.fetchall())
            return render_template("pitcher.html", pitchers=pitchers)
        else:
            cur.execute("SELECT * FROM Batting WHERE playerID = ?", (playerID,))
            batters = list(cur.fetchall())
            return render_template("batter.html", batters=batters)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    cur = get_db().cursor()

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
            return apology("Invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][1]

        # generates market
        build_market()

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

    session.clear()

    cur = get_db().cursor()

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
        cur.execute("INSERT INTO Users (username, password, cash) VALUES (?, ?, 50.00)", (request.form.get("username"), hash,))
        get_db().commit()

        # return users info for now registered user by searching for username
        cur.execute("SELECT * FROM Users WHERE username = ?", (request.form.get("username"),))
        rows = list(cur.fetchall())

        # log user into session by id
        session["user_id"] = rows[0][1]

        # generates market
        build_market()

        # redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")
