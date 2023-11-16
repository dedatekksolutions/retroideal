import boto3

def check_or_create_dynamodb_table():
    # Define the DynamoDB table name
    table_name = 'retroideal-vehicle-images-records'

    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    # Check if the table already exists
    existing_tables = dynamodb.meta.client.list_tables()['TableNames']

    if table_name in existing_tables:
        # Table exists
        print(f"Table '{table_name}' already exists.")
        return "Exists"

    # Create a new DynamoDB table if it doesn't exist
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'iid',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'iid',
                'AttributeType': 'S'  # Assuming iid is a string
            }
            # Add more AttributeDefinitions as needed for other attributes
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    # Wait for the table to be created
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

    # The table has been created
    print(f"Table '{table_name}' has been created.")
    return "Created"

# Call the function to check/create the table
result = check_or_create_dynamodb_table()
print(result)

