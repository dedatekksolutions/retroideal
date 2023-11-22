import boto3
from boto3.dynamodb.conditions import Attr

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