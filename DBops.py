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

def fetch_approved_images_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)

    try:
        # Query the vehicle image table based on userid and status as "pending"
        response = table.scan(
            FilterExpression=Attr('userid').eq(userid) & Attr('status').eq('approved')
        )
        items = response['Items']

        # Extract image URLs from the items
        image_urls = [item['image-url'] for item in items]

        # Print statements for debugging
        print("Pending Image URLs for userid:", userid)
        print(image_urls)

        return image_urls
    except Exception as e:
        print("Error fetching pending images:", e)
        return []

def fetch_pending_images_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_image_table)

    try:
        # Query the vehicle image table based on userid and status as "pending"
        response = table.scan(
            FilterExpression=Attr('userid').eq(userid) & Attr('status').eq('pending')
        )
        items = response['Items']

        # Extract image URLs from the items
        image_urls = [item['image-url'] for item in items]

        # Print statements for debugging
        print("Pending Image URLs for userid:", userid)
        print(image_urls)

        return image_urls
    except Exception as e:
        print("Error fetching pending images:", e)
        return []

    
def fetch_vehicles_by_userid(userid):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(vehicle_table)
    response = table.scan(FilterExpression=Attr('userid').eq(userid))
    items = response['Items']

    return items

def add_entry_to_vehicle_image_table(image_id, user_id, vehicle_id, image_url, status, purpose, filename):
    dynamodb = boto3.client('dynamodb')
    item = {
        'image-id': {'S': image_id},
        'userid': {'S': user_id},
        'vehicle-id': {'S': vehicle_id},
        'image-url': {'S': image_url},
        'status': {'S': status},
        'purpose': {'S': purpose},
        'filename': {'S': filename}
        # Add other attributes as needed
    }

    try:
        response = dynamodb.put_item(
            TableName=vehicle_image_table,
            Item=item
        )
        return "Entry added to DynamoDB table"
    except Exception as e:
        return str(e)