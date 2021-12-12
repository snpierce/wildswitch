from flask import Flask, redirect, render_template, request, session, url_for, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, usd, build_market, get_db

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

# method to properly open and close database from https://flask.palletsprojects.com/en/2.0.x/patterns/sqlite3/
# when app closes, close connection to database
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ensure responses aren't cached (taken from finance)
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

    # Note: position refers not to the actual position that a player plays, but rather 
    # is just a binary to indicate Batting (1) or Pitching (0)


# route for users to register
@app.route("/register", methods=["GET", "POST"])
def register():

    # clears previous user session
    session.clear()

    # opens connection to database
    cur = get_db().cursor()

    # when register button is clicked
    if request.method == "POST":

        # checks that all forms have valid input, if not returns error telling what is missing
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

        # if passes all the checks, add username+hash to users table with starting value of $200.00
        cur.execute("INSERT INTO Users (username, password, cash) VALUES (?, ?, 200.00)", (request.form.get("username"), hash,))
        get_db().commit()

        # return users info for now registered user by searching for username
        cur.execute("SELECT * FROM Users WHERE username = ?", (request.form.get("username"),))
        rows = list(cur.fetchall())

        # log user into session by id (is actually username)
        session["user_id"] = rows[0][1]

        # generates market
        build_market()

        # redirect user to home page
        return redirect("/")

    else:
        # if via GET, loads html page
        return render_template("register.html")


# route for users to log in
@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # opens connection to database
    cur = get_db().cursor()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username.", 403)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password.", 403)

        # query database for username
        cur.execute("SELECT * FROM Users WHERE username = ?", (request.form.get("username"),))
        rows = list(cur.fetchall())

        # ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # remember which user has logged in
        session["user_id"] = rows[0][1]

        # every time a user logs in, they earn extra cash (we decided not to have an add cash function to ensure
        # that the site's function as a market with somewhat finite currency remains)
        cur.execute("UPDATE Users SET cash = (cash + 5) WHERE username=?", (session["user_id"],))
        get_db().commit()

        # generates market
        build_market()

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# log user out
@app.route("/logout")
def logout():

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect("/")


# homepage 
@app.route("/")
@login_required
def index():
    
    # renders index html, or home page with site information/instructions
    return render_template("index.html")


# where user can view their own collection of cards, only via GET, no forms here
@app.route("/mycards")
@login_required
def mycards():
        # opens connection to database
        cur = get_db().cursor()

        # initializes arrays to store batters and pitchers that the user owns
        batters = []
        pitchers = []

        # creates list of cards that the user owns where the player is a batter
        cur.execute("SELECT playerID, year, status FROM Cards WHERE username = ? AND position = 1", (session["user_id"],))
        batterInfo = list(cur.fetchall())

        # creates list of cards that the user own where the player is a batter
        cur.execute("SELECT playerID, year, status FROM Cards WHERE username = ? AND position = 0", (session["user_id"],))
        pitcherInfo = list(cur.fetchall())

        # gets player information to display on baseball cards from Batting table 
        for i in range(len(batterInfo)):
            cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (batterInfo[i][0], batterInfo[i][1],))
            batters.append(list(cur.fetchall()))
        
        # gets player information to display on baseball cards from Batting table
        for i in range(len(pitcherInfo)):
            cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (pitcherInfo[i][0], pitcherInfo[i][1],))
            pitchers.append(list(cur.fetchall()))

        # selects the current user's cash stores
        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])
        # selects count of the # of cards the current user owns
        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ?", (session["user_id"],))
        cardCount = int(cur.fetchone()[0])

        # renders a template that displays the current users name, cash stores, # of cards, and information about the batters/pitchers they own
        return render_template("mycards.html", batters=batters, pitchers=pitchers, cash=cash, cardCount=cardCount, username=session["user_id"])


# where the user can search by player full name or for another user's profile
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    # opens database connections
    cur = get_db().cursor()
    
    # if search button is clicked
    if request.method == "POST":
        # get inputted value from form
        search = request.form.get("search")
        # get selected dropdown option value
        option = int(request.form.get("criteria"))

        # if batter full name is selected
        if option == 1:
            # check if the player name appears in the Batting table (case insensitive)
            cur.execute("SELECT COUNT(*) FROM Batting WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            # if there is at least one instance of the searched player in the Batting table
            if count != 0.0:
                # select the playerID from Batting
                cur.execute("SELECT playerID FROM Batting WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]

                # return reroute to 'search_player' with playerID and position as 1 because that indicates 'batter'
                return redirect(url_for('search_player', playerID=playerID, position = '1'))
            else:
                # if no instance in Batting, return error message
                return apology("Not a valid full name or incorrect position.")

        # if the selected dropdown is for pitcher full name
        elif option == 2:
            # check if the player name appears in the Pitching table (case insensitive)
            cur.execute("SELECT COUNT(*) FROM Pitching WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            # if there is at least one instance of the player name in Pitching
            if count != 0.0:
                # get the playerId from Pitching
                cur.execute("SELECT playerID FROM Pitching WHERE LOWER(fullName) LIKE LOWER(?)", (search,))
                playerID = cur.fetchone()[0]

                # return reroute to search_player, passing playerID anf 0 because that indicates 'pitcher'
                return redirect(url_for('search_player', playerID=playerID, position = '0'))
            else:
                # if no isntance in Pitching return error message
                return apology("Not a valid full name or incorrect position.")

        # if the selected dropdown is for a user        
        else:
            # check if user exists (case insensitive)
            cur.execute("SELECT COUNT(*) FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
            count = float(cur.fetchone()[0])

            # if user exists
            if count != 0.0:
                # select username from Users
                cur.execute("SELECT username FROM Users WHERE LOWER(username) LIKE LOWER(?)", (search,))
                username = cur.fetchone()[0]

                # return reroute to search_user passing username
                return redirect(url_for('search_user', username=username))
            else:
                # user doesn't exist, return apology
                return apology("Not a valid username.")
    else:
        # clears previous search values from tables everytime /search is accessed
        cur.execute("DELETE FROM Search")
        cur.execute("DELETE FROM SearchUser")
        get_db().commit()

        # returns search html template
        return render_template("search.html")


# route that appears after searching for a user's profile
@app.route("/search/<username>", methods=["GET", "POST"])
def search_user(username):
    # opens database connection
    cur = get_db().cursor()
    
    # if buy button to purchase one of the user's cards is pushed
    if request.method == "POST":

        # check that forms are valid, return error
        if not request.form.get("player"):
            return apology("Please enter player.")
        if not request.form.get("year"):
            return apology("Please enter year.")

        # store inputted values from form
        player = request.form.get("player")
        year = request.form.get("year")

        # get the username of the searched user's profile from stored searchuser table
        cur.execute("SELECT * FROM SearchUser")
        rows = cur.fetchall()
        user = rows[0][0]

        # checks if card searched belongs to the searched user
        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ? AND fullName=? AND year=?", (user, player, year,))
        count = cur.fetchall()[0][0]

        # if card not found belonging to searched user
        if count == 0:
            # return error
            return apology("Invalid card information or this user does not own requested card.")
        
        # if card does belong to user, get information about whether the card is for auction or not
        cur.execute("SELECT status, position FROM Cards WHERE username = ? AND fullName=? AND year=?", (user, player, year,))
        info = cur.fetchall()
        status = info[0][0]
        position = info[0][1]

        # if card is not for sale
        if status == 0:
            # return error
            return apology("Card not for sale.")
        else:
            # if card for sale, select auctionPrice
            cur.execute("SELECT auctionPrice FROM Cards WHERE username = ? AND fullName=? AND year=?", (user, player, year,))
            value = cur.fetchone()[0]

            # get current user's cash stores
            cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
            cash = int(cur.fetchone()[0])

            # checks if current user can afford requested card
            if value > cash:
                # if not, return error
                return apology("You cannot afford to purchase this card.")
            # if can afford
            else:
                # adds bought card into cards table
                cur.execute("UPDATE Cards SET username = ?, status = 0, auctionPrice = NULL WHERE fullName = ? AND year = ?", (session["user_id"], player, year,))
                # subtracts card cost from users total cash supply
                cur.execute("UPDATE Users SET cash = (cash - ?) WHERE username = ?", (value, session["user_id"],))

                # updates status to (1) owned for whichever table the card resides in
                if position == 1:
                    cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE fullName = ? AND yearID = ?", (player, year,))
                else:
                    cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE fullName = ? AND yearID = ?", (player, year,))

                # updates searched user's card to 'transfer' money
                cur.execute("UPDATE Users SET cash = (cash + ?) WHERE username = ?", (value, user,))

                # commits changes
                get_db().commit()

                # redirects to current user's collection
                return redirect("/mycards")
    # if via GET, returns the search results with option to search for one of the user's cards and buy it (if available)
    else:
        # stores in SearchUser the username that the current user searched for
        cur.execute("INSERT INTO SearchUser (username) VALUES (?)", (username,))
        get_db().commit()

        # retrieves the same information as for the collection page, but without cash and for the searched user
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

        # returns template that displays user's profile with form to search/buy one of their cards
        return render_template("usersearch.html", batters=batters, pitchers=pitchers, username=username)


# route that appears after searching for a player (either batter or pitcher)
@app.route("/search/<playerID>/<position>", methods=["GET", "POST"])
def search_player(playerID, position):
    # opens database connection
    cur = get_db().cursor()

    # if user submitted input
    if request.method == "POST":

        # if the user didn't submit a year of a card to buy, return an error
        if not request.form.get("year"):
            return apology("Please enter year.")
        
        year = request.form.get("year")

        # store all the info for the cards from the Search table
        cur.execute("SELECT * FROM Search")
        rows = cur.fetchall()
        player_id = rows[0][0]
        pos = rows[0][1]

        # get the user's cash store from the Users table
        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])

        # if a pitcher, get the number of players who have the searched name and the inputted year, and then get the data
        if pos == 0:
            cur.execute("SELECT COUNT(*) FROM Pitching WHERE playerID = ? AND yearID = ?", (player_id, year,))
            count = int(cur.fetchone()[0])
            cur.execute("SELECT playerID, value, yearID, fullName FROM Pitching WHERE playerID = ? AND yearID = ?", (player_id, year,))
            selected = cur.fetchone()
        
        # if a batter, get the number of players who have the searched name and the inputted year, and then get the data
        else:
            cur.execute("SELECT COUNT(*) FROM Batting WHERE playerID = ? AND yearID = ?", (player_id, year,))
            count = int(cur.fetchone()[0])
            cur.execute("SELECT playerID, value, yearID, fullName FROM Batting WHERE playerID = ? AND yearID = ?", (player_id, year,))
            selected = cur.fetchone()

        # if the count taken from either of the two branches of the above if-routes is 0, the card does not exist
        if count == 0:
            return apology("Not a valid year.")

        # check if the card is already owned
        cur.execute("SELECT COUNT(*) FROM Cards WHERE playerID = ? AND year = ?", (player_id, year,))
        check_owned = cur.fetchone()[0]
 
        # if the card is already owned
        if check_owned == 1:
            # get and store the status, price, and owner from the Cards table
            cur.execute("SELECT auctionPrice, status, username FROM Cards WHERE playerID = ? AND year = ?", (player_id, year,))
            info = cur.fetchall()
            username = info[0][2]
            # if the logged-in user already owns the card, return an error.
            if username == session["user_id"]:
                return apology("You own this card.")

            # if the card is not for sale, return an error
            if info[0][1] == 0:
                return apology("This card is not for sale.")
            
            else:
                # get value of card and make sure it is less than the user's cash (i.e. that they can afford)
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
                        cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2],))
                    else:
                        cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2],))

                    # adds value to previous user's cash
                    cur.execute("UPDATE Users SET cash = (cash + ?) WHERE username = ?", (value, info[0][2],))

                    get_db().commit()

                    return redirect("/mycards")
        
        # if card was not already owned
        else:
            # get market price
            value = selected[1]

        # make sure user can afford
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

    # if user reached via GET
    else:
        # get position of player
        int_position = int(position)

        # add into Search table the player and their position
        cur.execute("INSERT INTO Search (playerID, position) VALUES (?, ?)", (playerID, int_position,))
        get_db().commit()

        # if a pitcher, gets stats from Pitching table and passes it through to pitcher.html
        if int_position == 0:
            cur.execute("SELECT * FROM Pitching WHERE playerID = ?", (playerID,))
            pitchers = list(cur.fetchall())
            return render_template("pitcher.html", pitchers=pitchers)
        # if a batter, gets stats from Batting table and passes it through to batter.html
        else:
            cur.execute("SELECT * FROM Batting WHERE playerID = ?", (playerID,))
            batters = list(cur.fetchall())
            return render_template("batter.html", batters=batters)


# route for the user to buy from a pre-generated market of random players
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    cur = get_db().cursor()

    # if the user submitted input
    if request.method == "POST":

        # get amount of cash from Users
         cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
         cash = int(cur.fetchone()[0])

        # get the input which says which option the player selected
         player = int(request.form.get("buy"))

        # store the data for all 8 players in market in lists
         cur.execute("SELECT * FROM Market")
         players = list(cur.fetchall())
         selected = players[player]

        # check that card is available for purchase
         if selected[4] == 1:
             return apology("Already purchased!")
        # check that user can afford card
         elif selected[5] > cash:
             return apology("Can't afford - please add money to account.")

        # commannds if no errors
         else:
             # adds bought card into cards table
             cur.execute("INSERT INTO Cards (username, playerID, cardValue, status, position, year, fullName) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], selected[0], selected[5], '0', selected[3], selected[2], selected[1]))
             # subtracts card cost from users total cash supply
             cur.execute("UPDATE Users SET cash = (cash - ?) WHERE username = ?", (selected[5], session["user_id"],))
             # updates status in market to mean bought
             cur.execute("UPDATE Market SET status = '1' WHERE playerID = ?", (selected[0],))

             # updates status to mean owned for whichever table (pitching or batting) the card resides in
             if selected[3] == 1:
                 cur.execute("UPDATE Batting SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             else:
                 cur.execute("UPDATE Pitching SET auctionValue = 'Not For Sale', status = '1' WHERE playerID = ? AND yearID = ?", (selected[0], selected[2]))
             get_db().commit()

             return redirect("/mycards")

    else:
        # creates empty lists for batters and pitchers
        batters = []
        pitchers = []

        # get all the playerIDs and positions for the 8 displayed players
        cur.execute("SELECT playerID, year, position FROM Market")
        market = list(cur.fetchall())

        # loop through all 8 players, get data from the corresponding tables, and append to the lists
        for i in range(len(market)):
            if market[i][2] == 1:
                cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (market[i][0], market[i][1],))
                batters.append(cur.fetchone())
            else:
                cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (market[i][0], market[i][1],))
                pitchers.append(cur.fetchone())
        
        #return to buy.html page, passing through the lists we just created
        return render_template("buy.html", batters=batters, pitchers=pitchers)



# route for the user to sell their cards
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # creates cursor
    cur = get_db().cursor()

    # if user submitted input
    if request.method == "POST":

        # if they are using the sell to market form
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

            #Update user's cash by sale value
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

            # ensure new value for card was submitted
            if not request.form.get("value"):
                return apology("Must provide value.")

            # Check if card exists with their username, playername, and year
            cur.execute("SELECT COUNT(playerID) FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            if int(cur.fetchone()[0]) == 0:
                return apology("You do not own this card.")

            # set the status to for sale and the new auctionPrice in the cards table
            cur.execute("UPDATE Cards SET auctionPrice = ?, status = '1' WHERE username = ? AND fullName = ? AND year = ?", (request.form.get("value"), session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            get_db().commit()

            # get the player's position
            cur.execute("SELECT position FROM Cards WHERE username = ? AND fullName = ? AND year = ?", (session["user_id"], request.form.get("playerauction"), request.form.get("yearauction"),))
            position = int(cur.fetchone()[0])

            # if a pitcher, set the card to be for auction and the new price in Batting
            if position == 1:
                cur.execute("UPDATE Batting SET auctionValue = 'For Auction: ' || PRINTF('$%.2f', ?) WHERE fullName = ? AND yearID = ?", (request.form.get("value"), request.form.get("playerauction"), request.form.get("yearauction"),))
                get_db().commit()
            
            # if a batter, set the card to be for auction and the new price in Pitching
            else:
                cur.execute("UPDATE Pitching SET auctionValue = 'For Auction: ' || PRINTF('$%.2f', ?) WHERE fullName = ? AND yearID = ?", (request.form.get("value"), request.form.get("playerauction"), request.form.get("yearauction"),))
                get_db().commit()

            return redirect("/mycards")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # creates empty lists of batters and pitchers
        batters = []
        pitchers = []

        #gets all the playerIDs and years of batters who are owned by the logged-in user
        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 1", (session["user_id"],))
        batterInfo = list(cur.fetchall())

        #gets all the playerIDs and years of pitchers who are owned by the logged-in user
        cur.execute("SELECT playerID, year FROM Cards WHERE username = ? AND position = 0", (session["user_id"],))
        pitcherInfo = list(cur.fetchall())

        #loop through and append all the batters' data to batters list
        for i in range(len(batterInfo)):
            cur.execute("SELECT * FROM Batting WHERE playerID = ? AND yearID = ?", (batterInfo[i][0], batterInfo[i][1],))
            batters.append(list(cur.fetchall()))

        # loop through and append all the pitchers' data to pitchers list    
        for i in range(len(pitcherInfo)):
            cur.execute("SELECT * FROM Pitching WHERE playerID = ? AND yearID = ?", (pitcherInfo[i][0], pitcherInfo[i][1],))
            pitchers.append(list(cur.fetchall()))

        # query the Users table to get the current user's cash 
        cur.execute("SELECT cash FROM Users WHERE username = ?", (session["user_id"],))
        cash = int(cur.fetchone()[0])

        # query the cards table to count how many cards the user owns
        cur.execute("SELECT COUNT(*) FROM Cards WHERE username = ?", (session["user_id"],))
        cardCount = int(cur.fetchone()[0])

        # pass the batters and pitchers lists, number of cards, username, and cash value through to sell.html
        return render_template("sell.html", batters=batters, pitchers=pitchers, cash=cash, cardCount=cardCount, username=session["user_id"])

