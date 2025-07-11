#!/usr/bin/env python
"""
AWS IAM User and Group Management Helper Script
----------------------------------------------
This script provides a comprehensive menu-driven interface to manage AWS IAM users and groups
using Pulumi infrastructure-as-code.

Features:
- User management (create, edit, delete)
- Group management (import, view)
- Comprehensive error handling
- Input validation
- Password-protected credential viewing
- No programming knowledge required
"""

import os
import sys
import subprocess
import time
import json
import boto3
import re
import getpass
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

# Configuration - will be set dynamically
DEFAULT_USER_STACK_DIR = "user_stack"
DEFAULT_GROUPS_STACK_DIR = "groups_stack"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = None

# Security configuration
CREDENTIAL_VIEW_PASSWORD = "ChangeMe!123"
MAX_PASSWORD_ATTEMPTS = 3

# Input validation patterns
USERNAME_PATTERN = re.compile(r'^[\w+=,.@-]+$')  # AWS IAM username pattern
PATH_PATTERN = re.compile(r'^/[\w/]*/$')  # AWS IAM path pattern

def find_project_root():
    """Find the project root by looking for user_stack and groups_stack directories."""
    global PROJECT_ROOT, DEFAULT_USER_STACK_DIR, DEFAULT_GROUPS_STACK_DIR
    
    # Start from current directory
    current = Path.cwd()
    
    # Check if we're already in user_stack or groups_stack
    if current.name == 'user_stack':
        PROJECT_ROOT = current.parent
        DEFAULT_USER_STACK_DIR = "."
        print(f"📁 Detected running from user_stack directory")
        return True
    elif current.name == 'groups_stack':
        PROJECT_ROOT = current.parent
        DEFAULT_GROUPS_STACK_DIR = "."
        os.chdir(PROJECT_ROOT)
        print(f"📁 Detected running from groups_stack directory, moved to project root")
        return True
    
    # Look for the directories in current location
    if (current / DEFAULT_USER_STACK_DIR).exists() and (current / DEFAULT_GROUPS_STACK_DIR).exists():
        PROJECT_ROOT = current
        print(f"📁 Found project root at: {PROJECT_ROOT}")
        return True
    
    # Search up the directory tree
    for parent in current.parents:
        if (parent / DEFAULT_USER_STACK_DIR).exists() and (parent / DEFAULT_GROUPS_STACK_DIR).exists():
            PROJECT_ROOT = parent
            os.chdir(PROJECT_ROOT)
            print(f"📁 Found project root at: {PROJECT_ROOT}")
            print(f"📁 Changed directory to project root")
            return True
    
    # Last resort - check if script is in user_stack
    script_path = Path(SCRIPT_DIR)
    if script_path.name == 'user_stack':
        PROJECT_ROOT = script_path.parent
        os.chdir(PROJECT_ROOT)
        print(f"📁 Script is in user_stack, using parent as project root: {PROJECT_ROOT}")
        return True
    
    print("❌ Could not find project directories (user_stack and groups_stack)")
    print("📁 Current directory:", current)
    print("\nPlease run this script from:")
    print("  - The project root directory (containing user_stack and groups_stack)")
    print("  - Or from within the user_stack directory")
    return False

def setup_aws_profile():
    """Setup or select AWS profile."""
    try:
        # First, check if AWS CLI is installed
        result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ AWS CLI is not installed or not in PATH")
            print("Please install AWS CLI: https://aws.amazon.com/cli/")
            return None
    except FileNotFoundError:
        print("❌ AWS CLI is not installed or not in PATH")
        print("Please install AWS CLI: https://aws.amazon.com/cli/")
        return None
    
    # Check current profile
    current_profile = os.environ.get('AWS_PROFILE', 'default')
    
    # List available profiles
    try:
        result = subprocess.run(["aws", "configure", "list-profiles"], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            available_profiles = result.stdout.strip().split('\n')
            print("\n📋 Available AWS profiles:")
            for idx, profile in enumerate(available_profiles, 1):
                marker = " (current)" if profile == current_profile else ""
                print(f"  {idx}. {profile}{marker}")
            
            # Ask user to select or create new
            print(f"\n  {len(available_profiles) + 1}. Create new profile")
            print("  0. Cancel")
            
            choice = get_numeric_input("\nSelect profile", 0, len(available_profiles) + 1)
            
            if choice == 0:
                return None
            elif choice == len(available_profiles) + 1:
                # Create new profile
                profile_name = input("\nEnter new profile name: ").strip()
                if profile_name:
                    print(f"\nConfiguring AWS profile '{profile_name}'...")
                    subprocess.run(["aws", "configure", "--profile", profile_name])
                    return profile_name
            else:
                # Use existing profile
                return available_profiles[choice - 1]
        else:
            # No profiles found, create one
            print("\n📋 No AWS profiles found.")
            create = get_yes_no_input("Create a new AWS profile?", "yes")
            if create:
                profile_name = input("Enter profile name [default]: ").strip() or "default"
                print(f"\nConfiguring AWS profile '{profile_name}'...")
                subprocess.run(["aws", "configure", "--profile", profile_name])
                return profile_name
                
    except Exception as e:
        print(f"⚠️ Error listing profiles: {e}")
        # Fall back to manual entry
        profile_name = input("\nEnter AWS profile name to use [default]: ").strip() or "default"
        return profile_name
    
    return None

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the script header."""
    clear_screen()
    print("=" * 80)
    print("               AWS IAM USER AND GROUP MANAGEMENT HELPER")
    print("=" * 80)
    print()

def validate_username(username):
    """Validate AWS IAM username format."""
    if not username:
        return False, "Username cannot be empty"
    if len(username) > 64:
        return False, "Username cannot exceed 64 characters"
    if not USERNAME_PATTERN.match(username):
        return False, "Username contains invalid characters. Use only alphanumeric characters and +=,.@-"
    return True, ""

def validate_path(path):
    """Validate AWS IAM path format."""
    if not path:
        return True, ""  # Empty path is okay (will use default)
    if not PATH_PATTERN.match(path):
        return False, "Path must start and end with '/' and contain only alphanumeric characters and '/'"
    if len(path) > 512:
        return False, "Path cannot exceed 512 characters"
    return True, ""

def get_yes_no_input(prompt, default=None):
    """Get validated yes/no input from user."""
    valid_yes = ['yes', 'y', 'true', '1']
    valid_no = ['no', 'n', 'false', '0']
    
    if default is not None:
        prompt += f" [{default}]"
    
    while True:
        try:
            response = input(f"{prompt}: ").strip().lower()
            
            if not response and default is not None:
                response = default.lower()
            
            if response in valid_yes:
                return True
            elif response in valid_no:
                return False
            else:
                print("Please enter 'yes' or 'no'")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return False
        except Exception as e:
            print(f"Error reading input: {e}")
            return False

def get_numeric_input(prompt, min_val=None, max_val=None, allow_zero=True):
    """Get validated numeric input from user."""
    while True:
        try:
            response = input(f"{prompt}: ").strip()
            
            if not response:
                print("Please enter a number")
                continue
                
            value = int(response)
            
            if not allow_zero and value == 0:
                print("Please enter a non-zero number")
                continue
                
            if min_val is not None and value < min_val:
                print(f"Please enter a number >= {min_val}")
                continue
                
            if max_val is not None and value > max_val:
                print(f"Please enter a number <= {max_val}")
                continue
                
            return value
            
        except ValueError:
            print("Invalid input. Please enter a valid number")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None
        except Exception as e:
            print(f"Error reading input: {e}")
            return None

def check_aws_credentials(profile=None):
    """Check and validate AWS credentials."""
    try:
        if profile:
            os.environ['AWS_PROFILE'] = profile
            
        aws_profile = os.environ.get('AWS_PROFILE', 'default')
        print(f"🔑 Using AWS Profile: {aws_profile}")
        
        # Try to create session
        try:
            session = boto3.Session(profile_name=aws_profile)
            sts_client = session.client('sts')
            identity = sts_client.get_caller_identity()
            
            print(f"✅ AWS Account ID: {identity['Account']}")
            print(f"✅ IAM User/Role: {identity['Arn']}")
            print("✅ AWS credentials verified successfully.\n")
            return True, session
            
        except ProfileNotFound:
            print(f"❌ AWS profile '{aws_profile}' not found")
            # Try without profile
            try:
                session = boto3.Session()
                sts_client = session.client('sts')
                identity = sts_client.get_caller_identity()
                print(f"✅ Using default AWS credentials")
                print(f"✅ AWS Account ID: {identity['Account']}")
                return True, session
            except:
                return False, None
                
    except NoCredentialsError:
        print("❌ ERROR: No AWS credentials found.")
        print("Please configure AWS credentials using 'aws configure' or set AWS_PROFILE.")
        return False, None
    except ClientError as e:
        print(f"❌ ERROR: AWS credentials validation failed: {e}")
        return False, None
    except Exception as e:
        print(f"❌ ERROR: Unexpected error verifying AWS credentials: {e}")
        return False, None

def check_pulumi_configuration():
    """Check if Pulumi is properly configured."""
    try:
        result = subprocess.run(["pulumi", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ ERROR: Pulumi is not installed or not in PATH")
            return False
            
        # Check if logged in
        result = subprocess.run(["pulumi", "whoami"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ ERROR: Not logged in to Pulumi")
            print("Run 'pulumi login' to authenticate")
            return False
            
        print("✅ Pulumi is properly configured")
        return True
        
    except FileNotFoundError:
        print("❌ ERROR: Pulumi command not found. Please install Pulumi first.")
        print("Visit https://www.pulumi.com/docs/install/ for installation instructions.")
        return False
    except Exception as e:
        print(f"❌ ERROR: Failed to check Pulumi configuration: {e}")
        return False

def view_groups():
    """View available IAM groups from both Pulumi config and AWS."""
    print_header()
    print("View Available IAM Groups")
    print("-" * 80)
    
    try:
        groups_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_GROUPS_STACK_DIR) if PROJECT_ROOT else DEFAULT_GROUPS_STACK_DIR
        
        # Try to get groups from Pulumi config first
        result = subprocess.run(
            ["pulumi", "config", "get", "imported_groups", "--cwd", groups_stack_path],
            capture_output=True, text=True
        )
        
        pulumi_groups = []
        if result.returncode == 0 and result.stdout.strip():
            imported_groups = json.loads(result.stdout.strip())
            pulumi_groups = list(imported_groups.keys())
            
            print("📁 Groups in Pulumi Configuration:")
            print("-" * 40)
            for idx, group in enumerate(sorted(pulumi_groups), 1):
                group_info = imported_groups[group]
                policy_count = (len(group_info.get('managed_policy_arns', [])) + 
                              len(group_info.get('customer_managed_policies', [])) + 
                              len(group_info.get('inline_policies', {})))
                print(f"   {idx:2d}. {group:<30} ({policy_count} policies)")
            print(f"\n   Total: {len(pulumi_groups)} groups")
        else:
            print("⚠️  No groups found in Pulumi configuration.")
            print("   Run 'Import Groups from AWS' (option 8) first.")
        
        # Also check AWS
        print("\n📁 Checking AWS for groups...")
        valid_creds, session = check_aws_credentials()
        if valid_creds:
            iam_client = session.client('iam')
            aws_groups = []
            
            try:
                paginator = iam_client.get_paginator('list_groups')
                for page in paginator.paginate():
                    for group in page['Groups']:
                        aws_groups.append(group['GroupName'])
                
                # Show groups that are in AWS but not in Pulumi
                missing_in_pulumi = set(aws_groups) - set(pulumi_groups)
                if missing_in_pulumi:
                    print(f"\n⚠️  Groups in AWS but not in Pulumi config ({len(missing_in_pulumi)}):")
                    for group in sorted(missing_in_pulumi):
                        print(f"      • {group}")
                    print("\n   Consider running 'Import Groups from AWS' to update.")
                else:
                    print("✅ All AWS groups are in Pulumi configuration.")
                
                print(f"\n📊 Summary:")
                print(f"   • Groups in Pulumi: {len(pulumi_groups)}")
                print(f"   • Groups in AWS: {len(aws_groups)}")
                print(f"   • Missing in Pulumi: {len(missing_in_pulumi)}")
                
            except ClientError as e:
                print(f"❌ Error fetching AWS groups: {e}")
        else:
            print("❌ Could not verify AWS groups (credentials issue)")
        
    except Exception as e:
        print(f"❌ Error viewing groups: {e}")
    
    input("\nPress Enter to return to the main menu...")

def refresh_pulumi_state():
    """Refresh the Pulumi state to match the AWS resources."""
    print_header()
    print("Refresh Pulumi State")
    print("-" * 80)
    print("This will synchronize Pulumi's state with the actual AWS resources.")
    print("Useful when changes were made outside of Pulumi or to resolve drift.")
    print()
    
    if get_yes_no_input("Do you want to proceed?", "yes"):
        try:
            # Change to user_stack directory
            user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
            original_dir = os.getcwd()
            os.chdir(user_stack_path)
            
            print("\n🔄 Refreshing Pulumi state...")
            print("This may take a moment...\n")
            
            result = subprocess.run(["pulumi", "refresh", "--yes"])
            
            if result.returncode == 0:
                print("\n✅ State refresh completed successfully!")
                print("Pulumi state is now synchronized with AWS.")
            else:
                print("\n❌ State refresh failed. Check the error messages above.")
            
            os.chdir(original_dir)
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to refresh state: {str(e)}")
            try:
                os.chdir(original_dir)
            except:
                pass
    else:
        print("\nOperation cancelled.")
    
    input("\nPress Enter to return to the main menu...")

def deploy_pending_changes():
    """Deploy pending changes to AWS."""
    print_header()
    print("Deploy Pending Changes")
    print("-" * 80)
    print("This will apply any pending changes to your AWS resources.")
    print()
    
    try:
        # Change to user_stack directory
        user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
        original_dir = os.getcwd()
        os.chdir(user_stack_path)
        
        # First show a preview
        print("📋 Previewing changes...\n")
        preview_result = subprocess.run(["pulumi", "preview"], capture_output=True, text=True)
        
        if preview_result.returncode != 0:
            print("❌ Preview failed:")
            print(preview_result.stderr)
            os.chdir(original_dir)
            input("\nPress Enter to return to the main menu...")
            return
        
        # Show preview output
        print(preview_result.stdout)
        
        # Check if there are any changes
        if "no changes" in preview_result.stdout.lower():
            print("\n✅ No changes to deploy. Everything is up to date!")
        else:
            if get_yes_no_input("\n🚀 Do you want to apply these changes?", "yes"):
                print("\n📤 Deploying changes...")
                print("This may take a few moments...\n")
                
                deploy_result = subprocess.run(["pulumi", "up", "--yes"])
                
                if deploy_result.returncode == 0:
                    print("\n✅ Deployment completed successfully!")
                else:
                    print("\n❌ Deployment failed. Check the error messages above.")
            else:
                print("\nDeployment cancelled.")
        
        os.chdir(original_dir)
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed during deployment: {str(e)}")
        try:
            os.chdir(original_dir)
        except:
            pass
    
    input("\nPress Enter to return to the main menu...")

def fix_user_access_keys():
    """Fix issues with user access keys by cleaning up excess keys."""
    print_header()
    print("Fix User Access Key Issues")
    print("-" * 80)
    print("AWS allows a maximum of 2 access keys per user.")
    print("This tool helps you manage and clean up excess access keys.")
    print()
    
    try:
        # Check AWS credentials
        valid_creds, session = check_aws_credentials()
        if not valid_creds:
            print("❌ Cannot proceed without valid AWS credentials.")
            input("\nPress Enter to return to the main menu...")
            return
        
        iam_client = session.client('iam')
        
        # Get users from Pulumi config
        user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
        result = subprocess.run(
            ["pulumi", "config", "get", "users", "--cwd", user_stack_path],
            capture_output=True, text=True
        )
        
        try:
            current_users = json.loads(result.stdout.strip() or "{}")
        except Exception:
            print("❌ Error: Unable to get current users from Pulumi config")
            current_users = {}
        
        if not current_users:
            print("No users found in Pulumi configuration.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Check each user's access keys
        print("🔍 Checking access keys for all users...\n")
        users_with_issues = []
        
        for username in current_users.keys():
            try:
                response = iam_client.list_access_keys(UserName=username)
                keys = response.get('AccessKeyMetadata', [])
                if len(keys) >= 2:
                    users_with_issues.append({
                        'username': username,
                        'keys': keys,
                        'count': len(keys)
                    })
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    print(f"⚠️  Error checking {username}: {e}")
            except Exception as e:
                print(f"⚠️  Unexpected error for {username}: {e}")
        
        if not users_with_issues:
            print("✅ No users have access key issues!")
            print("All users have less than 2 access keys.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Display users with issues
        print(f"Found {len(users_with_issues)} user(s) with 2 or more access keys:\n")
        for idx, user_info in enumerate(users_with_issues, 1):
            print(f"{idx}. {user_info['username']} - {user_info['count']} keys")
        
        # Let user select which user to fix
        user_idx = get_numeric_input(
            f"\nSelect user to manage (1-{len(users_with_issues)}) or 0 to exit",
            0, len(users_with_issues)
        )
        
        if user_idx is None or user_idx == 0:
            return
        
        selected_user_info = users_with_issues[user_idx - 1]
        username = selected_user_info['username']
        keys = selected_user_info['keys']
        
        print(f"\n📋 Access keys for user '{username}':")
        print("-" * 60)
        for idx, key in enumerate(keys, 1):
            key_id = key.get('AccessKeyId')
            status = key.get('Status')
            created = key.get('CreateDate').strftime('%Y-%m-%d %H:%M') if key.get('CreateDate') else 'Unknown'
            print(f"{idx}. Key ID: {key_id}")
            print(f"   Status: {status} | Created: {created}")
        
        # Select key to delete
        print(f"\n⚠️  User has {len(keys)} access keys (limit is 2)")
        key_idx = get_numeric_input(
            f"Select key to delete (1-{len(keys)}) or 0 to cancel",
            0, len(keys)
        )
        
        if key_idx is None or key_idx == 0:
            print("Operation cancelled.")
            input("\nPress Enter to return to the main menu...")
            return
        
        key_to_delete = keys[key_idx - 1]['AccessKeyId']
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: You are about to delete access key: {key_to_delete}")
        print("This action cannot be undone!")
        
        if get_yes_no_input("Are you sure you want to delete this key?", "no"):
            try:
                iam_client.delete_access_key(
                    UserName=username,
                    AccessKeyId=key_to_delete
                )
                print(f"\n✅ Successfully deleted access key {key_to_delete}")
                print(f"User '{username}' now has {len(keys) - 1} access key(s).")
                
                # Offer to create a new key if needed
                if len(keys) - 1 < 1 and current_users[username].get('create_key', 'no') == 'yes':
                    if get_yes_no_input(f"\nUser '{username}' needs an access key. Create one now?", "yes"):
                        print("Please use the 'Edit Existing User' option to regenerate access keys.")
                
            except Exception as e:
                print(f"❌ Error deleting access key: {e}")
        else:
            print("Deletion cancelled.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    input("\nPress Enter to return to the main menu...")

def verify_credential_access():
    """Verify password before allowing credential access."""
    print("\n🔐 Security Verification Required")
    print("-" * 40)
    print("Please enter the security password to view credentials.")
    
    for attempt in range(MAX_PASSWORD_ATTEMPTS):
        try:
            # Use getpass to hide password input
            password = getpass.getpass(f"Password (attempt {attempt + 1}/{MAX_PASSWORD_ATTEMPTS}): ")
            
            if password == CREDENTIAL_VIEW_PASSWORD:
                print("✅ Access granted.\n")
                return True
            else:
                remaining = MAX_PASSWORD_ATTEMPTS - attempt - 1
                if remaining > 0:
                    print(f"❌ Incorrect password. {remaining} attempt(s) remaining.")
                else:
                    print("❌ Maximum attempts exceeded. Access denied.")
                    
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            return False
        except Exception as e:
            print(f"❌ Error reading password: {e}")
            return False
    
    print("\n🚫 Returning to main menu for security...")
    time.sleep(2)  # Brief pause before returning
    return False

def show_user_credentials(username=None):
    """Show credentials for a specific user or all users with password protection."""
    print_header()
    
    # Security check
    if not verify_credential_access():
        return  # Return to main menu if password verification fails
    
    try:
        user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
        original_dir = os.getcwd()
        os.chdir(user_stack_path)
        
        if username:
            # Validate username if provided
            valid, error_msg = validate_username(username)
            if not valid:
                print(f"❌ Invalid username: {error_msg}")
                os.chdir(original_dir)
                input("\nPress Enter to return to the main menu...")
                return
            
            print(f"Showing Credentials for User: {username}")
            print("-" * 80)
            
            # Get specific outputs
            outputs = {}
            
            # Try to get the password
            pwd_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_generatedPassword", "--show-secrets"],
                capture_output=True, text=True
            )
            if pwd_result.returncode == 0 and pwd_result.stdout.strip():
                outputs['password'] = pwd_result.stdout.strip()
            
            # Try to get the access key
            key_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_accessKeyId"],
                capture_output=True, text=True
            )
            if key_result.returncode == 0 and key_result.stdout.strip():
                outputs['access_key_id'] = key_result.stdout.strip()
            
            # Try to get the secret key
            secret_result = subprocess.run(
                ["pulumi", "stack", "output", f"{username}_secretAccessKey", "--show-secrets"],
                capture_output=True, text=True
            )
            if secret_result.returncode == 0 and secret_result.stdout.strip():
                outputs['secret_key'] = secret_result.stdout.strip()
            
            # Display results
            print(f"\n📋 Credentials for '{username}':")
            print("-" * 40)
            
            if 'password' in outputs:
                print(f"🔑 Console Password: {outputs['password']}")
            else:
                print("🔑 Console Password: Not set or not available")
            
            if 'access_key_id' in outputs:
                print(f"🔑 Access Key ID: {outputs['access_key_id']}")
                if 'secret_key' in outputs:
                    print(f"🔐 Secret Access Key: {outputs['secret_key']}")
                else:
                    print("🔐 Secret Access Key: Not available")
            else:
                print("🔑 Access Key: Not set or not available")
            
            # Check user config for additional info
            config_result = subprocess.run(
                ["pulumi", "config", "get", "users"],
                capture_output=True, text=True
            )
            if config_result.returncode == 0:
                try:
                    users_config = json.loads(config_result.stdout.strip())
                    if username in users_config:
                        user_info = users_config[username]
                        print(f"\n📊 User Configuration:")
                        print(f"   Groups: {', '.join(user_info.get('groups', [])) or 'None'}")
                        print(f"   Path: {user_info.get('path', '/')}")
                        print(f"   Console Access: {user_info.get('has_console_access', 'no')}")
                        print(f"   Access Key Config: {user_info.get('create_key', 'no')}")
                except:
                    pass
            
        else:
            # Show all outputs
            print("Showing All User Credentials")
            print("-" * 80)
            print("\n⚠️  Displaying all credentials. Please ensure this is secure.\n")
            
            result = subprocess.run(["pulumi", "stack", "output", "--show-secrets"])
            
            if result.returncode != 0:
                print("❌ Error retrieving credentials.")
        
        os.chdir(original_dir)
        
        print("\n📝 SECURITY NOTES:")
        print("   • Store these credentials securely")
        print("   • Never share credentials via email or chat")
        print("   • Rotate credentials regularly")
        print("   • Delete this terminal output when done")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to show credentials: {str(e)}")
        try:
            os.chdir(original_dir)
        except:
            pass
    
    input("\nPress Enter to return to the main menu...")

def import_groups():
    """Import IAM groups from AWS - integrated from import_groups.py."""
    print_header()
    print("Import IAM Groups from AWS")
    print("-" * 80)
    print("This will import all existing IAM groups and their policies from AWS")
    print("into Pulumi configuration for management.")
    print("-" * 80)
    
    try:
        # Check AWS credentials
        valid_creds, session = check_aws_credentials()
        if not valid_creds:
            # Try to set up AWS profile
            print("\n🔧 AWS credentials not found. Let's set them up.")
            profile = setup_aws_profile()
            if profile:
                valid_creds, session = check_aws_credentials(profile)
                if not valid_creds:
                    print("❌ Failed to validate AWS credentials after setup")
                    input("\nPress Enter to return to the main menu...")
                    return
            else:
                input("\nPress Enter to return to the main menu...")
                return
        
        # Confirm before proceeding
        if not get_yes_no_input("\n🚀 Proceed with importing all IAM groups?", "no"):
            print("Import cancelled.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Initialize IAM client
        iam_client = session.client('iam')
        
        print("\nDiscovering IAM groups...")
        groups_data = {}
        total_groups = 0
        
        # Use paginator to handle accounts with many groups
        paginator = iam_client.get_paginator('list_groups')
        
        for page in paginator.paginate():
            for group in page['Groups']:
                group_name = group['GroupName']
                group_path = group['Path']
                total_groups += 1
                
                print(f"Processing group: {group_name} (Path: {group_path})")
                
                # Initialize group data structure
                groups_data[group_name] = {
                    "path": group_path,
                    "arn": group['Arn'],
                    "created_date": group['CreateDate'].isoformat(),
                    "managed_policy_arns": [],
                    "customer_managed_policies": [],
                    "inline_policies": {}
                }
                
                # Get attached managed policies
                try:
                    attached_policies = iam_client.list_attached_group_policies(GroupName=group_name)
                    for policy in attached_policies['AttachedPolicies']:
                        policy_arn = policy['PolicyArn']
                        
                        # Distinguish between AWS managed and customer managed policies
                        if policy_arn.startswith('arn:aws:iam::aws:policy/'):
                            groups_data[group_name]['managed_policy_arns'].append(policy_arn)
                            print(f"  • AWS Managed Policy: {policy['PolicyName']}")
                        else:
                            groups_data[group_name]['customer_managed_policies'].append({
                                'policy_name': policy['PolicyName'],
                                'policy_arn': policy_arn
                            })
                            print(f"  • Customer Managed Policy: {policy['PolicyName']}")
                            
                except ClientError as e:
                    print(f"  ⚠️  Warning: Could not fetch managed policies for {group_name}: {e}")
                
                # Get inline policies
                try:
                    inline_policies = iam_client.list_group_policies(GroupName=group_name)
                    for policy_name in inline_policies['PolicyNames']:
                        # Get the actual policy document
                        policy_response = iam_client.get_group_policy(
                            GroupName=group_name,
                            PolicyName=policy_name
                        )
                        groups_data[group_name]['inline_policies'][policy_name] = policy_response['PolicyDocument']
                        print(f"  • Inline Policy: {policy_name}")
                        
                except ClientError as e:
                    print(f"  ⚠️  Warning: Could not fetch inline policies for {group_name}: {e}")
        
        print(f"\n✅ Successfully processed {total_groups} IAM groups.")
        
        if total_groups == 0:
            print("\n⚠️  No groups found in AWS account.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Display summary
        print("\n" + "=" * 80)
        print("                        IMPORT SUMMARY")
        print("=" * 80)
        
        for group_name, group_info in groups_data.items():
            print(f"\n📁 Group: {group_name}")
            print(f"   Path: {group_info['path']}")
            
            # Count policies
            aws_managed_count = len(group_info['managed_policy_arns'])
            customer_managed_count = len(group_info['customer_managed_policies'])
            inline_count = len(group_info['inline_policies'])
            
            print(f"   Policies: {aws_managed_count} AWS managed, {customer_managed_count} customer managed, {inline_count} inline")
        
        # Confirm save
        print(f"\n💾 Ready to save {len(groups_data)} groups to Pulumi configuration.")
        if not get_yes_no_input("Save to Pulumi config?", "yes"):
            print("Save cancelled. Groups not saved to configuration.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Save to Pulumi config
        print("\n💾 Saving groups to Pulumi configuration...")
        
        # Check if we need to change to groups_stack directory
        original_dir = os.getcwd()
        groups_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_GROUPS_STACK_DIR) if PROJECT_ROOT else DEFAULT_GROUPS_STACK_DIR
        
        if not os.path.exists(os.path.join(groups_stack_path, 'Pulumi.yaml')):
            print(f"❌ ERROR: Pulumi.yaml not found in {groups_stack_path}")
            print("Please ensure the groups_stack is properly initialized.")
            input("\nPress Enter to return to the main menu...")
            return
        
        try:
            # Change to groups_stack directory
            os.chdir(groups_stack_path)
            
            # Convert to JSON string for Pulumi config
            groups_json = json.dumps(groups_data, indent=2, default=str)
            
            # Save to Pulumi config
            result = subprocess.run(
                ["pulumi", "config", "set", "imported_groups", groups_json],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ ERROR: Failed to save to Pulumi config: {result.stderr}")
                return
            
            print("✅ Groups successfully saved to Pulumi configuration.")
            print(f"  Configuration key: 'imported_groups'")
            print(f"  Total groups stored: {len(groups_data)}")
            
            # Ask if they want to deploy the groups now
            if get_yes_no_input("\n🚀 Deploy the imported groups now?", "yes"):
                print("\nDeploying groups...")
                deploy_result = subprocess.run(["pulumi", "up", "--yes"])
                if deploy_result.returncode == 0:
                    print("\n✅ Groups deployed successfully!")
                else:
                    print("\n❌ Deployment failed. Check the error messages above.")
            
        finally:
            # Always return to original directory
            os.chdir(original_dir)
        
        print("\n✅ Import completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Import cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error during import: {e}")
    
    input("\nPress Enter to return to the main menu...")

def run_script(script_name, script_description):
    """Run a specific user management script with error handling."""
    print_header()
    print(f"Running: {script_description}")
    print("-" * 80)
    
    user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
    script_path = os.path.join(user_stack_path, script_name)
    original_dir = os.getcwd()
    
    try:
        # Check if the script exists
        if not os.path.exists(script_path):
            print(f"❌ ERROR: Script '{script_path}' not found.")
            print("Make sure you have all the required scripts in the user_stack directory.")
            input("\nPress Enter to return to the main menu...")
            return
        
        # Change to user_stack directory to run the script
        os.chdir(user_stack_path)
        
        # Run the script and capture its exit code
        print(f"Executing {script_name}...\n")
        exit_code = subprocess.call([sys.executable, script_name])
        
        # Change back to the original directory
        os.chdir(original_dir)
        
        if exit_code != 0:
            print(f"\n⚠️  WARNING: The script exited with code {exit_code}")
            print("There might have been an error during execution.")
        else:
            print("\n✅ Script completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to run {script_name}: {str(e)}")
    finally:
        # Always try to return to original directory
        try:
            os.chdir(original_dir)
        except:
            pass
    
    input("\nPress Enter to return to the main menu...")

def check_environment():
    """Comprehensive environment check."""
    print("Checking environment setup...")
    print("-" * 80)
    
    all_good = True
    
    # Check directory structure first
    print("1. Checking directory structure...")
    if not find_project_root():
        return False
    
    user_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_USER_STACK_DIR) if PROJECT_ROOT else DEFAULT_USER_STACK_DIR
    groups_stack_path = os.path.join(PROJECT_ROOT, DEFAULT_GROUPS_STACK_DIR) if PROJECT_ROOT else DEFAULT_GROUPS_STACK_DIR
    
    if os.path.exists(user_stack_path) and os.path.exists(groups_stack_path):
        print("   ✅ Required directories found")
    else:
        all_good = False
        print("   ❌ Missing required directories")
        if not os.path.exists(user_stack_path):
            print(f"      - Missing: {user_stack_path}")
        if not os.path.exists(groups_stack_path):
            print(f"      - Missing: {groups_stack_path}")
    
    # Check AWS credentials
    print("\n2. Checking AWS credentials...")
    valid_creds, _ = check_aws_credentials()
    if not valid_creds:
        # Try to help set up AWS
        if get_yes_no_input("   Would you like to set up AWS credentials now?", "yes"):
            profile = setup_aws_profile()
            if profile:
                valid_creds, _ = check_aws_credentials(profile)
        
        if not valid_creds:
            all_good = False
            print("   ❌ AWS credentials need to be configured")
    
    # Check Pulumi
    print("\n3. Checking Pulumi installation...")
    if not check_pulumi_configuration():
        all_good = False
        print("   ❌ Pulumi needs to be configured")
    
    # Check Pulumi stacks
    print("\n4. Checking Pulumi stacks...")
    try:
        original_dir = os.getcwd()
        
        # Check user stack
        os.chdir(user_stack_path)
        result = subprocess.run(["pulumi", "stack", "--show-name"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print(f"   ✅ User stack active: {result.stdout.strip()}")
        else:
            all_good = False
            print("   ❌ No active user stack")
            if get_yes_no_input("      Initialize user stack now?", "yes"):
                stack_name = input("      Enter stack name: ").strip()
                if stack_name:
                    subprocess.run(["pulumi", "stack", "init", stack_name])
        
        # Check groups stack
        os.chdir(original_dir)
        os.chdir(groups_stack_path)
        result = subprocess.run(["pulumi", "stack", "--show-name"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print(f"   ✅ Groups stack active: {result.stdout.strip()}")
        else:
            all_good = False
            print("   ❌ No active groups stack")
            if get_yes_no_input("      Initialize groups stack now?", "yes"):
                stack_name = input("      Enter stack name: ").strip()
                if stack_name:
                    subprocess.run(["pulumi", "stack", "init", stack_name])
        
        os.chdir(original_dir)
        
    except Exception as e:
        all_good = False
        print(f"   ❌ Error checking stacks: {e}")
    
    print("\n" + "-" * 80)
    if all_good:
        print("✅ Environment check passed! Ready to proceed.")
    else:
        print("❌ Environment issues detected. Please fix the issues above.")
    
    return all_good

def main():
    """Main function."""
    # Initial environment check
    print_header()
    env_ok = check_environment()
    
    if not env_ok:
        if not get_yes_no_input("\nContinue anyway?", "no"):
            print("\nExiting. Please fix environment issues and try again.")
            sys.exit(1)
    
    input("\nPress Enter to continue...")
    
    while True:
        print_header()
        print("MAIN MENU")
        print("-" * 80)
        print("User Management:")
        print("  1. Create New User")
        print("  2. Edit Existing User")
        print("  3. Delete User")
        print("  4. Import Existing AWS User")
        print("  5. Sync All AWS Users")
        print("  6. Show User Credentials 🔐")
        print("  7. Fix User Access Key Issues")
        print("\nGroup Management:")
        print("  8. Import Groups from AWS")
        print("  9. View Available Groups")
        print("\nSystem Operations:")
        print("  10. Refresh Pulumi State")
        print("  11. Deploy Pending Changes")
        print("  12. Verify/Setup AWS Credentials")
        print("  13. Re-run Environment Check")
        print("\n  0. Exit")
        print("-" * 80)
        
        choice = get_numeric_input("Enter your choice", 0, 13)
        
        if choice is None:
            continue
        
        if choice == 1:
            run_script("create_user.py", "Create New User")
        elif choice == 2:
            run_script("edit_user.py", "Edit Existing User")
        elif choice == 3:
            run_script("delete_user.py", "Delete User")
        elif choice == 4:
            run_script("import_user.py", "Import Existing AWS User")
        elif choice == 5:
            run_script("sync_users.py", "Sync All AWS Users")
        elif choice == 6:
            # Password-protected credential viewing
            print_header()
            print("Show User Credentials 🔐")
            print("-" * 80)
            specific_user = input("Enter username (or leave blank for all): ").strip()
            if specific_user:
                show_user_credentials(specific_user)
            else:
                show_user_credentials()
        elif choice == 7:
            fix_user_access_keys()
        elif choice == 8:
            import_groups()
        elif choice == 9:
            view_groups()
        elif choice == 10:
            refresh_pulumi_state()
        elif choice == 11:
            deploy_pending_changes()
        elif choice == 12:
            print_header()
            print("AWS Credentials Setup")
            print("-" * 80)
            profile = setup_aws_profile()
            if profile:
                print(f"\n✅ AWS profile '{profile}' is now active")
            input("\nPress Enter to continue...")
        elif choice == 13:
            print_header()
            check_environment()
            input("\nPress Enter to continue...")
        elif choice == 0:
            print("\n👋 Exiting User Management Helper. Goodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: An unexpected error occurred: {str(e)}")
        sys.exit(1)