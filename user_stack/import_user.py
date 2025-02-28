import json
import subprocess
import boto3
import time

def main():
    # Initialize AWS clients
    iam_client = boto3.client('iam')
    
    # Get all existing IAM users
    user_list = []
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            user_list.append({
                'name': user['UserName'],
                'path': user['Path'],
                'arn': user['Arn']
            })
    
    print(f"Found {len(user_list)} users in AWS IAM")
    
    # Build a dictionary of users with their properties
    users_dict = {}
    for user_info in user_list:
        username = user_info['name']
        path = user_info['path']
        
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
        
        # Add user to dictionary
        users_dict[username] = {
            "groups": groups,
            "create_key": has_access_key,
            "has_console_access": has_console_access,
            "path": path
        }
    
    # Save the users to Pulumi config
    updated_users = json.dumps(users_dict)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    print(f"Added {len(users_dict)} AWS users to Pulumi config")
    
    # Ask if user wants to proceed with importing resources
    proceed = input("Proceed with importing users into Pulumi state? This will clean your current state. (yes/no): ").lower()
    if proceed != "yes":
        print("Import cancelled.")
        return
    
    # Create a minimal Pulumi program for import
    print("Creating temporary Pulumi program for import...")
    with open("__main__.py.backup", "w") as f:
        with open("__main__.py", "r") as source:
            f.write(source.read())
    
    with open("__main__.py", "w") as f:
        f.write("""import pulumi
import pulumi_aws as aws

# This is a temporary file for importing existing resources
# It will be replaced after import
""")
    
    # Import each user into Pulumi state
    for username, user_info in users_dict.items():
        resource_id = username
        resource_name = f"user-{username}"
        
        print(f"Importing user '{username}'...")
        import_cmd = ["pulumi", "import", "aws:iam/user:User", resource_name, resource_id, "--yes"]
        subprocess.run(import_cmd)
        
        # If user has groups, import group memberships
        if user_info["groups"]:
            groups_str = ",".join(user_info["groups"])
            resource_id = f"{username}/{groups_str}"
            resource_name = f"userGroupMembership-{username}"
            
            print(f"Importing group memberships for '{username}'...")
            import_cmd = ["pulumi", "import", "aws:iam/userGroupMembership:UserGroupMembership", 
                         resource_name, resource_id, "--yes"]
            subprocess.run(import_cmd)
    
    # Restore original __main__.py
    print("Restoring original Pulumi program...")
    with open("__main__.py.backup", "r") as f:
        original_content = f.read()
    
    with open("__main__.py", "w") as f:
        f.write(original_content)
    
    # Remove backup
    subprocess.run(["rm", "__main__.py.backup"])
    
    print("\nImport completed! Now run 'pulumi up' to apply any changes.")
    print("Existing users have been imported into Pulumi state and will be updated rather than recreated.")

if __name__ == "__main__":
    main()