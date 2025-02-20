import pulumi
import pulumi_aws as aws
from pulumi import Config, Output

# Read configuration values
config = Config()
username = config.require("username")          # e.g., "Rajas"
groups_input = config.get("groups") or ""       # e.g., "Volunteer"
create_key = config.get("createKey") or "no"      # "yes" or "no"

# Create the IAM user
user = aws.iam.User(
    "dynamicUser",
    name=username,
    path="/system/",
    tags={"Name": username},
)

# Split the comma-separated group names
group_list = [g.strip() for g in groups_input.split(",") if g.strip()]

if group_list:
    # For each group name, get the group as an Output and extract group_name
    group_names_outputs = [
        aws.iam.get_group_output(group_name=g).apply(lambda r: r.group_name)
        for g in group_list
    ]
    
    # Combine all outputs into one Output that is a list of group names
    combined_group_names = Output.all(*group_names_outputs)
    
    # Create the user-group membership using the combined list
    aws.iam.UserGroupMembership(
        "userGroupMembership",
        user=user.name,
        groups=combined_group_names,
    )

# Optionally create an access key if requested
if create_key.lower() == "yes":
    user_access_key = aws.iam.AccessKey("dynamicUserAccessKey", user=user.name)
    pulumi.export("accessKeyId", user_access_key.id)
    pulumi.export("secretAccessKey", user_access_key.secret)
