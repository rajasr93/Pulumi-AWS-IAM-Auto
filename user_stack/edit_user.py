import json
import subprocess
import boto3
import sys

def main():
    # Initialize AWS client
    session = boto3.Session(profile_name='pulumi-dev')
    iam_client = session.client('iam')
    
    # Retrieve the current 'users' config as a JSON object
    result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
    try:
        current_users = json.loads(result.stdout.strip() or "{}")
    except Exception:
        print("Error: Unable to get current users from Pulumi config")
        return
    
    # List available users
    print("Available users:")
    for idx, username in enumerate(current_users.keys(), 1):
        print(f"{idx}. {username}")
    
    # Let the user select a user
    try:
        selection = int(input("\nSelect user by number: ")) - 1
        username = list(current_users.keys())[selection]
    except (ValueError, IndexError):
        print("Invalid selection")
        return
    
    # Get current groups
    user_config = current_users[username]
    current_groups = user_config.get("groups", [])
    
    # Also get groups from AWS to verify
    try:
        aws_groups_response = iam_client.list_groups_for_user(UserName=username)
        aws_groups = [group['GroupName'] for group in aws_groups_response['Groups']]
        
        if set(current_groups) != set(aws_groups):
            print(f"\nWARNING: Pulumi config groups {current_groups} differ from AWS groups {aws_groups}")
            sync_choice = input("Sync from AWS to Pulumi? (yes/no): ").lower()
            if sync_choice == "yes":
                current_groups = aws_groups
                current_users[username]["groups"] = current_groups
    except iam_client.exceptions.NoSuchEntityException:
        print(f"User {username} not found in AWS")
        return
    
    print(f"\nCurrent groups for {username}: {current_groups}")
    
    # Get available groups
    paginator = iam_client.get_paginator('list_groups')
    all_groups = []
    for page in paginator.paginate():
        for group in page['Groups']:
            all_groups.append(group['GroupName'])
    
    print("\nAvailable groups:")
    for idx, group in enumerate(all_groups, 1):
        status = "[ASSIGNED]" if group in current_groups else ""
        print(f"{idx}. {group} {status}")
    
    # Let user modify groups
    while True:
        print("\nOptions:")
        print("1. Add group")
        print("2. Remove group")
        print("3. Done")
        
        choice = input("Select option: ")
        
        if choice == "1":
            try:
                group_idx = int(input("Enter group number to add: ")) - 1
                group_to_add = all_groups[group_idx]
                if group_to_add not in current_groups:
                    current_groups.append(group_to_add)
                    print(f"Added {group_to_add}")
                else:
                    print(f"{group_to_add} is already assigned")
            except (ValueError, IndexError):
                print("Invalid selection")
        
        elif choice == "2":
            if not current_groups:
                print("No groups to remove")
                continue
            print("\nCurrent groups:")
            for idx, group in enumerate(current_groups, 1):
                print(f"{idx}. {group}")
            try:
                group_idx = int(input("Enter group number to remove: ")) - 1
                group_to_remove = current_groups[group_idx]
                current_groups.remove(group_to_remove)
                print(f"Removed {group_to_remove}")
            except (ValueError, IndexError):
                print("Invalid selection")
        
        elif choice == "3":
            break
        else:
            print("Invalid option")
    
    # Update the user configuration
    current_users[username]["groups"] = current_groups
    
    # Save the updated configuration
    updated_users = json.dumps(current_users)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    
    print(f"\nUser '{username}' updated with groups: {current_groups}")
    
    # Ask if they want to apply changes
    deploy = input("Deploy changes now? (yes/no): ").lower()
    if deploy == "yes":
        print("Running 'pulumi up --yes' to apply changes...")
        subprocess.run(["pulumi", "up", "--yes"])
    else:
        print("Changes saved to config. Run 'pulumi up' when ready to apply.")

if __name__ == "__main__":
    main()