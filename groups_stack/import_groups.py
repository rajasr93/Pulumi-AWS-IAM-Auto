import json
import subprocess
import boto3
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError

def print_header():
    """Print script header."""
    print("=" * 80)
    print("                    AWS IAM GROUPS IMPORT TOOL")
    print("=" * 80)
    print("This tool imports all existing IAM groups and their policies")
    print("from AWS into Pulumi configuration for dynamic management.")
    print("=" * 80)
    print()

def check_aws_credentials():
    """Verify AWS credentials are working."""
    try:
        aws_profile = os.environ.get('AWS_PROFILE', 'default')
        print(f"Using AWS Profile: {aws_profile}")
        
        session = boto3.Session(profile_name=aws_profile)
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        
        print(f"AWS Account ID: {identity['Account']}")
        print(f"IAM User/Role: {identity['Arn']}")
        print("✅ AWS credentials verified successfully.\n")
        return session
        
    except NoCredentialsError:
        print("  ERROR: No AWS credentials found.")
        print("Please configure AWS credentials using 'aws configure' or set AWS_PROFILE.")
        return None
    except ClientError as e:
        print(f"  ERROR: AWS credentials validation failed: {e}")
        return None
    except Exception as e:
        print(f"  ERROR: Unexpected error verifying AWS credentials: {e}")
        return None

def fetch_all_groups(iam_client):
    """Fetch all IAM groups with their policies."""
    print("Discovering IAM groups...")
    
    groups_data = {}
    total_groups = 0
    
    try:
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
                            print(f"AWS Managed Policy: {policy['PolicyName']}")
                        else:
                            groups_data[group_name]['customer_managed_policies'].append({
                                'policy_name': policy['PolicyName'],
                                'policy_arn': policy_arn
                            })
                            print(f"Customer Managed Policy: {policy['PolicyName']}")
                            
                except ClientError as e:
                    print(f"Warning: Could not fetch managed policies for {group_name}: {e}")
                
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
                        print(f"Inline Policy: {policy_name}")
                        
                except ClientError as e:
                    print(f"Warning: Could not fetch inline policies for {group_name}: {e}")
        
        print(f"\n Successfully processed {total_groups} IAM groups.")
        return groups_data
        
    except ClientError as e:
        print(f" ERROR: Failed to fetch IAM groups: {e}")
        return None
    except Exception as e:
        print(f" ERROR: Unexpected error fetching groups: {e}")
        return None

def save_to_pulumi_config(groups_data):
    """Save imported groups to Pulumi configuration."""
    print("\n Saving groups to Pulumi configuration...")
    
    try:
        # Check if we're in the groups_stack directory
        if not os.path.exists('Pulumi.yaml'):
            print("  ERROR: Pulumi.yaml not found. Please run this script from the groups_stack directory.")
            return False
        
        # Convert to JSON string for Pulumi config
        groups_json = json.dumps(groups_data, indent=2, default=str)
        
        # Save to Pulumi config
        result = subprocess.run(
            ["pulumi", "config", "set", "imported_groups", groups_json],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ERROR: Failed to save to Pulumi config: {result.stderr}")
            return False
        
        print(" Groups successfully saved to Pulumi configuration.")
        print(f"  Configuration key: 'imported_groups'")
        print(f"  Total groups stored: {len(groups_data)}")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Failed to save to Pulumi config: {e}")
        return False

def display_import_summary(groups_data):
    """Display a summary of imported groups."""
    print("\n" + "=" * 80)
    print("                        IMPORT SUMMARY")
    print("=" * 80)
    
    if not groups_data:
        print("No groups were imported.")
        return
    
    for group_name, group_info in groups_data.items():
        print(f"\n Group: {group_name}")
        print(f"   Path: {group_info['path']}")
        print(f"   ARN: {group_info['arn']}")
        
        # Count policies
        aws_managed_count = len(group_info['managed_policy_arns'])
        customer_managed_count = len(group_info['customer_managed_policies'])
        inline_count = len(group_info['inline_policies'])
        
        print(f"   Policies: {aws_managed_count} AWS managed, {customer_managed_count} customer managed, {inline_count} inline")
        
        # Show first few policies as examples
        if group_info['managed_policy_arns']:
            print("   AWS Managed Policies:")
            for arn in group_info['managed_policy_arns'][:3]:  # Show first 3
                policy_name = arn.split('/')[-1]
                print(f"     • {policy_name}")
            if len(group_info['managed_policy_arns']) > 3:
                print(f"     ... and {len(group_info['managed_policy_arns']) - 3} more")
        
        if group_info['customer_managed_policies']:
            print("   Customer Managed Policies:")
            for policy in group_info['customer_managed_policies'][:3]:  # Show first 3
                print(f"     • {policy['policy_name']}")
            if len(group_info['customer_managed_policies']) > 3:
                print(f"     ... and {len(group_info['customer_managed_policies']) - 3} more")
        
        if group_info['inline_policies']:
            print("   Inline Policies:")
            for policy_name in list(group_info['inline_policies'].keys())[:3]:  # Show first 3
                print(f"     • {policy_name}")
            if len(group_info['inline_policies']) > 3:
                print(f"     ... and {len(group_info['inline_policies']) - 3} more")

def main():
    """Main function."""
    print_header()
    
    # Check AWS credentials
    session = check_aws_credentials()
    if not session:
        sys.exit(1)
    
    # Initialize IAM client
    iam_client = session.client('iam')
    
    # Confirm before proceeding
    proceed = input("🚀 Proceed with importing all IAM groups? (yes/no): ").strip().lower()
    if proceed != 'yes':
        print("Import cancelled by user.")
        sys.exit(0)
    
    # Fetch all groups
    groups_data = fetch_all_groups(iam_client)
    if not groups_data:
        print("  Failed to fetch groups. Exiting.")
        sys.exit(1)
    
    # Display summary
    display_import_summary(groups_data)
    
    # Confirm save
    print(f"\n Ready to save {len(groups_data)} groups to Pulumi configuration.")
    save_confirm = input(" Save to Pulumi config? (yes/no): ").strip().lower()
    if save_confirm != 'yes':
        print("Save cancelled. Groups not saved to configuration.")
        sys.exit(0)
    
    # Save to Pulumi config
    if save_to_pulumi_config(groups_data):
        print("\n Import completed successfully!")
        print("\nNext steps:")
        print("1. Review the imported groups in your Pulumi configuration")
        print("2. Run 'pulumi up' in the groups_stack to deploy the imported groups")
        print("3. Update your user creation scripts to use the new imported groups")
        print("\nNote: The groups_stack/__main__.py will need to be updated to use imported_groups config.")
    else:
        print("  Import failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Import cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Unexpected error: {e}")
        sys.exit(1)