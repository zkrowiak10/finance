import os
import logging
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

logging.basicConfig(level=logging.DEBUG, format= ' %(asctime)s -%(levelname)s - %(message)s')
logging.debug('Start of program')
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    pass
    """Show portfolio of stocks"""
    cash = usd(user.cash())
    portfolio = db.execute(f'SELECT * FROM {user.username} WHERE shares > 0')
    portfolio_value = 0
    for row in portfolio:
        value = lookup(row['stock'])['price']*row['shares']
        portfolio_value += value
        row['value'] = usd(value)
    portfolio_value += user.cash()
    portfolio_value = usd(portfolio_value)
    return render_template('index.html', portfolio=portfolio, cash=cash, portfolio_value = portfolio_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    logging.debug('Start of buy')
    if request.method=="POST":
        #constitute variables
        stock = request.form.get('stock').upper()
        try:
            price = lookup(stock)
            price= price['price']
        except:
            return apology('Stock Does Not Exist')
        number = int(request.form.get('number'))
        total = price*number
        user_id= session["user_id"]
        cash = db.execute('SELECT cash FROM users WHERE id = :id', id=user_id)
        cash=cash[0]['cash']
        date = datetime.datetime.now()
        print(cash)

        if total>cash:
            return apology('You lack sufficient funds')

        else:
            cash=cash-total
            db.execute('INSERT INTO purchases (stock, date, user_id, price,shares) VALUES (:stock,:date,:user_id,:price,:number)', stock=stock, date=date, user_id=user_id, number=number, price=price)
            db.execute('UPDATE users SET cash= :cash WHERE id= :user_id', user_id=user_id, cash=cash)
            if len(db.execute(f'SELECT * FROM {user.username} WHERE stock= :stock', stock=stock))<1:
                    db.execute(f'INSERT INTO {user.username} (stock, shares) VALUES (:stock, :shares)', stock=stock, shares=number)
            else:
                db.execute(f'UPDATE  {user.username} SET shares = shares + :shares WHERE stock= :stock', stock=stock, shares=number)
            flash(f'You Purchased {number} Shares of {stock} for {usd(total)}!')
            return redirect('/')




    else:
        return render_template('buy.html')

    return apology("TODO")
    logging.debug('End of buy')

@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    if len(db.execute('select * from users where username = :username', username = request.args.get('username')))>0:
        return None
    else:
        return jsonify('true')


@app.route("/history")
@login_required
def history():
    purchases = db.execute(f'SELECT * FROM purchases WHERE user_id = {user.id} ORDER BY date DESC')
    return render_template('history.html', purchases = purchases)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        global user
        user = Current_User(session["user_id"])

        # Redirect user to home page
        flash('You were successfully logged in')
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method== "POST":
        stock=request.form.get('stock')
        data = lookup(stock)
        if data == None:
            return apology('This stock does not exist')
        else:
            return render_template('quoted.html',name=data['name'],price=data['price'])
    else:
        return render_template('quote.html')



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        hashed_password = generate_password_hash(password)
        if not username:
                return apology('please provide a username')
        elif password !=confirmation:
            return apology("please make sure passwords match")
        elif len(db.execute("SELECT * FROM users WHERE username= :username", username=username)) != 0:
            return apology("Username already exists")
        else:
            db.execute("INSERT INTO users(username,hash) VALUES (:username,:password)", username=username, password=hashed_password)
            db.execute(f'CREATE TABLE :username (stock VARCHAR(5), shares INT)', username=username)
            flash(f'You have successfully registered, {username}')
            return  redirect("/login")
        return apology("TODO")
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    logging.debug('start of sell')
    if request.method == 'POST':

        logging.debug('START OF SELL POST')
        symbol= request.form.get('symbol')
        price = lookup(symbol)['price']
        shares = int(request.form.get('number'))
        value = shares*price
        date = datetime.datetime.now()
        logging.debug(f'shares is {str(shares)} value is {str(value)} symbol is {symbol}')
        if shares > db.execute(f'SELECT shares FROM {user.username} WHERE stock = :stock', stock = symbol)[0]['shares']:
            return apology('You don\'t have that many shares')
        else:
            db.execute(f'UPDATE {user.username} SET shares = shares - :number WHERE stock = :stock', stock = symbol, number = shares)
            db.execute(f'UPDATE users SET cash= cash+ :value WHERE id = {user.id}', value=value)
            db.execute('INSERT INTO purchases (stock, date, user_id, price,shares) VALUES (:stock,:date,:user_id,:price,-:number)', \
            stock=symbol, date=date, user_id=user.id, number=shares, price=price)
            logging.debug('end of sell.post')
            flash(f'You Sold {shares} Shares of {symbol} For {usd(value)}')
            return redirect('/')
    else:
        stocks = db.execute(f'SELECT stock FROM {user.username} WHERE shares > 0')
        logging.debug('end of sell')
        return render_template('sell.html', stocks = stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
logging.debug('End of program')

class Current_User():
    def __init__(self, id):
        self.id = id
        self.username= db.execute('SELECT username FROM users WHERE id= :id', id=id )[0]['username']

    def cash (self):
        test = db.execute (f'SELECT cash FROM users WHERE id = {self.id}')
        return test[0]['cash']

