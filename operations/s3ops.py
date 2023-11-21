from flask import request
import uuid
import boto3

def upload_image_to_s3(bucket_name, folder_name, file_name):
    if request.method == "POST":
            file_data = request.files['fileInput']
            if file_data:
                # Upload the file to S3
                uploaded_filename = str(uuid.uuid4())  # Generate a unique filename
                upload_image_to_s3(
                    file_name=uploaded_filename,
                    image_data=file_data.read()
                )
            

def upload_image_to_s3_passdata(bucket_name, folder_name, file_name, image_data):
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