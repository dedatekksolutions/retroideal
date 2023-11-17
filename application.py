from flask import Flask, render_template, redirect, request, url_for  
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Attr
import boto3
from botocore.exceptions import ClientError
import secrets
import time
from DBops import *
from utilities.init import *
from utilities.helpers import *

app = Flask(__name__)

app.secret_key = "GnmcfY6KMHui9qlFcxp8lDMGywKcdukrQQIiJ0nz"

@app.route("/")
def index():
    return render_template('index.html')
    
@app.route("/login")
def display_users():
    users = fetch_users()
    return render_template('login.html', users=users)

from flask import session  # Include the session module from Flask

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Handle the login logic for POST requests
        username = request.form["username"]
        password = request.form["password"]

        user = fetch_user_by_username(username)

        if user:
            stored_password_hash = user.get("passwordhash")
            stored_salt = user.get("salt")

            if verify_hash(password, stored_password_hash, stored_salt):
                # If authentication is successful, store user information in the session
                session["user"] = {
                    "userid": user.get("userid"),
                    "username": user.get("username"),
                    # Add other user details as needed
                }
                # Redirect to the user page or any other route as needed
                return redirect(url_for("user_page"))

    # If login fails or user does not exist, redirect back to the login page
    return redirect(url_for("display_users"))

@app.route("/user_page")
def user_page():
    if "user" in session:
        userid = session["user"]["userid"]
        user = fetch_user_by_userid(userid)
        
        if user:
            first_name = user.get("firstname")
            last_name = user.get("lastname")

            # Fetch vehicles for the current user
            user_vehicles = fetch_vehicles_by_userid(userid)

            return render_template("user-page.html", first_name=first_name, last_name=last_name, vehicles=user_vehicles)
        else:
            return "User not found"
    else:
        return redirect(url_for("display_users"))


if __name__ == "__main__":
    delete_resources()
    print("Sleeping for 5 seconds...")
    time.sleep(5)
    print("Awake after 5 seconds!")
    init()
    app.run(host='0.0.0.0')
