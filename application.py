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
            
@app.route("/user_home/<userid>/vehicles")
def get_user_vehicles(userid):
    if "user" in session and session["user"]["userid"] == userid:
        vehicles = fetch_vehicles_by_userid(userid)
        return jsonify(vehicles)
    else:
        return jsonify({"error": "User not authenticated or unauthorized"}), 401

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

            # Fetch all vehicle data for the user
            vehicles = fetch_vehicles_by_userid(userid)

            # Print statements for debugging
            print("User:", user)
            print("Image URLs:", image_urls)
            print("Vehicles:", vehicles)

            return render_template("user-home.html", first_name=first_name, last_name=last_name, image_urls=image_urls)

    # If the user is not authenticated, redirect to the login page
    return redirect(url_for("display_users"))

@app.route("/logout")
def logout():
    # Clear the session data
    session.pop("user", None)
    return jsonify({"message": "Logout successful"})

@app.route("/user_home/<vehicle_id>/images")
def get_vehicle_images(vehicle_id):
    # Fetch images for the specified vehicle_id from the retroideal-vehicle-image-table
    images = fetch_images_by_vehicle_id(vehicle_id)
    
    return jsonify(images)

@app.route("/upload/<vehicle_id>")
def upload_page(vehicle_id):
    # Fetch additional details for the vehicle using the vehicle_id
    vehicle_details = fetch_vehicle_by_id(vehicle_id)

    # Render the upload page with the vehicle details
    return render_template("user-upload.html", vehicle_details=vehicle_details)


if __name__ == "__main__":
    #init()
    #delete_resources()
    app.run(host='0.0.0.0')


