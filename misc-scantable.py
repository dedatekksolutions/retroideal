import boto3
import uuid

# Initialize the AWS resources
s3 = boto3.client('s3', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('retroideal-vehicle-images-records')  # Replace with your table name

def create_db_entry(image_key):
    # Generate a unique iid (UUID) for each entry
    iid = str(uuid.uuid4())  # Generate a UUID as a string

    # Construct the item for the DynamoDB table
    item = {
        'iid': iid,
        'image_name': image_key.split('/')[-1],
        'image_url': f"https://your-bucket.s3.amazonaws.com/{image_key}",
        # Add more attributes as needed for your schema
    }

    # Put item into DynamoDB table
    table.put_item(Item=item)
    print(f"Added item with iid: {iid}")

def process_images():
    bucket_name = 'retroideal-approved-images'  # Replace with your S3 bucket name

    # List objects in the S3 bucket
    response = s3.list_objects_v2(Bucket=bucket_name)

    # Process each object in the bucket
    for obj in response.get('Contents', []):
        image_key = obj['Key']
        create_db_entry(image_key)

# Execute the function to process images
process_images()

