from flask import Flask, render_template
import boto3
from botocore.exceptions import ClientError
import secrets
import hashlib
import uuid

app = Flask(__name__)

flask_app_user="retroideal-flask"
member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"
user_table="retroideal-user-credentials"

#####################################ROUTES##########################################
@app.route("/")
def index():
    return render_template('index.html')
    
@app.route("/login")
def display_users():
    users = fetch_users()
    return render_template('login.html', users=users)

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
        print(f"DynamoDB table '{table_name}' does not exist.")
        create_dynamodb_user_table(table_name, user_arn)  # Pass user_arn here
        print(f"DynamoDB table '{table_name}' created.")
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
            add_initial_entries_to_table(table_name)
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
    salted_string = input_string + salt

    hash_object = hashlib.sha256()
    hash_object.update(salted_string.encode('utf-8'))
    hashed_result = hash_object.hexdigest()

    return hashed_result == stored_hash

def add_initial_entries_to_table(table_name):
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

    hashed_password1, salt1 = generate_hash_with_salt(password1)

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

    hashed_password2, salt2 = generate_hash_with_salt(password2)

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


if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0')
