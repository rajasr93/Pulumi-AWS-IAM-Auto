import json
import subprocess
import boto3

def main():
    # Initialize AWS clients
    iam_client = boto3.client('iam')
    
    # Retrieve the current 'users' config as a JSON object
    result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
    try:
        current_users = json.loads(result.stdout.strip() or "{}")
    except Exception:
        current_users = {}
    
    print("Syncing all AWS IAM users to Pulumi configuration...")
    
    # Use pagination to get all users regardless of path
    paginator = iam_client.get_paginator('list_users')
    page_iterator = paginator.paginate()  # No PathPrefix means all paths
    
    new_users_added = 0
    
    for page in page_iterator:
        aws_users = page['Users']
        
        # Process each AWS user
        for aws_user in aws_users:
            username = aws_user['UserName']
            user_path = aws_user['Path']
            
            # Skip if user already exists in Pulumi config
            if username in current_users:
                print(f"User '{username}' already exists in Pulumi config - skipping")
                continue
            
            # Get user's group memberships
            groups_response = iam_client.list_groups_for_user(UserName=username)
            groups = [group['GroupName'] for group in groups_response['Groups']]
            
            # Check if the user has console access (login profile)
            has_console_access = "no"
            try:
                iam_client.get_login_profile(UserName=username)
                has_console_access = "yes"
            except iam_client.exceptions.NoSuchEntityException:
                pass
            
            # Check if the user has access keys
            access_keys = iam_client.list_access_keys(UserName=username)
            has_access_key = "yes" if access_keys['AccessKeyMetadata'] else "no"
            
            # Add user to Pulumi config with their original path
            current_users[username] = {
                "groups": groups,
                "create_key": has_access_key,  # Preserve existing setting
                "has_console_access": has_console_access,  # Preserve existing setting
                "path": user_path  # Save the original path
            }
            new_users_added += 1
            print(f"Added user '{username}' with path '{user_path}' and groups: {groups}")
    
    # Update Pulumi config with all users
    if new_users_added > 0:
        updated_users = json.dumps(current_users)
        subprocess.run(["pulumi", "config", "set", "users", updated_users])
        print(f"Added {new_users_added} AWS users to Pulumi config")
    else:
        print("No new users added to Pulumi config")
    
    print("Sync complete!")

if __name__ == "__main__":
    main()