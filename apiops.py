import requests
import json

def verify_image(filename):
    api_url = 'https://ok9ogdv6x0.execute-api.us-east-1.amazonaws.com/prod/DynamoDBManager'

    payload = {
        'filename': [filename]
    }

    try:
        response = requests.post(api_url, data=json.dumps(payload))
        
        if response.status_code == 200:
            return response.json()  # Return JSON response if successful
        else:
            return {'error': f'Failed to verify image. Status code: {response.status_code}'}
    except requests.RequestException as e:
        return {'error': f'Request Exception: {str(e)}'}