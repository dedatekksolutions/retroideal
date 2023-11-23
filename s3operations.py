import boto3
from datetime import datetime
import uuid
from DBops import *

# Assuming you have these variables defined
bucket_name = "retroideal-member-vehicle-images"
pending_images_folder = "pending-vehicle-images"
vehicle_image_table = "retroideal-vehicle-image-table"

def upload_image_to_s3(file, user_id, vehicle_id):
    s3 = boto3.client('s3')
    try:
        unique_filename = str(uuid.uuid4())
        filename = f"{unique_filename}.jpg"

        s3.upload_fileobj(file, bucket_name, f"{pending_images_folder}/{filename}")

        image_url = f"https://{bucket_name}.s3.amazonaws.com/{pending_images_folder}/{filename}"
        status = "pending"
        purpose = str(datetime.now())
        image_id = str(uuid.uuid4())
        
        add_entry_to_vehicle_image_table(image_id, user_id, vehicle_id, image_url, status, purpose, filename)
        
        return "Upload successful"
    except Exception as e:
        return str(e)