from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from utilities.init import *
from utilities.helpers import *
from DBops import *

app = Flask(__name__)

app.secret_key = "GnmcfY6KMHui9qlFcxp8lDMGywKcdukrQQIiJ0nz"

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login")
def display_users():
    users = fetch_users()
    return render_template('login.html', users=users)

@app.route("/login", methods=["POST"])
def login():
    # Handle the login logic for POST requests
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = fetch_user_by_username(username)

        if user:
            stored_password_hash = user.get("passwordhash")
            stored_salt = user.get("salt")

            if verify_hash(password, stored_password_hash, stored_salt):
                # If authentication is successful, store user information in the session
                session["user"] = {
                    "userid": user.get("userid")
                }

                # Fetch user details
                user_details = fetch_user_by_userid(session["user"]["userid"])
                first_name = user_details.get("firstname")

                # Redirect to the user page or any other route as needed
                return redirect(url_for("user_home"))

@app.route("/user_home")
def user_home():
    if "user" in session:
        userid = session["user"]["userid"]
        user = fetch_user_by_userid(userid)
        
        if user:
            first_name = user.get("firstname")
            last_name = user.get("lastname")

            # Fetch image URLs for the user's vehicles
            image_urls = fetch_images_by_userid(userid)

            # Print statements for debugging
            print("User:", user)
            print("Image URLs:", image_urls)

            return render_template("user-home.html", first_name=first_name, last_name=last_name, image_urls=image_urls)

    # If user is not authenticated, redirect to the login page
    return redirect(url_for("display_users"))

@app.route("/logout")
def logout():
    # Clear the session data
    session.pop("user", None)
    return jsonify({"message": "Logout successful"})


if __name__ == "__main__":
    #init()
    #delete_resources()
    app.run(host='0.0.0.0')
