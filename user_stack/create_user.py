import json
import subprocess
import boto3

def check_access_key_limit(username):
    """Check if a user already has 2 access keys and warn if so."""
    try:
        session = boto3.Session(profile_name='pulumi-dev')
        iam_client = session.client('iam')
        response = iam_client.list_access_keys(UserName=username)
        key_count = len(response.get('AccessKeyMetadata', []))
        
        if key_count >= 2:
            print(f"WARNING: User '{username}' already has {key_count} access keys (the AWS limit is 2).")
            print("You may encounter errors when deploying.")
            delete_key = input("Would you like to delete one of these keys first? (yes/no): ").strip().lower()
            
            if delete_key == "yes":
                # Show the keys
                for idx, key in enumerate(response['AccessKeyMetadata'], 1):
                    key_id = key['AccessKeyId']
                    created = key['CreateDate'].strftime('%Y-%m-%d')
                    status = key['Status']
                    print(f"{idx}. {key_id} - Created: {created} - Status: {status}")
                
                # Let user select which key to delete
                selection = input("Enter the number of the key to delete: ").strip()
                try:
                    key_idx = int(selection) - 1
                    if 0 <= key_idx < len(response['AccessKeyMetadata']):
                        key_to_delete = response['AccessKeyMetadata'][key_idx]['AccessKeyId']
                        iam_client.delete_access_key(
                            UserName=username,
                            AccessKeyId=key_to_delete
                        )
                        print(f"Deleted access key {key_to_delete} for user {username}")
                        return True
                    else:
                        print("Invalid selection. Continuing without deleting.")
                except ValueError:
                    print("Invalid input. Continuing without deleting.")
            
            return False
        
        return True
    except Exception as e:
        print(f"Warning: Could not check access keys for {username}: {str(e)}")
        return True  # Continue anyway

def main():
    # Retrieve the current 'users' config as a JSON object (dictionary).
    result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
    try:
        current_users = json.loads(result.stdout.strip() or "{}")
    except Exception:
        current_users = {}

    new_username = input("Enter the new IAM username: ").strip()

    # Check if this username already exists
    if new_username in current_users:
        print(f"User '{new_username}' already exists in the configuration. Skipping creation.")
        return

    groups_input = input("Enter comma-separated groups to assign (e.g., Beneficiary,Volunteer): ").strip()
    groups_list = [g.strip() for g in groups_input.split(",") if g.strip()]
    
    create_key = input("Create an access key? (yes/no): ").strip().lower()
    has_console_access = input("Enable console access? (yes/no): ").strip().lower()
    
    # Use AWS Console default behavior (root path) for new users
    user_path = "/system/"
    
    # Check if any of the existing users are the same as the groups and have create_key="yes"
    users_to_check = []
    for group in groups_list:
        if group in current_users and current_users[group].get("create_key", "no").lower() == "yes":
            users_to_check.append(group)
    
    # Check access key limits for any matching users
    for username in users_to_check:
        check_access_key_limit(username)
    
    # Add the new user object to the dictionary.
    current_users[new_username] = {
        "groups": groups_list,
        "create_key": create_key,
        "has_console_access": has_console_access,
        "path": user_path
    }

    updated_users = json.dumps(current_users)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    
    print(f"User '{new_username}' added to configuration with path '{user_path}' and groups: {groups_list}")
    if has_console_access.lower() == "yes":
        print(f"A random password will be generated and password change will be required on first login")
        print(f"The generated password will be available in the Pulumi outputs after deployment")
    
    deploy = input("Deploy changes now? (yes/no): ").strip().lower()
    if deploy == "yes":
        subprocess.run(["pulumi", "up", "--yes"])
        
        # Try to show the password
        if has_console_access.lower() == "yes":
            print("\nPassword:")
            password_result = subprocess.run(
                ["pulumi", "stack", "output", f"{new_username}_generatedPassword", "--show-secrets"],
                capture_output=True,
                text=True
            )
            
            if password_result.returncode == 0 and password_result.stdout.strip():
                print(password_result.stdout.strip())
            else:
                print("Password not available in outputs. Try running:")
                print(f"pulumi refresh --yes")
                print(f"pulumi stack output {new_username}_generatedPassword --show-secrets")

if __name__ == "__main__":
    main()