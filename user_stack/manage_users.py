def fix_user_access_keys():
    """Fix issues with user access keys by cleaning up excess keys."""
    print_header()
    print("Fix User Access Key Issues")
    print("-" * 80)
    print("This tool helps resolve access key errors, such as exceeding the 2-key limit per user.")
    print("It will allow you to delete excess access keys for users.")
    print()
    
    try:
        # Initialize AWS client
        aws_profile = os.environ.get('AWS_PROFILE', 'default')
        session = boto3.Session(profile_name=aws_profile)
        iam_client = session.client('iam')
        
        # Get users from config
        result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
        try:
            current_users = json.loads(result.stdout.strip() or "{}")
        except Exception:
            print("Error: Unable to get current users from Pulumi config")
            current_users = {}
        
        # List all users with their access keys
        user_access_keys = {}
        
        for username in current_users.keys():
            try:
                response = iam_client.list_access_keys(UserName=username)
                keys = response.get('AccessKeyMetadata', [])
                if keys:
                    user_access_keys[username] = keys
            except Exception as e:
                print(f"Warning: Could not fetch access keys for user {username}: {str(e)}")
        
        if not user_access_keys:
            print("No users with access keys found.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Display users with access keys
        print("\nUsers with access keys:")
        user_list = list(user_access_keys.keys())
        for idx, username in enumerate(user_list, 1):
            keys = user_access_keys[username]
            key_count = len(keys)
            status = "ISSUE DETECTED" if key_count >= 2 else "OK"
            print(f"{idx}. {username} - {key_count} keys - {status}")
        
        # Let user select a user to manage
        selection = input("\nSelect user to manage access keys (number) or 0 to exit: ")
        if not selection or selection == "0":
            return
        
        try:
            user_idx = int(selection) - 1
            if user_idx < 0 or user_idx >= len(user_list):
                print("Invalid selection.")
                input("\nPress Enter to return to the main menu...")
                return
            
            selected_user = user_list[user_idx]
            keys = user_access_keys[selected_user]
            
            print(f"\nAccess keys for user {selected_user}:")
            for idx, key in enumerate(keys, 1):
                key_id = key.get('AccessKeyId')
                status = key.get('Status')
                created = key.get('CreateDate').strftime('%Y-%m-%d') if key.get('CreateDate') else 'Unknown'
                print(f"{idx}. Key ID: {key_id} - Status: {status} - Created: {created}")
            
            if len(keys) < 2:
                print("\nThis user has less than 2 access keys. No action needed.")
                input("\nPress Enter to return to the main menu...")
                return
            
            # Let user select a key to delete
            key_selection = input("\nSelect an access key to delete (number) or 0 to exit: ")
            if not key_selection or key_selection == "0":
                return
            
            try:
                key_idx = int(key_selection) - 1
                if key_idx < 0 or key_idx >= len(keys):
                    print("Invalid selection.")
                    input("\nPress Enter to return to the main menu...")
                    return
                
                key_to_delete = keys[key_idx]['AccessKeyId']
                
                # Confirm deletion
                confirm = input(f"\nAre you sure you want to delete access key {key_to_delete}? (yes/no): ").lower()
                if confirm != "yes":
                    print("Deletion cancelled.")
                    input("\nPress Enter to return to the main menu...")
                    return
                
                # Delete the key
                iam_client.delete_access_key(
                    UserName=selected_user,
                    AccessKeyId=key_to_delete
                )
                
                print(f"\nSuccessfully deleted access key {key_to_delete} for user {selected_user}.")
                print("You can now try creating a new access key for this user.")
                
            except ValueError:
                print("Invalid selection.")
            except Exception as e:
                print(f"Error deleting access key: {str(e)}")
            
        except ValueError:
            print("Invalid selection.")
        
        input("\nPress Enter to return to the main menu...")
    except Exception as e:
        print(f"Error: {str(e)}")
        input("\nPress Enter to return to the main menu...")#!/usr/bin/env python
"""
AWS IAM User Management Helper Script
-------------------------------------
This script provides a simple menu-driven interface to manage AWS IAM users and groups
using the existing user management scripts.

No programming knowledge required to use this tool.
"""

import os
import sys
import subprocess
import time
import json
import boto3

# Configuration
DEFAULT_STACK_DIR = "user_stack"  # The directory where user management scripts are located

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the script header."""
    clear_screen()
    print("=" * 80)
    print("               AWS IAM USER MANAGEMENT HELPER")
    print("=" * 80)
    print("This tool helps you manage AWS IAM users and groups with Pulumi")
    print("=" * 80)
    print()

def check_environment():
    """Check if the environment is properly set up."""
    # Detect if we're running from user_stack directory
    current_dir = os.path.basename(os.getcwd())
    if current_dir == "user_stack":
        print("Notice: You are running this script from within the user_stack directory.")
        print("For best results, run it from the project root directory.")
        # We're already in user_stack, so we need to modify our perception of paths
        global DEFAULT_STACK_DIR
        DEFAULT_STACK_DIR = "."  # Current directory is the user_stack
    elif not os.path.exists(DEFAULT_STACK_DIR):
        # Try to find the user_stack directory
        if os.path.exists(os.path.join("..", DEFAULT_STACK_DIR)):
            os.chdir("..")
            print("Notice: Changed directory to project root.")
        else:
            print("ERROR: Could not locate the user_stack directory.")
            print("Please run this script from the project root directory or from within user_stack.")
            sys.exit(1)
    
    # Check if AWS profile is set
    if not os.environ.get('AWS_PROFILE'):
        profile = input("AWS_PROFILE is not set. Enter AWS profile name [default]: ").strip()
        if not profile:
            profile = "default"
        os.environ['AWS_PROFILE'] = profile
    
    print(f"AWS Profile: {os.environ.get('AWS_PROFILE')}")
    
    # Verify AWS credentials are working
    try:
        aws_result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                               capture_output=True, text=True)
        if aws_result.returncode != 0:
            print("\nWARNING: AWS credentials validation failed:")
            print(aws_result.stderr)
            configure = input("Do you want to configure AWS credentials now? (yes/no): ").strip().lower()
            if configure == "yes":
                profile = input("Enter AWS profile name to configure: ").strip()
                if profile:
                    subprocess.run(["aws", "configure", "--profile", profile])
                    os.environ['AWS_PROFILE'] = profile
                    print(f"AWS profile '{profile}' configured and set as active.")
                    # Verify again
                    aws_result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                                           capture_output=True, text=True)
                    if aws_result.returncode != 0:
                        print("AWS credentials still not valid. Please check your configuration.")
                        print("You can continue, but operations may fail.")
            else:
                print("Continuing with invalid AWS credentials. Operations may fail.")
        else:
            print("AWS credentials verified successfully.")
    except Exception as e:
        print(f"WARNING: Failed to verify AWS credentials: {str(e)}")
        print("Continuing, but operations may fail.")
    
    # Check Pulumi stack
    try:
        result = subprocess.run(["pulumi", "stack", "ls"], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            print("\nERROR: Pulumi is not properly configured.")
            print("Possible reasons:")
            print("1. Pulumi might not be installed or not in your PATH")
            print("2. You might need to login to Pulumi first")
            print("3. You might need to initialize the Pulumi project in this directory")
            
            fix_pulumi = input("\nDo you want to try to fix Pulumi configuration? (yes/no): ").strip().lower()
            if fix_pulumi == "yes":
                print("\nAttempting to fix Pulumi configuration...")
                
                # Check if Pulumi is installed
                try:
                    subprocess.run(["pulumi", "version"], capture_output=True, text=True)
                    print("Pulumi is installed.")
                except:
                    print("Pulumi command not found. Please install Pulumi first.")
                    print("Visit https://www.pulumi.com/docs/install/ for installation instructions.")
                    sys.exit(1)
                
                # Try to login
                print("\nAttempting to login to Pulumi...")
                subprocess.run(["pulumi", "login"])
                
                # Check if we have a Pulumi.yaml file
                if os.path.exists("Pulumi.yaml"):
                    print("Pulumi project found.")
                else:
                    print("No Pulumi.yaml found in current directory.")
                    if os.path.exists(os.path.join(DEFAULT_STACK_DIR, "Pulumi.yaml")):
                        print(f"Found Pulumi.yaml in {DEFAULT_STACK_DIR} directory.")
                        print(f"Changing to {DEFAULT_STACK_DIR} directory...")
                        os.chdir(DEFAULT_STACK_DIR)
                        # If we changed to user_stack, update DEFAULT_STACK_DIR
                        if DEFAULT_STACK_DIR != ".":
                            DEFAULT_STACK_DIR = "."
                
                # Try to list stacks again
                result = subprocess.run(["pulumi", "stack", "ls"], 
                                       capture_output=True, text=True)
                if result.returncode != 0:
                    print("\nStill unable to list Pulumi stacks.")
                    print("You may need to initialize a new stack with 'pulumi stack init'.")
                    init_stack = input("Would you like to initialize a new stack? (yes/no): ").strip().lower()
                    if init_stack == "yes":
                        stack_name = input("Enter new stack name: ").strip()
                        if stack_name:
                            subprocess.run(["pulumi", "stack", "init", stack_name])
                            print(f"Stack '{stack_name}' initialized.")
                        else:
                            print("No stack name provided. Exiting.")
                            sys.exit(1)
                    else:
                        print("Cannot proceed without a valid Pulumi stack. Exiting.")
                        sys.exit(1)
                else:
                    print("Pulumi configuration fixed successfully!")
            else:
                print("Cannot proceed without a valid Pulumi stack. Exiting.")
                sys.exit(1)
        
        # Try listing stacks again after potential fixes
        result = subprocess.run(["pulumi", "stack", "ls"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("\nAvailable Pulumi stacks:")
            print(result.stdout)
            
            # Get current stack
            result = subprocess.run(["pulumi", "stack", "--show-name"], 
                                   capture_output=True, text=True)
            current_stack = result.stdout.strip()
            
            if not current_stack:
                print("No active Pulumi stack detected.")
                stack_name = input("Enter stack name to select: ").strip()
                if stack_name:
                    subprocess.run(["pulumi", "stack", "select", stack_name])
                    print(f"Selected stack: {stack_name}")
                else:
                    print("No stack selected. Exiting.")
                    sys.exit(1)
            else:
                print(f"Current Pulumi stack: {current_stack}")
        else:
            print("Failed to list Pulumi stacks even after attempting fixes. Exiting.")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Failed to check Pulumi configuration: {str(e)}")
        sys.exit(1)
    
    print("\nEnvironment check completed. Ready to proceed.\n")
    input("Press Enter to continue...")

def run_script(script_name, script_description):
    """Run a specific user management script."""
    print_header()
    print(f"Running: {script_description}")
    print("-" * 80)
    
    script_path = os.path.join(DEFAULT_STACK_DIR, script_name)
    original_dir = os.getcwd()
    
    try:
        # Check if the script exists
        if not os.path.exists(script_path):
            print(f"ERROR: Script '{script_path}' not found.")
            print("Make sure you have all the required scripts in the user_stack directory.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Change to user_stack directory to run the script
        os.chdir(DEFAULT_STACK_DIR)
        
        # Run the script and capture its exit code
        print(f"Executing {script_name}...\n")
        exit_code = subprocess.call([sys.executable, script_name])
        
        # Change back to the original directory
        os.chdir(original_dir)
        
        if exit_code != 0:
            print(f"\nWARNING: The script exited with code {exit_code}")
            print("There might have been an error during execution.")
        else:
            print("\nScript completed successfully!")
        
        input("\nPress Enter to return to the main menu...")
    except Exception as e:
        print(f"\nERROR: Failed to run {script_name}: {str(e)}")
        input("\nPress Enter to return to the main menu...")
        # Make sure we get back to the original directory
        try:
            os.chdir(original_dir)
        except:
            pass

def show_user_credentials(username=None):
    """Show credentials for a specific user or all users."""
    print_header()
    
    if username:
        print(f"Showing Credentials for User: {username}")
    else:
        print("Showing All User Credentials")
    print("-" * 80)
    
    try:
        # First try the stack output command for the specific user
        if username:
            # Try to get the password
            pwd_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_generatedPassword", "--show-secrets"],
                capture_output=True,
                text=True
            )
            
            # Try to get the access key
            key_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_accessKeyId"],
                capture_output=True,
                text=True
            )
            
            # Try to get the secret key
            secret_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_secretAccessKey", "--show-secrets"],
                capture_output=True,
                text=True
            )
            
            print(f"Results for user '{username}':")
            
            if pwd_result.returncode == 0 and pwd_result.stdout.strip():
                print(f"  Console Password: {pwd_result.stdout.strip()}")
            else:
                print("  Console Password: Not available or not set")
            
            if key_result.returncode == 0 and key_result.stdout.strip():
                print(f"  Access Key ID: {key_result.stdout.strip()}")
                if secret_result.returncode == 0 and secret_result.stdout.strip():
                    print(f"  Secret Access Key: {secret_result.stdout.strip()}")
                else:
                    print("  Secret Access Key: Not available or not set")
            else:
                print("  Access Key: Not available or not set")
        else:
            # Show all outputs
            subprocess.run(["pulumi", "stack", "output", "--show-secrets"])
        
        # Show refresh notice
        print("\nNOTE: If you just created a new user and don't see credentials,")
        print("try first refreshing the stack state with option 7 from the main menu,")
        print("then view the credentials again.")
        
        input("\nPress Enter to return to the main menu...")
    except Exception as e:
        print(f"\nERROR: Failed to show credentials: {str(e)}")
        input("\nPress Enter to return to the main menu...")

def refresh_pulumi_state():
    """Refresh the Pulumi state to match the AWS resources."""
    print_header()
    print("Refreshing Pulumi State")
    print("-" * 80)
    print("This will synchronize Pulumi's state with the actual AWS resources.")
    print("It's useful when changes were made outside of Pulumi.")
    print()
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    
    if confirm == "yes":
        try:
            subprocess.run(["pulumi", "refresh", "--yes"])
            print("\nState refresh completed!")
        except Exception as e:
            print(f"\nERROR: Failed to refresh state: {str(e)}")
    else:
        print("\nOperation cancelled.")
    
    input("\nPress Enter to return to the main menu...")

def deploy_changes():
    """Deploy pending changes."""
    print_header()
    print("Deploying Pending Changes")
    print("-" * 80)
    print("This will apply any pending changes to your AWS resources.")
    print()
    
    # First show a preview
    print("Previewing changes...\n")
    try:
        subprocess.run(["pulumi", "preview"])
        
        confirm = input("\nDo you want to apply these changes? (yes/no): ").strip().lower()
        if confirm == "yes":
            subprocess.run(["pulumi", "up", "--yes"])
            print("\nDeployment completed!")
        else:
            print("\nDeployment cancelled.")
    except Exception as e:
        print(f"\nERROR: Failed during deployment: {str(e)}")
    
    input("\nPress Enter to return to the main menu...")

def verify_aws_credentials():
    """Verify AWS credentials are working."""
    print_header()
    print("Verifying AWS Credentials")
    print("-" * 80)
    
    try:
        result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\nAWS credentials are valid. Identity information:")
            print(result.stdout)
        else:
            print("\nERROR: AWS credentials validation failed:")
            print(result.stderr)
            
            # Offer to configure AWS profile
            configure = input("\nDo you want to configure AWS credentials now? (yes/no): ").strip().lower()
            if configure == "yes":
                profile = input("Enter AWS profile name to configure: ").strip()
                if profile:
                    subprocess.run(["aws", "configure", "--profile", profile])
                    # Set the newly configured profile
                    os.environ['AWS_PROFILE'] = profile
                    print(f"\nAWS profile '{profile}' configured and set as active.")
    except Exception as e:
        print(f"\nERROR: Failed to verify AWS credentials: {str(e)}")
    
    input("\nPress Enter to return to the main menu...")

def main():
    """Main function."""
    # Check environment once at startup
    print_header()
    check_environment()
    
    while True:
        print_header()
        print("MAIN MENU")
        print("-" * 80)
        print("1. Create New User")
        print("2. Edit Existing User")
        print("3. Delete User")
        print("4. Import Existing AWS User")
        print("5. Sync All AWS Users")
        print("6. Show User Credentials")
        print("7. Refresh Pulumi State")
        print("8. Deploy Pending Changes")
        print("9. Fix User Access Key Issues")
        print("10. Verify AWS Credentials")
        print("0. Exit")
        print("-" * 80)
        
        choice = input("Enter your choice (0-10): ").strip()
        
        if choice == "1":
            run_script("create_user.py", "Create New User")
        elif choice == "2":
            run_script("edit_user.py", "Edit Existing User")
        elif choice == "3":
            run_script("delete_user.py", "Delete User")
        elif choice == "4":
            run_script("import_user.py", "Import Existing AWS User")
        elif choice == "5":
            run_script("sync_users.py", "Sync All AWS Users")
        elif choice == "6":
            # Ask if they want to see credentials for a specific user
            print_header()
            print("Show User Credentials")
            print("-" * 80)
            specific_user = input("Enter a specific username (or leave blank for all users): ").strip()
            if specific_user:
                show_user_credentials(specific_user)
            else:
                show_user_credentials()
        elif choice == "7":
            refresh_pulumi_state()
        elif choice == "8":
            deploy_changes()
        elif choice == "9":
            fix_user_access_keys()
        elif choice == "10":
            verify_aws_credentials()
        elif choice == "0":
            print("\nExiting User Management Helper. Goodbye!")
            break
        else:
            print("\nInvalid choice! Please try again.")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERROR: An unexpected error occurred: {str(e)}")
        sys.exit(1)