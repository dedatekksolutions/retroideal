from datetime import datetime, timedelta
import time
import boto3
import json
import uuid
import random
import string
import requests
from botocore.exceptions import ClientError
from utilities.helpers import generate_hash_with_salt, verify_hash

flask_app_user="retroideal-flask"
member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"
user_table="retroideal-user-credentials"
vehicle_table="retroideal-vehicle-table"
vehicle_image_table="retroideal-vehicle-image-table"
pending_images_folder="pending-vehicle-images"
approved_images_folder="approved-vehicle-images"


def init():
    print("Begin initialisation!")
    user_arn = get_user_arn(flask_app_user)
    check_user_existence(flask_app_user)
    check_s3_bucket(member_vehicle_images_bucket_name, user_arn)
    check_dynamodb_table_exists(user_table, user_arn)
    check_dynamodb_table_exists(vehicle_table, user_arn)
    check_dynamodb_table_exists(vehicle_image_table, user_arn)
    check_folder_exists(member_vehicle_images_bucket_name, pending_images_folder)
    check_folder_exists(member_vehicle_images_bucket_name, approved_images_folder)
    check_images_in_folder(member_vehicle_images_bucket_name, approved_images_folder)
    print("Application initialized!")

def iterate_vehicle_and_image_urls(bucket_name, folder_name):
    try:
        with open('initial_vehicles.json', 'r') as vehicle_file, open('initial_images.json', 'r') as image_file:
            vehicle_data = json.load(vehicle_file)
            image_data = json.load(image_file)
            vehicles = vehicle_data if isinstance(vehicle_data, list) else []
            images = image_data.get('images', []) if isinstance(image_data, dict) else []

            if len(vehicles) != len(images):
                print("Unequal number of vehicles and images. Cannot proceed.")
                return

            for index, vehicle in enumerate(vehicles):
                if index < len(images):  # Ensure the index is within the range of images
                    vehicle_id = vehicle.get('vh_id')  # Assuming 'vh_id' key exists in vehicle JSON
                    image_url = images[index].get('url')  # Extracting 'url' from the image entry
                    userid = vehicle.get('userid')
                    approval = "approved"
                    purpose = str(datetime.now())
                    image_id = str(uuid.uuid4())
                    upload_image_to_s3_from_url(bucket_name, folder_name, image_id, image_url)
                    path, image_url = get_image_url_and_path(bucket_name, folder_name, image_id)
                    add_entry_to_vehicle_image_table(vehicle_image_table, image_id, userid, vehicle_id, image_url, approval, purpose, image_id, path)
    except FileNotFoundError:
        print("File 'initial_vehicles.json' or 'initial_images.json' not found.")
        pass
    except json.JSONDecodeError:
        print("Error decoding JSON data from 'initial_vehicles.json' or 'initial_images.json'.")
        pass
    except Exception as e:
        print("An error occurred:", e)
        pass

def check_images_in_folder(bucket_name, folder_name):
    s3 = boto3.client('s3')
    try:
        # Get a list of objects in the specified folder
        objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_name)

        # Check if there are at least six images in the folder
        if 'Contents' in objects and len(objects['Contents']) >= 6:
            print(f"At least six images found in the '{folder_name}' folder.")
        else:
            print(f"Less than six images found in the '{folder_name}' folder.")
            iterate_vehicle_and_image_urls(member_vehicle_images_bucket_name, approved_images_folder)
    except Exception as e:
        print(f"An error occurred: {e}")

def get_image_url_and_path(bucket_name, folder_name, image_id):
    s3 = boto3.client('s3')
    file_name = f"{image_id}.jpg"  # Make sure this matches the filename format used while uploading
    s3_key = f"{folder_name}/{file_name}"
    image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

    return file_name, image_url

def add_entry_to_vehicle_image_table(table_name, image_id, userid, vehicle_id, image_url, status, purpose, filename, path):
    dynamodb = boto3.client('dynamodb')

    # Define item attributes
    item = {
        'image-id': {'S': image_id},
        'userid': {'S': userid},
        'vehicle-id': {'S': vehicle_id},
        'image-url': {'S': image_url},
        'status': {'S': status},
        'purpose': {'S': purpose},
        'filename': {'S': filename},
        'path': {'S': path}
    }

    try:
        response = dynamodb.put_item(
            TableName=table_name,
            Item=item
        )
        print(f"Entry added to '{table_name}' with image ID: {image_id}")
        return response  # Optional: Return the response from the DynamoDB service
    except Exception as e:
        print("Error adding entry:", e)
        return None  # Return None in case of failure


def upload_image_to_s3_from_url(bucket_name, folder_name, image_id, image_url):
    s3 = boto3.client('s3')
    
    try:
        # Get the image data from the URL
        response = requests.get(image_url)
        if response.status_code == 200:
            image_data = response.content

            # Use image_id as the filename
            file_name = f"{image_id}.jpg"  # You can adjust the file extension as needed

            # Construct the S3 key using folder name and file name
            s3_key = f"{folder_name}/{file_name}"

            # Upload the image data to S3
            s3.put_object(Bucket=bucket_name, Key=s3_key, Body=image_data)

            print(f"Image from URL '{image_url}' uploaded to '{folder_name}' in bucket '{bucket_name}' as '{file_name}'.")
        else:
            print(f"Failed to fetch image from URL '{image_url}'. Status code: {response.status_code}")
    except ClientError as e:
        print("An error occurred:", e)
    except Exception as e:
        print("An error occurred:", e)

def create_vehicle_images_table(table_name, user_arn):
    dynamodb = boto3.resource('dynamodb')
    
    # Define table attributes
    table_attributes = [
        {'AttributeName': 'image-id', 'AttributeType': 'S'},
        {'AttributeName': 'userid', 'AttributeType': 'S'},
        {'AttributeName': 'vehicle-id', 'AttributeType': 'S'},
        {'AttributeName': 'image-url', 'AttributeType': 'S'},
        {'AttributeName': 'status', 'AttributeType': 'S'},
        {'AttributeName': 'purpose', 'AttributeType': 'S'},
        {'AttributeName': 'filename', 'AttributeType': 'S'},  # New attribute for filename
        {'AttributeName': 'path', 'AttributeType': 'S'}         # New attribute for path
    ]

    # Define primary key
    key_schema = [
        {'AttributeName': 'image-id', 'KeyType': 'HASH'},  # Partition key
    ]

    # Create table parameters
    provisioned_throughput = {
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    }

    # Create table
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=key_schema,
        AttributeDefinitions=table_attributes[:1],  # Use only the primary key in AttributeDefinitions
        ProvisionedThroughput=provisioned_throughput
    )

    # Wait until table is created
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

    print(f"Table '{table_name}' created successfully.")


def create_folder(bucket_name, folder_name):
    s3 = boto3.client('s3')

    try:
        # Put an empty object (file) to create a folder in S3
        s3.put_object(Bucket=bucket_name, Key=(folder_name + '/'))
        print(f"Folder '{folder_name}' created in bucket '{bucket_name}'.")
    except Exception as e:
        print("An error occurred:", e)
        raise

def check_folder_exists(bucket_name, folder_name):
    s3 = boto3.client('s3')

    try:
        # Use head_object to check if the folder exists
        response = s3.head_object(Bucket=bucket_name, Key=(folder_name + '/'))
        print(f"The folder '{folder_name}' exists in the bucket '{bucket_name}'.")
    except s3.exceptions.ClientError as e:
        # If head_object throws an error, the folder doesn't exist
        if e.response['Error']['Code'] == '404':
            print(f"The folder '{folder_name}' does not exist in the bucket '{bucket_name}'.")
            create_folder(bucket_name, folder_name)
        else:
            # Handle other potential errors
            print("An error occurred:", e)
            raise

def delete_resources():
    print("Begin resource deletion!")
    empty_s3_bucket(member_vehicle_images_bucket_name)
    delete_s3_bucket(member_vehicle_images_bucket_name)
    delete_dynamodb_table(user_table)
    delete_dynamodb_table(vehicle_table)
    delete_dynamodb_table(vehicle_image_table)
    print("Resources deleted!")


def empty_s3_bucket(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    for obj in bucket.objects.all():
        obj.delete()

    print(f"Bucket '{bucket_name}' emptied successfully.")


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
        
        # Define the bucket policy granting full access to the app user
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'GiveFlaskAppUserFullAccess',
                'Effect': 'Allow',
                'Principal': {'AWS': user_arn},  # Use the IAM user's ARN
                'Action': ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
                'Resource': [f'arn:aws:s3:::{bucket_name}', f'arn:aws:s3:::{bucket_name}/*']
            }]
        }
        
        
        # Convert the policy to a JSON string and apply it to the bucket
        bucket_policy_str = str(bucket_policy).replace("'", '"')
        s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_str)
        
        print(f"Permissions granted for the app user to read and write to the bucket.")
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
        elif table_name == vehicle_image_table:
            print(f"DynamoDB table '{table_name}' does not exist.")
            create_vehicle_images_table(table_name, user_arn)
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
        reg = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        engine_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        vh_id = vehicle.get('vh_id')
        vehicle['vh-id'] = vh_id
        vehicle['reg'] = reg
        vehicle['engine_no'] = engine_no
        table.put_item(Item=vehicle)

    print("Initial vehicles added to DynamoDB table.")

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


