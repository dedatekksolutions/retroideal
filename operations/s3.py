from flask import request
import uuid


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
            