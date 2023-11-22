import boto3
from boto3.dynamodb.conditions import Attr, Key

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

def fetch_images_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)

    try:
        # Query the vehicle image table based on userid
        response = table.scan(FilterExpression=Attr('userid').eq(userid))
        items = response['Items']

        # Extract image URLs from the items
        image_urls = [item['image-url'] for item in items]

        # Print statements for debugging
        print("Image URLs for userid:", userid)
        print(image_urls)

        return image_urls

    except Exception as e:
        print("Error fetching images:", e)
        return []
    
def fetch_vehicles_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_table)
    response = table.scan(FilterExpression=Attr('userid').eq(userid))
    items = response['Items']

    return items


def fetch_images_by_vehicle_id(vehicle_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)

    try:
        # Query the vehicle image table based on vehicle_id
        response = table.scan(FilterExpression=Attr('vehicle-id').eq(vehicle_id))
        items = response['Items']

        # Extract image URLs from the items
        image_urls = [item['image-url'] for item in items]

        # Print statements for debugging
        print("Image URLs for vehicle_id:", vehicle_id)
        print(image_urls)

        return image_urls

    except Exception as e:
        print("Error fetching images:", e)
        return []

def fetch_vehicle_by_id(vehicle_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_table)

    try:
        # Query the vehicle table based on vehicle_id
        response = table.query(
            KeyConditionExpression=Key('vehicle_id').eq(vehicle_id)
        )
        items = response['Items']

        # Print statements for debugging
        print("Vehicles for vehicle_id:", vehicle_id)
        print(items)

        return items

    except Exception as e:
        print("Error fetching vehicles:", e)
        return []
