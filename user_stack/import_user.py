import json
import subprocess
import boto3
import time
import sys

def main():
    # Initialize AWS clients
    session = boto3.Session(profile_name='pulumi-dev')
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
    
    # Get existing Pulumi state
    state_output = subprocess.run(["pulumi", "stack", "export"], capture_output=True, text=True)
    existing_state = json.loads(state_output.stdout) if state_output.returncode == 0 else {}
    existing_resources = existing_state.get('deployment', {}).get('resources', [])
    
    # Extract existing user resource names
    existing_user_names = []
    existing_group_memberships = []
    for resource in existing_resources:
        if resource.get('type') == 'aws:iam/user:User':
            # Extract username from URN
            urn = resource.get('urn', '')
            parts = urn.split('::')
            if len(parts) > 3:
                resource_name = parts[3].replace('aws:iam/user:User::', '')
                existing_user_names.append(resource_name)
        elif resource.get('type') == 'aws:iam/userGroupMembership:UserGroupMembership':
            urn = resource.get('urn', '')
            parts = urn.split('::')
            if len(parts) > 3:
                resource_name = parts[3].replace('aws:iam/userGroupMembership:UserGroupMembership::', '')
                existing_group_memberships.append(resource_name)
    
    # Build a dictionary of users with their properties
    users_dict = {}
    users_to_import = []
    
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
        
        # Check if user needs to be imported
        resource_name = f"user-{username}"
        if resource_name not in existing_user_names:
            users_to_import.append(username)
            print(f"User '{username}' will be imported")
        else:
            print(f"User '{username}' already exists in Pulumi state - skipping")
    
    # Save the users to Pulumi config
    updated_users = json.dumps(users_dict)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    print(f"Added {len(users_dict)} AWS users to Pulumi config")
    
    if not users_to_import:
        print("No users to import - all users already exist in Pulumi state")
        return
    
    # Ask if user wants to proceed with importing resources
    proceed = input(f"Proceed with importing {len(users_to_import)} new users into Pulumi state? (yes/no): ").lower()
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
    
    # Import only the users that don't exist in state
    for username in users_to_import:
        user_info = users_dict[username]
        resource_id = username
        resource_name = f"user-{username}"
        
        print(f"Importing user '{username}'...")
        import_cmd = ["pulumi", "import", "aws:iam/user:User", resource_name, resource_id, "--yes"]
        result = subprocess.run(import_cmd)
        if result.returncode != 0:
            print(f"Failed to import user '{username}'")
            continue
        
        # If user has groups, import group memberships
        if user_info["groups"]:
            groups_str = ",".join(user_info["groups"])
            resource_id = f"{username}/{groups_str}"
            resource_name = f"userGroupMembership-{username}"
            
            # Check if group membership already exists
            if resource_name not in existing_group_memberships:
                print(f"Importing group memberships for '{username}'...")
                import_cmd = ["pulumi", "import", "aws:iam/userGroupMembership:UserGroupMembership", 
                             resource_name, resource_id, "--yes"]
                subprocess.run(import_cmd)
            else:
                print(f"Group membership for '{username}' already exists - skipping")
    
    # Restore original __main__.py
    print("Restoring original Pulumi program...")
    with open("__main__.py.backup", "r") as f:
        original_content = f.read()
    
    with open("__main__.py", "w") as f:
        f.write(original_content)
    
    # Remove backup
    subprocess.run(["rm", "__main__.py.backup"])
    
    print("\nImport completed! Now run 'pulumi up' to apply any changes.")
    print("Only new users have been imported into Pulumi state.")

if __name__ == "__main__":
    main()