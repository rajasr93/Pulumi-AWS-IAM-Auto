import json
import pulumi
import pulumi_aws as aws

# 1) Define the role-to-actions mapping from your table
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
    ]
}

# 2) Create a group and inline policy for each role
for role_name, actions in roles_policies.items():
    # Create the IAM group
    group = aws.iam.Group(role_name,
        name=role_name,
        path="/system/"
        # If your Pulumi AWS provider supports it, you can add tags:
        # tags={"Name": role_name}
    )

    # Build the inline policy document for this role
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": actions,
            "Resource": "*"
        }]
    }

    # Attach the inline policy to the group
    group_policy = aws.iam.GroupPolicy(
        f"{role_name}-policy",
        group=group.name,
        policy=json.dumps(policy_doc)
    )

# 3) Example: Create a test user and assign them to a group
#    (Remove or adapt this if you don’t want a test user)
test_user = aws.iam.User(
    "testUser",
    name="testUser",
    path="/system/",
    tags={"Name": "testUser"},
)

# Assign the user to one of the groups (e.g., "Beneficiary")
membership = aws.iam.UserGroupMembership(
    "testUserMembership",
    user=test_user.name,
    groups=["Beneficiary"],
)
