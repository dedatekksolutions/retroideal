from application import boto3, user_table, vehicle_table, Attr

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
