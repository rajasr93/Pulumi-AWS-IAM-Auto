import json
import subprocess
import boto3
import os

def get_available_groups():
    """Get available groups from both Pulumi config and AWS for validation."""
    try:
        # Get imported groups from groups_stack config
        result = subprocess.run(
            ["pulumi", "config", "get", "imported_groups", "--cwd", "../groups_stack"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            imported_groups = json.loads(result.stdout.strip())
            pulumi_groups = list(imported_groups.keys())
        else:
            print("  Warning: No imported groups found in groups_stack configuration.")
            print("   Run 'python import_groups.py' in the groups_stack directory first.")
            pulumi_groups = []
        
        # Also get current groups from AWS for validation
        try:
            aws_profile = os.environ.get('AWS_PROFILE', 'default')
            session = boto3.Session(profile_name=aws_profile)
            iam_client = session.client('iam')
            
            aws_groups = []
            paginator = iam_client.get_paginator('list_groups')
            for page in paginator.paginate():
                for group in page['Groups']:
                    aws_groups.append(group['GroupName'])
        except Exception as e:
            print(f"  Warning: Could not fetch AWS groups for validation: {e}")
            aws_groups = []
        
        return pulumi_groups, aws_groups
        
    except Exception as e:
        print(f"Error getting available groups: {e}")
        return [], []

def display_available_groups(pulumi_groups, aws_groups):
    """Display available groups for user selection."""
    print("\n" + "=" * 60)
    print("                 AVAILABLE IAM GROUPS")
    print("=" * 60)
    
    if not pulumi_groups and not aws_groups:
        print(" No groups found!")
        print("\nTo fix this:")
        print("1. Go to groups_stack directory: cd ../groups_stack")
        print("2. Run: python import_groups.py")
        print("3. Run: pulumi up")
        print("4. Return here and try again")
        return False
    
    if pulumi_groups:
        print(" Groups available in Pulumi configuration:")
        for idx, group in enumerate(pulumi_groups, 1):
            print(f"   {idx:2d}. {group}")
    
    if aws_groups and set(aws_groups) != set(pulumi_groups):
        missing_in_pulumi = set(aws_groups) - set(pulumi_groups)
        if missing_in_pulumi:
            print(f"\n  Groups in AWS but not in Pulumi config ({len(missing_in_pulumi)}):")
            for group in sorted(missing_in_pulumi):
                print(f"      • {group}")
            print("   Consider running 'python import_groups.py' in groups_stack to update.")
    
    print("=" * 60)
    return True

def validate_selected_groups(selected_groups, available_groups):
    """Validate that selected groups exist."""
    invalid_groups = []
    for group in selected_groups:
        if group not in available_groups:
            invalid_groups.append(group)
    
    if invalid_groups:
        print(f"\n Error: The following groups don't exist: {', '.join(invalid_groups)}")
        print("Please check the available groups list above.")
        return False
    
    return True

def check_access_key_limit(username):
    """Check if a user already has 2 access keys and warn if so."""
    try:
        session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE', 'default'))
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
    print("=" * 80)
    print("                      CREATE NEW IAM USER")
    print("=" * 80)
    print("This script creates a new IAM user with the imported group assignments.")
    print("=" * 80)
    print()
    
    # Get available groups
    pulumi_groups, aws_groups = get_available_groups()
    
    # Display available groups
    if not display_available_groups(pulumi_groups, aws_groups):
        print("\n Cannot proceed without available groups.")
        return
    
    # Use Pulumi groups as the primary source, fall back to AWS groups if needed
    available_groups = pulumi_groups if pulumi_groups else aws_groups
    
    # Retrieve the current 'users' config as a JSON object (dictionary).
    result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
    try:
        current_users = json.loads(result.stdout.strip() or "{}")
    except Exception:
        current_users = {}

    # Get new username
    print("\n" + "-" * 40)
    new_username = input("Enter the new IAM username: ").strip()
    
    if not new_username:
        print(" Username cannot be empty.")
        return

    # Check if this username already exists
    if new_username in current_users:
        print(f" User '{new_username}' already exists in the configuration.")
        print("Use the edit_user.py script to modify existing users.")
        return

    # Group selection with enhanced interface
    print(f"\n" + "-" * 40)
    print("GROUP SELECTION")
    print("-" * 40)
    print("Enter group names separated by commas.")
    print("You can use:")
    print("• Group numbers from the list above (e.g., 1,3,5)")
    print("• Group names directly (e.g., Developers,Admins)")
    print("• Mixed (e.g., 1,Developers,3)")
    print()
    
    groups_input = input("Enter groups to assign: ").strip()
    
    if not groups_input:
        print("No groups specified. User will be created without group memberships.")
        groups_list = []
    else:
        # Parse input - handle both numbers and names
        groups_list = []
        for item in groups_input.split(","):
            item = item.strip()
            
            # Check if it's a number (group index)
            try:
                group_idx = int(item) - 1
                if 0 <= group_idx < len(available_groups):
                    groups_list.append(available_groups[group_idx])
                else:
                    print(f"  Warning: Group number {item} is out of range. Skipping.")
            except ValueError:
                # It's a group name
                if item in available_groups:
                    groups_list.append(item)
                else:
                    print(f"  Warning: Group '{item}' not found. Skipping.")
        
        # Remove duplicates while preserving order
        groups_list = list(dict.fromkeys(groups_list))
        
        # Validate final group list
        if not validate_selected_groups(groups_list, available_groups):
            print(" Group validation failed. Please try again.")
            return
    
    print(f"\n Selected groups: {groups_list if groups_list else 'None'}")
    
    # Access key configuration
    print(f"\n" + "-" * 40)
    create_key = input("Create an access key for programmatic access? (yes/no): ").strip().lower()
    
    # Console access configuration
    has_console_access = input("Enable console access with password? (yes/no): ").strip().lower()
    
    # User path configuration
    user_path = "/system/"  # Default path for created users
    custom_path = input(f"User path (press Enter for default '{user_path}'): ").strip()
    if custom_path:
        if not custom_path.startswith('/') or not custom_path.endswith('/'):
            print("  Path should start and end with '/'. Auto-correcting...")
            custom_path = f"/{custom_path.strip('/')}/"
        user_path = custom_path
    
    # Check access key limits for groups that might have existing users
    if create_key == "yes":
        for group in groups_list:
            if group in current_users and current_users[group].get("create_key", "no").lower() == "yes":
                check_access_key_limit(group)
    
    # Add the new user object to the dictionary.
    current_users[new_username] = {
        "groups": groups_list,
        "create_key": create_key,
        "has_console_access": has_console_access,
        "path": user_path
    }

    # Save configuration
    updated_users = json.dumps(current_users)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    
    # Display summary
    print("\n" + "=" * 60)
    print("                    USER CREATION SUMMARY")
    print("=" * 60)
    print(f"Username: {new_username}")
    print(f"Path: {user_path}")
    print(f"Groups: {', '.join(groups_list) if groups_list else 'None'}")
    print(f"Access Key: {' Yes' if create_key == 'yes' else ' No'}")
    print(f"Console Access: {'Yes' if has_console_access == 'yes' else ' No'}")
    
    if has_console_access.lower() == "yes":
        print("\n Console Access Notes:")
        print("• A random password will be generated")
        print("• Password change will be required on first login")
        print("• Password will be available in Pulumi outputs after deployment")
    
    print("=" * 60)
    
    # Deploy option
    deploy = input("\n Deploy changes now? (yes/no): ").strip().lower()
    if deploy == "yes":
        print("\n Deploying user creation...")
        result = subprocess.run(["pulumi", "up", "--yes"])
        
        if result.returncode == 0:
            print("\n User created successfully!")
            
            # Try to show the password if console access was enabled
            if has_console_access.lower() == "yes":
                print("\n Retrieving generated password...")
                password_result = subprocess.run(
                    ["pulumi", "stack", "output", f"{new_username}_generatedPassword", "--show-secrets"],
                    capture_output=True,
                    text=True
                )
                
                if password_result.returncode == 0 and password_result.stdout.strip():
                    print(f"Console Password: {password_result.stdout.strip()}")
                else:
                    print("Password not available in outputs. Try running:")
                    print(f"  pulumi refresh --yes")
                    print(f"  pulumi stack output {new_username}_generatedPassword --show-secrets")
            
            # Show access key if created
            if create_key == "yes":
                print("\n Retrieving access key...")
                key_result = subprocess.run(
                    ["pulumi", "stack", "output", f"{new_username}_accessKeyId"],
                    capture_output=True,
                    text=True
                )
                secret_result = subprocess.run(
                    ["pulumi", "stack", "output", f"{new_username}_secretAccessKey", "--show-secrets"],
                    capture_output=True,
                    text=True
                )
                
                if key_result.returncode == 0 and key_result.stdout.strip():
                    print(f"Access Key ID: {key_result.stdout.strip()}")
                    if secret_result.returncode == 0 and secret_result.stdout.strip():
                        print(f"Secret Access Key: {secret_result.stdout.strip()}")
        else:
            print("\n Deployment failed. Check the error messages above.")
    else:
        print(f"\n User '{new_username}' added to configuration.")
        print("Run 'pulumi up' when ready to deploy.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  User creation cancelled.")
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        print("Please check your configuration and try again.")