import hashlib
import secrets


def generate_hash_with_salt(input_string):
    salt = secrets.token_hex(16)  # Generate a random 128-bit salt (16 bytes)

    salted_string = input_string + salt

    hash_object = hashlib.sha256()
    hash_object.update(salted_string.encode('utf-8'))
    hashed_result = hash_object.hexdigest()

    return hashed_result, salt

def verify_hash(input_string, stored_hash, salt):
    hash_object = hashlib.sha256()
    input_with_salt = (input_string + salt).encode('utf-8')
    
    # Debugging: Print the intermediate hashed result for verification
    hash_object.update(input_with_salt)
    intermediate_hashed_result = hash_object.hexdigest()
    print(f"Intermediate hashed result: {intermediate_hashed_result}")

    hash_object = hashlib.sha256()
    hash_object.update(input_with_salt)
    hashed_result = hash_object.hexdigest()

    return hashed_result == stored_hash

