from flask import Flask, render_template, redirect, request, url_for  # Include 'redirect' and 'url_for' here
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Attr
import boto3
from botocore.exceptions import ClientError
import secrets
import hashlib
import uuid
import random
import string
import json
import time

app = Flask(__name__)

flask_app_user="retroideal-flask"
member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"
user_table="retroideal-user-credentials"
vehicle_table="retroideal-vehicle-table"
app.secret_key = "GnmcfY6KMHui9qlFcxp8lDMGywKcdukrQQIiJ0nz"

#####################################ROUTES##########################################
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

###################################HELPERS#############################################
def fetch_user_by_username(username):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)
    
    response = table.scan(FilterExpression=Attr('username').eq(username))
    items = response['Items']
    
    if items:
        return items[0]  # Assuming usernames are unique; return the first match found
    
    return None  # If no match found

def fetch_vehicles_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_table)

    response = table.scan(FilterExpression=Attr('userid').eq(userid))
    items = response.get('Items', [])
    return items

def fetch_user_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)
    
    response = table.get_item(Key={'userid': userid})
    user = response.get('Item')
    
    return user

def fetch_users():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(user_table)
    response = table.scan()
    return response['Items']


########################################INIT########################################
#initialise resources
def init():
    user_arn = get_user_arn(flask_app_user)
    check_user_existence(flask_app_user)
    check_s3_bucket(member_vehicle_images_bucket_name, user_arn)
    check_dynamodb_table_exists(user_table, user_arn)
    check_dynamodb_table_exists(vehicle_table, user_arn)
    print("Application initialized!")

#get user arn for creating resources
def get_user_arn(username):
    iam = boto3.client('iam')
    response = iam.get_user(UserName=username)
    user_arn = response['User']['Arn']
    return user_arn

#check if iam user exists
def check_user_existence(username):
    iam = boto3.client('iam')
    try:
        iam.get_user(UserName=username)
        print(f"IAM user '{username}' exists.")
    except iam.exceptions.NoSuchEntityException:
        print(f"IAM user '{username}' does not exist.")
        create_iam_user(username)
        print(f"IAM user '{username}' created.")

#create iam user for the app
def create_iam_user(username):
    iam = boto3.client('iam')
    try:
        iam.create_user(UserName=username)
        print(f"IAM user '{username}' created successfully.")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{username}' already exists.")

#check if bucket exists
def check_s3_bucket(bucket_name, user_arn):  # Modify the function to accept user_arn
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"The bucket '{bucket_name}' already exists and is owned by you.")
    except s3.exceptions.ClientError as e:
        # If a specific error code is raised, it means the bucket doesn't exist
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            create_s3_bucket(bucket_name, user_arn)
        else:
            # Handle other errors if needed
            raise

def create_s3_bucket(bucket_name, user_arn):
    s3 = boto3.client('s3')
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created successfully.")
        
        # Define the bucket policy granting full access to the owner (replace with your app/user ID)
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'GiveAppReadWriteAccess',
                'Effect': 'Allow',
                'Principal': {'AWS': user_arn},  # Use the IAM user's ARN
                'Action': ['s3:GetObject', 's3:PutObject'],
                'Resource': f'arn:aws:s3:::{bucket_name}/*'
            }]
        }
        
        # Convert the policy to a JSON string and apply it to the bucket
        bucket_policy_str = str(bucket_policy).replace("'", '"')
        s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_str)
        
        print(f"Permissions granted for the app to read and write to the bucket.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"The bucket '{bucket_name}' already exists and is owned by you.")
        else:
            print(f"Error creating bucket '{bucket_name}': {e}")

def check_dynamodb_table_exists(table_name, user_arn):
    dynamodb = boto3.client('dynamodb')
    
    existing_tables = dynamodb.list_tables()['TableNames']
    
    if table_name in existing_tables:
        print(f"DynamoDB table '{table_name}' exists.")
        if table_name == user_table:
            check_table_entries(user_table, user_arn)
        elif table_name == vehicle_table:
            check_table_entries(user_table, user_arn)
        return True
    else:
        if table_name == user_table:
            print(f"DynamoDB table '{table_name}' does not exist.")
            create_dynamodb_user_table(table_name, user_arn)
            print(f"DynamoDB table '{table_name}' created.")
            check_table_entries(user_table, user_arn)
        elif table_name == vehicle_table:
            print(f"DynamoDB table '{table_name}' does not exist.")
            create_dynamodb_vehicle_table(table_name, user_arn)
            print(f"DynamoDB table '{table_name}' created.")
            check_table_entries(vehicle_table, user_arn)
        else:
            print("Table name doesn't match user_table or vehicle_table. No action taken.")
        return False


def create_dynamodb_user_table(table_name, user_arn):
    dynamodb = boto3.client('dynamodb')
    app_user_arn = get_user_arn(flask_app_user)

    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'userid',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'userid',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String
                }
                # Add other attribute definitions here as needed
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            # Define access permissions for the app's IAM user
            # Replace 'YOUR_APP_ARN' with the actual ARN of the app's IAM user
            # Ensure to provide necessary permissions as required
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ]
        )

        # Wait for table creation to be active
        dynamodb.get_waiter('table_exists').wait(TableName=table_name)
        print(f"DynamoDB table '{table_name}' created successfully.")

        check_table_entries(user_table, user_arn)

    except dynamodb.exceptions.ResourceInUseException:
        print(f"DynamoDB table '{table_name}' already exists.")
        check_table_entries(user_table, user_arn)
        
def check_table_entries(table_name, user_arn):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    try:
        response = table.scan()
        items = response.get('Items', [])

        if not items:
            print(f"No entries found in DynamoDB table '{table_name}'.")
            if table_name == user_table:
                add_initial_user_entries_to_table(table_name)
            elif table_name == vehicle_table:  # Assuming you have a variable named vehicle_table with the stored value
                add_initial_vehicle_entries_to_table(vehicle_table, "0123456789", "1234567890")
            else:
                print("Table name doesn't match user_table or vehicle_table. No action taken.")
        else:
            print(f"Entries found in DynamoDB table '{table_name}':")

    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print(f"DynamoDB table '{table_name}' does not exist.")
    except Exception as e:
        print(f"An error occurred while scanning DynamoDB table '{table_name}': {e}")

def generate_hash_with_salt(input_string):
    salt = secrets.token_hex(16)  # Generate a random 128-bit salt (16 bytes)

    salted_string = input_string + salt

    hash_object = hashlib.sha256()
    hash_object.update(salted_string.encode('utf-8'))
    hashed_result = hash_object.hexdigest()

    return hashed_result, salt

def verify_hash(input_string, stored_hash, salt):
    hash_object = hashlib.sha256()
    input_with_salt = (input_string + salt).encode('utf-8')
    
    # Debugging: Print the intermediate hashed result for verification
    hash_object.update(input_with_salt)
    intermediate_hashed_result = hash_object.hexdigest()
    print(f"Intermediate hashed result: {intermediate_hashed_result}")

    hash_object = hashlib.sha256()
    hash_object.update(input_with_salt)
    hashed_result = hash_object.hexdigest()

    return hashed_result == stored_hash

def add_initial_user_entries_to_table(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    with open('initial_users.json') as f:
        initial_users = json.load(f)

    for user_data in initial_users:
        hashed_password, salt = generate_hash_with_salt(user_data['password'])  # Change to use the same hashing method
        user_item = {
            'userid': user_data['userid'],
            'passwordhash': hashed_password,
            'salt': salt,
            'email': user_data['email'],
            'phone': user_data['phone'],
            'username': user_data['username'],
            'firstname': user_data['firstname'],
            'lastname': user_data['lastname'],
            'address': user_data['address']
        }

        table.put_item(Item=user_item)

    print("Initial entries added to DynamoDB table.")

def create_dynamodb_vehicle_table(table_name, user_arn):
    dynamodb = boto3.client('dynamodb')

    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'vh-id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'vh-id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'userid',
                    'AttributeType': 'S'
                }
                # Add other attribute definitions used in KeySchema or GlobalSecondaryIndexes
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserIdIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'userid',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ]
        )

        # Wait for table creation to be active
        dynamodb.get_waiter('table_exists').wait(TableName=table_name)
        print(f"DynamoDB table '{table_name}' created successfully.")

        check_table_entries(table_name, user_arn)

    except dynamodb.exceptions.ResourceInUseException:
        print(f"DynamoDB table '{table_name}' already exists.")
        check_table_entries(table_name, user_arn)


import json
import boto3
from datetime import datetime
import uuid
import random
import string

def add_initial_vehicle_entries_to_table(table_name, userid1, userid2):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    with open('initial_vehicles.json') as f:
        initial_vehicles = json.load(f)

    for vehicle in initial_vehicles:
        vehicle['datejoined'] = str(datetime.now())
        vh_id = str(uuid.uuid4())
        reg = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        engine_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        vehicle['vh-id'] = vh_id
        vehicle['reg'] = reg
        vehicle['engine_no'] = engine_no

        # Assign the correct userid based on the entry
        if vehicle['userid'] == 'user1':
            vehicle['userid'] = userid1
        elif vehicle['userid'] == 'user2':
            vehicle['userid'] = userid2

        table.put_item(Item=vehicle)

    print("Initial vehicles added to DynamoDB table.")

# Usage:
# Provide the table name, user ids for userid1 and userid2
# add_initial_vehicle_entries_to_table('YourTableName', 'user1_id', 'user2_id')




if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0')
