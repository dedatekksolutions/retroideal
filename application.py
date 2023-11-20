from flask import Flask, render_template, redirect, request, url_for, session  
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

            # Fetch vehicle images for the current user
            user_vehicle_images = fetch_vehicle_image_data_by_userid(userid)

            return render_template("user-page.html", first_name=first_name, last_name=last_name, vehicles=user_vehicles, vehicle_images=user_vehicle_images)

        else:
            return "User not found"
    else:
        return redirect(url_for("display_users"))

from flask import Flask, render_template, redirect, request, url_for, session
# Other import statements


app.secret_key = "Ez45vGRo5KmMnJPueMLu48RCZiPawAqlDQc3FMVF"

from flask import Flask, render_template, redirect, request, url_for, session
# Other import statements...

@app.route("/upload_image", methods=["POST"])
def upload_image():
    if request.method == "POST":
        file_data = request.files['fileInput']
        if file_data:
            # Upload the file to S3
            uploaded_filename = str(uuid.uuid4())  # Generate a unique filename
            upload_image_to_s3(
                bucket_name="retroideal-member-vehicle-images",
                folder_name="pending-vehicle-images",
                file_name=uploaded_filename,
                image_data=file_data.read()
            )
            
            # Add an entry to the database with a "pending" status
            vehicle_reg = request.form.get("vehicle_reg")
            add_pending_image_entry(vehicle_reg, uploaded_filename)  # Function to add to the database
            
    return redirect(url_for("user_page"))

@app.route("/add_vehicle/<vehicle_reg>", methods=["GET"])
def add_vehicle(vehicle_reg):
    # Fetch vehicle details using the vehicle registration number, assuming it's unique
    vehicle_details = fetch_vehicle_by_reg(vehicle_reg)  # Implement this function

    # Pass the vehicle details to the template
    return render_template('new_upload.html', vehicle_reg=vehicle_reg, vehicle_details=vehicle_details)


if __name__ == "__main__":
    #delete_resources()
    init()
    app.run(host='0.0.0.0')
