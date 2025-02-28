import json
import pulumi
import pulumi_aws as aws

# Map each role (group) to the custom application actions it should allow
app_roles_policies = {
    "Beneficiary": [
        "ViewProfile",
        "EditProfile",
        "SubmitRequest"
    ],
    "Volunteer": [
        "ViewProfile",
        "EditProfile",
        "AcceptRequest"
    ],
    "Steward": [
        "ViewProfile",
        "EditProfile",
        "AcceptRequest",
        "ManageRoles"
    ],
    "Admin": [
        "ViewProfile",
        "EditProfile",
        "AcceptRequest",
        "DeleteRequest"
    ],
    "SuperAdmin": [
        "ViewProfile",
        "EditProfile",
        "AcceptRequest",
        "DeleteRequest",
        "ManageRoles",
        "ManageAdmin",
        "ManageIntegrations",
        "ManageDashboard",
        "MatchRequests",
        "ViewReports",
        "ManageUsers"
    ],
    "CharityOrg": [
        "ViewProfile",
        "EditProfile",
        "ManageRoles"
    ],
}

# Map each role to standard AWS IAM permissions
aws_roles_policies = {
    "Beneficiary": [],
    "Volunteer": ["iam:ChangePassword", "iam:GetAccountPasswordPolicy"],
    "Steward": ["iam:ChangePassword", "iam:GetAccountPasswordPolicy"],
    "Admin": ["iam:ChangePassword", "iam:GetAccountPasswordPolicy"],
    "SuperAdmin": ["iam:ChangePassword", "iam:GetAccountPasswordPolicy"],
    "CharityOrg": ["iam:ChangePassword", "iam:GetAccountPasswordPolicy"],
}

# Create an IAM Group and attach policies for each role
for role_name, app_actions in app_roles_policies.items():
    # Create the IAM group
    group = aws.iam.Group(
        role_name,             # Pulumi resource name
        name=role_name,        # Actual IAM group name in AWS
        path="/system/",
    )

    # Get AWS IAM permissions for this role
    aws_actions = aws_roles_policies.get(role_name, [])
    
    # Build the app permissions policy document (tag-based)
    app_policy_doc = {
        "Version": "2012-10-17",
        "Statement": []
    }
    
    # Only add app permissions if there are any
    if app_actions:
        app_policy_doc["Statement"].append({
            "Effect": "Allow",
            "Action": ["application:TagBasedAccess"],  # Use a standard AWS action as placeholder
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "application:actions": app_actions  # Store app permissions as a condition
                }
            }
        })
    
    # Add AWS IAM permissions
    if aws_actions:
        app_policy_doc["Statement"].append({
            "Effect": "Allow",
            "Action": aws_actions,
            "Resource": "*"
        })
    
    # Attach the policy to the group
    aws.iam.GroupPolicy(
        f"{role_name}-policy",
        group=group.name,
        policy=json.dumps(app_policy_doc),
    )