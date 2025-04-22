# AWS IAM User and Group Management with Pulumi

This project provides a comprehensive solution for managing AWS IAM users and groups using Pulumi infrastructure-as-code.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Group Management](#group-management)
5. [User Management](#user-management)
6. [Working with AWS Profiles](#working-with-aws-profiles)
7. [Common Operations](#common-operations)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.6 or later
- AWS CLI installed and configured
- AWS account with IAM permissions to create users and groups
- Pulumi CLI installed

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Set up Python virtual environments for both stacks

For the groups stack:
```bash
cd groups_stack
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

For the user stack:
```bash
cd ../user_stack
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

### Setting up AWS credentials

1. Create an AWS profile for Pulumi to use:

```bash
aws configure --profile pulumi-dev
```

Enter your AWS Access Key ID, Secret Access Key, region (e.g., us-east-1), and output format (json).

2. Export the AWS profile for Pulumi to use:

```bash
export AWS_PROFILE=pulumi-dev
```

On Windows:
```cmd
set AWS_PROFILE=pulumi-dev
```

### Initializing Pulumi stacks

1. Initialize the groups stack:

```bash
cd ../groups_stack
pulumi stack init Rajas  # Or any stack name you prefer
pulumi config set aws:region us-east-1  # Set your preferred region
```

2. Initialize the user stack:

```bash
cd ../user_stack
pulumi stack init Rajas  # Use the same stack name
pulumi config set aws:region us-east-1  # Set your preferred region
```

## Group Management

The groups stack creates IAM groups with specific permissions for different roles.

### Deploying Groups

```bash
cd ../groups_stack
export AWS_PROFILE=pulumi-dev  # Ensure the AWS profile is set
pulumi up
```

Review the changes and select "yes" to apply them.

### Customizing Groups

To modify group permissions, edit the `app_roles_policies` and `aws_roles_policies` dictionaries in `groups_stack/__main__.py`.

Example:
```python
# Add a new role
app_roles_policies["NewRole"] = [
    "ViewProfile",
    "EditProfile",
    "CustomPermission"
]

aws_roles_policies["NewRole"] = [
    "iam:ChangePassword", 
    "iam:GetAccountPasswordPolicy"
]
```

After making changes, run `pulumi up` to apply them.

## User Management

The user stack manages IAM users and their group memberships.

### Creating a User

```bash
cd ../user_stack
export AWS_PROFILE=pulumi-dev  # Ensure the AWS profile is set
python create_user.py
```

Follow the prompts to:
1. Enter the IAM username
2. Specify groups to assign (comma-separated)
3. Choose whether to create an access key
4. Enable/disable console access
5. Deploy changes immediately

### Editing a User

```bash
cd ../user_stack
export AWS_PROFILE=pulumi-dev
python edit_user.py
```

Follow the prompts to:
1. Select a user from the list
2. Add or remove groups
3. Deploy changes immediately

### Deleting a User

```bash
cd ../user_stack
export AWS_PROFILE=pulumi-dev
python delete_user.py
```

Enter the username to delete and confirm.

### Importing Existing Users

To import users that already exist in AWS:

```bash
cd ../user_stack
export AWS_PROFILE=pulumi-dev
python import_user.py
```

### Synchronizing All AWS Users

To sync all AWS IAM users to Pulumi:

```bash
cd ../user_stack
export AWS_PROFILE=pulumi-dev
python sync_users.py
```

## Working with AWS Profiles

You can manage multiple AWS accounts by using different AWS profiles.

### Creating Additional Profiles

```bash
aws configure --profile profile-name
```

### Using Different Profiles

```bash
export AWS_PROFILE=profile-name
```

Then run any of the Pulumi or Python commands as normal.

### Using Profiles for Specific Commands

```bash
AWS_PROFILE=profile-name pulumi up
```

Or for Python scripts:

```bash
AWS_PROFILE=profile-name python create_user.py
```

### Checking Active Profile

```bash
echo $AWS_PROFILE  # Linux/Mac
echo %AWS_PROFILE%  # Windows
```

### Profile Configuration in Scripts

The `edit_user.py` and `import_user.py` scripts use the boto3 session with a profile name:

```python
session = boto3.Session(profile_name='pulumi-dev')
```

To use a different profile, modify these lines or update your environment.

## Common Operations

### View Stack Outputs

To view information about created users, including access keys and passwords:

```bash
cd ../user_stack
pulumi stack output --show-secrets
```

### Refresh Stack State

To sync the Pulumi state with the actual AWS resources:

```bash
cd ../user_stack
pulumi refresh
```

### View all IAM Users in AWS

```bash
aws iam list-users --profile pulumi-dev
```

### View Group Membership for a User

```bash
aws iam list-groups-for-user --user-name USERNAME --profile pulumi-dev
```

## Troubleshooting

### Permission Denied Errors

If you encounter permission issues:

1. Verify your AWS credentials are correct:
   ```bash
   aws sts get-caller-identity --profile pulumi-dev
   ```

2. Ensure your IAM user has the necessary permissions to create and manage IAM resources.

### Login Profile Already Exists

If you see an error about login profiles already existing:

1. Check if the user already has console access:
   ```bash
   aws iam get-login-profile --user-name USERNAME --profile pulumi-dev
   ```

2. Either delete the login profile through AWS console or skip creating a new one.

### Path Conflicts

If you have users with the same name but different paths:

1. Use the full resource name including the path:
   ```bash
   aws iam get-user --user-name USERNAME --profile pulumi-dev
   ```

2. Make sure the path in your Pulumi configuration matches the path in AWS.

## Project Structure

```
.
├── groups_stack/            # IAM Groups management
│   ├── __main__.py          # Main Pulumi program for groups
│   ├── Pulumi.yaml          # Pulumi project file
│   └── requirements.txt     # Python dependencies
└── user_stack/              # IAM Users management
    ├── __main__.py          # Main Pulumi program for users
    ├── create_user.py       # Script to create new users
    ├── delete_user.py       # Script to delete users
    ├── edit_user.py         # Script to edit existing users
    ├── import_user.py       # Script to import AWS users
    ├── sync_users.py        # Script to sync all AWS users
    ├── Pulumi.yaml          # Pulumi project file
    └── requirements.txt     # Python dependencies
```

## License

[MIT](LICENSE)