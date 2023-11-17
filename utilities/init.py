from datetime import datetime, timedelta
import boto3
import json
import uuid
import random
import string
from botocore.exceptions import ClientError
from utilities.helpers import generate_hash_with_salt, verify_hash


flask_app_user="retroideal-flask"
member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"
user_table="retroideal-user-credentials"
vehicle_table="retroideal-vehicle-table"

def delete_resources():
    print("Begin resource deletion!")
    delete_s3_bucket('retroideal-member-vehicle-images')
    delete_dynamodb_table('retroideal-user-credentials')
    delete_dynamodb_table('retroideal-vehicle-table')
    print("Resources deleted!")

def init():
    print("Begin initialisation!")
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

import boto3
from botocore.exceptions import ClientError

def delete_s3_bucket(bucket_name):
    s3 = boto3.client('s3')
    try:
        response = s3.delete_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' deleted successfully.")
    except ClientError as e:
        print(f"Error deleting bucket '{bucket_name}': {e}")

def delete_dynamodb_table(table_name):
    dynamodb = boto3.client('dynamodb')
    try:
        response = dynamodb.delete_table(TableName=table_name)
        print(f"DynamoDB table '{table_name}' deleted successfully.")
    except ClientError as e:
        print(f"Error deleting DynamoDB table '{table_name}': {e}")

def delete_iam_user(username):
    iam = boto3.client('iam')
    try:
        response = iam.delete_user(UserName=username)
        print(f"IAM user '{username}' deleted successfully.")
    except ClientError as e:
        print(f"Error deleting IAM user '{username}': {e}")


