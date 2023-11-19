import boto3
from boto3.dynamodb.conditions import Attr
import uuid

member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"
user_table="retroideal-user-credentials"
vehicle_table="retroideal-vehicle-table"
vehicle_image_table="retroideal-vehicle-image-table"
pending_images_folder="pending-vehicle-images"
approved_images_folder="approved-vehicle-images"

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
    print(items)
    return items

def fetch_vehicle_image_data_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)
    response = table.scan(FilterExpression=Attr('user-id').eq(userid))
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

def upload_image_to_s3(bucket_name, folder_name, file_name, image_data):
    s3 = boto3.client('s3')
    
    try:
        # Construct the S3 key using folder name and file name
        s3_key = f"{folder_name}/{file_name}"

        # Upload the image data to S3
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=image_data)

        print(f"Image '{file_name}' uploaded to '{folder_name}' in bucket '{bucket_name}'")
    except Exception as e:
        print("An error occurred:", e)
        raise


def fetch_vehicle_by_reg(vehicle_reg):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_table)
    
    response = table.scan(FilterExpression=Attr('registration').eq(vehicle_reg))
    items = response.get('Items', [])
    
    if items:
        return items[0]  # Assuming registration numbers are unique; return the first match found
    
    return None  # If no match found


def add_pending_image_entry(vehicle_reg, uploaded_filename):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)
    
    # Create a new entry with the pending status
    entry = {
        'image-id': str(uuid.uuid4()),  # Assuming image-id is a UUID
        'vehicle_reg': vehicle_reg,
        'image_url': f"https://your-s3-bucket-url/pending-vehicle-images/{uploaded_filename}",
        'status': 'pending'
        # Add other necessary details
    }
    
    # Put the entry into the DynamoDB table
    table.put_item(Item=entry)

