from flask import Flask
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

flask_app_user="retroideal-flask"
member_vehicle_images_bucket_name = "retroideal-member-vehicle-images"


@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

#initialise resources
def init():
    user_arn = get_user_arn(flask_app_user)
    check_user_existence(flask_app_user)
    check_s3_bucket(member_vehicle_images_bucket_name, user_arn)  
    print("Application initialized!")

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

def get_user_arn(username):
    iam = boto3.client('iam')
    response = iam.get_user(UserName=username)
    user_arn = response['User']['Arn']
    return user_arn


def create_s3_bucket(bucket_name, user_arn):
    s3 = boto3.client('s3')
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created successfully.")
        
        # Define the bucket policy granting full access to the owner (replace with your app/user ID)
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'GiveAppReadWriteAccess',
                'Effect': 'Allow',
                'Principal': {'AWS': user_arn},  # Use the IAM user's ARN
                'Action': ['s3:GetObject', 's3:PutObject'],
                'Resource': f'arn:aws:s3:::{bucket_name}/*'
            }]
        }
        
        # Convert the policy to a JSON string and apply it to the bucket
        bucket_policy_str = str(bucket_policy).replace("'", '"')
        s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_str)
        
        print(f"Permissions granted for the app to read and write to the bucket.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"The bucket '{bucket_name}' already exists and is owned by you.")
        else:
            print(f"Error creating bucket '{bucket_name}': {e}")





if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0')
