import json
import pulumi
import pulumi_aws as aws

# Map each role (group) to the custom actions it should allow.
roles_policies = {
    "Beneficiary": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:SubmitRequest"
    ],
    "Volunteer": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:AcceptRequest"
    ],
    "Steward": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:AcceptRequest",
        "application:ManageRoles"
    ],
    "Admin": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:AcceptRequest",
        "application:DeleteRequest"
    ],
    "SuperAdmin": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:AcceptRequest",
        "application:DeleteRequest",
        "application:ManageRoles",
        "application:ManageAdmin",
        "application:ManageIntegrations",
        "application:ManageDashboard",
        "application:MatchRequests",
        "application:ViewReports",
        "application:ManageUsers"
    ],
    "CharityOrg": [
        "application:ViewProfile",
        "application:EditProfile",
        "application:ManageRoles"
    ],
}

# Create an IAM Group and attach an inline policy for each role
for role_name, actions in roles_policies.items():
    # Create the IAM group
    group = aws.iam.Group(
        role_name,             # Pulumi resource name
        name=role_name,        # Actual IAM group name in AWS
        path="/system/",
        # tags={"Name": role_name},  # If supported by your Pulumi AWS provider
    )

    # Build the inline policy document
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": actions,
            "Resource": "*"
        }]
    }

    # Attach the inline policy to the group
    aws.iam.GroupPolicy(
        f"{role_name}-policy",
        group=group.name,
        policy=json.dumps(policy_doc),
    )
