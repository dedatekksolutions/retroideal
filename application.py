from flask import Flask, render_template, redirect, request, url_for  # Include 'redirect' and 'url_for' here
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Attr
import boto3
from botocore.exceptions import ClientError
import secrets
import hashlib
import uuid

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

            print("User:", userid)

            # Fetch vehicles for the current user
            user_vehicles = fetch_vehicles_by_userid(userid)

            # Add print statement to display fetched vehicles
            print("Vehicles fetched:", user_vehicles)

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

    print(f"Retrieved vehicles for user with ID {userid}:")
    for vehicle in items:
        print(vehicle)  # Output each vehicle information retrieved from DynamoDB

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
    try:
        response = dynamodb.describe_table(TableName=table_name)
        print(f"DynamoDB table '{table_name}' exists.")
        check_table_entries(user_table, user_arn)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        if table_name == user_table:
            try:
                response = dynamodb.describe_table(TableName=table_name)
                print(f"DynamoDB table '{table_name}' exists.")
                check_table_entries(user_table, user_arn)
                return True
            except dynamodb.exceptions.ResourceNotFoundException:
                    print(f"DynamoDB table '{table_name}' does not exist.")
                    create_dynamodb_user_table(table_name, user_arn)
                    print(f"DynamoDB table '{table_name}' created.")
        elif table_name == vehicle_table:  # Assuming you have a variable named vehicle_table with the stored value
            try:
                response = dynamodb.describe_table(TableName=table_name)
                print(f"DynamoDB table '{table_name}' exists.")
                check_table_entries(user_table, user_arn)
                return True
            except dynamodb.exceptions.ResourceNotFoundException:
                    print(f"DynamoDB table '{table_name}' does not exist.")
                    create_dynamodb_vehicle_table(table_name, user_arn)  # Pass user_arn here
                    print(f"DynamoDB table '{table_name}' created.")
        else:
            print("Table name doesn't match user_table or vehicle_table. No action taken.")
        return False  # Adjust the indentation here to match the try block
    

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

        # Define the policy granting access to the app's IAM user
        table_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'AWS': user_arn},
                'Action': ['dynamodb:Query', 'dynamodb:Scan', 'dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem'],
                'Resource': f'arn:aws:dynamodb:*:*:table/{table_name}'
            }]
        }

        # Apply the policy to the table
        table_policy_str = str(table_policy).replace("'", '"')
        dynamodb.put_table_policy(TableName=table_name, PolicyName='AppAccessPolicy', PolicyDocument=table_policy_str)
        print(f"Permissions granted for the app user to read and write to the table.")

        check_table_entries(user_table, user_arn)

    except dynamodb.exceptions.ResourceInUseException:
        print(f"DynamoDB table '{table_name}' already exists.")
        check_table_entries(user_table, user_arn)
        
def check_table_entries(table_name, user_arn):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    print(f"Test193")
    try:
        response = table.scan()
        items = response.get('Items', [])

        if not items:
            print(f"No entries found in DynamoDB table '{table_name}'.")
            if table_name == user_table:
                add_initial_user_entries_to_table(table_name)
            elif table_name == vehicle_table:  # Assuming you have a variable named vehicle_table with the stored value
                add_initial_vehicle_entries_to_table(vehicle_table, "user_id_1", "user_id_2")
            else:
                print("Table name doesn't match user_table or vehicle_table. No action taken.")
        else:
            print(f"Entries found in DynamoDB table '{table_name}':")
            for item in items:
                print(item)  

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

    # Entry 1
    userid1 = str(uuid.uuid4())
    password1 = "testpassword1"
    email1 = "email1@email.com"
    phone1 = "1234567890"
    username1 = "testuser1"
    firstname1 = "testfirstname1"
    lastname1 = "testlastname1"
    address1 = "1 test st testville testies test 12345"

    hashed_password1, salt1 = generate_hash_with_salt(password1)  # Change to use the same hashing method

    item1 = {
        'userid': userid1,
        'passwordhash': hashed_password1,
        'salt': salt1,
        'email': email1,
        'phone': phone1,
        'username': username1,
        'firstname': firstname1,
        'lastname': lastname1,
        'address': address1
    }

    # Entry 2
    userid2 = str(uuid.uuid4())
    password2 = "testpassword0"
    email2 = "email0@email.com"
    phone2 = "0123456789"
    username2 = "testuser0"
    firstname2 = "testfirstname0"
    lastname2 = "testlastname0"
    address2 = "0 test st testville testies test 01234"

    hashed_password2, salt2 = generate_hash_with_salt(password2)  # Change to use the same hashing method

    item2 = {
        'userid': userid2,
        'passwordhash': hashed_password2,
        'salt': salt2,
        'email': email2,
        'phone': phone2,
        'username': username2,
        'firstname': firstname2,
        'lastname': lastname2,
        'address': address2
    }

    # Put items into the DynamoDB table
    table.put_item(Item=item1)
    table.put_item(Item=item2)

    print("Initial entries added to DynamoDB table.")

import boto3
import uuid
from datetime import datetime
import random
import string

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

        # Define the policy granting access to the app's IAM user
        # Apply the policy to the table (if the put_table_policy is available in your AWS version)

        print(f"Permissions granted for the app user to read and write to the table.")

        check_table_entries(table_name, user_arn)

    except dynamodb.exceptions.ResourceInUseException:
        print(f"DynamoDB table '{table_name}' already exists.")
        check_table_entries(table_name, user_arn)


def add_initial_vehicle_entries_to_table(table_name, userid1, userid2):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Get the current year
    current_year = datetime.now().year

    # Calculate the year 25 years ago
    year_25_years_ago = current_year - 25

    # Create vehicles for user 1
    for i in range(1, 4):
        vehicle_year = year_25_years_ago - i  # Creating vehicles 25, 26, and 27 years old
        vh_id = str(uuid.uuid4())
        vin = f"VIN{i}"
        chassis_no = f"Chassis{i}"
        make = f"Make{i}"
        model = f"Model{i}"
        year = str(vehicle_year)
        variant = f"Variant{i}"
        date_joined = str(datetime.now())
        reg = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generate a 6-character alphanumeric string for reg

        item = {
            'vh-id': vh_id,
            'vin': vin,
            'chassisno': chassis_no,
            'make': make,
            'model': model,
            'year': year,
            'variant': variant,
            'userid': userid1,
            'datejoined': date_joined,
            'reg': reg  # Add the 'reg' attribute to the item
        }

        # Only put the item if all attributes are included
        table.put_item(Item=item)

    # Create vehicles for user 2
    for i in range(4, 7):
        vehicle_year = year_25_years_ago - i  # Creating vehicles 28, 29, and 30 years old
        vh_id = str(uuid.uuid4())
        vin = f"VIN{i}"
        chassis_no = f"Chassis{i}"
        make = f"Make{i}"
        model = f"Model{i}"
        year = str(vehicle_year)
        variant = f"Variant{i}"
        date_joined = str(datetime.now())
        reg = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generate a 6-character alphanumeric string for reg

        item = {
            'vh-id': vh_id,
            'vin': vin,
            'chassisno': chassis_no,
            'make': make,
            'model': model,
            'year': year,
            'variant': variant,
            'userid': userid2,
            'datejoined': date_joined,
            'reg': reg  # Add the 'reg' attribute to the item
        }

        # Only put the item if all attributes are included
        table.put_item(Item=item)

    print("Initial vehicles added to DynamoDB table.")



if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0')
