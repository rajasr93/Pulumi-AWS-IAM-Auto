import json
import pulumi
import pulumi_aws as aws
from pulumi import Config, Output

config = Config()
# Get the JSON object from config; default to empty dict if not set.
users_config = config.get("users") or "{}"
users_dict = json.loads(users_config)  # Expected format: { username: { groups: [...], create_key: "yes"/"no", has_console_access: "yes"/"no", path: "/path/" } }

for username, user_obj in users_dict.items():
    # If the stored value isn't already a dict, assume no groups and no access key.
    if not isinstance(user_obj, dict):
        user_obj = {"groups": [], "create_key": "no", "has_console_access": "no"}
    
    groups = user_obj.get("groups", [])
    create_key_flag = user_obj.get("create_key", "no").lower()
    has_console_access = user_obj.get("has_console_access", "no").lower()
    
    # Use the user's original path if specified, otherwise use root path like AWS Console
    user_path = user_obj.get("path", "/")
    
    # Create the IAM user resource with a unique Pulumi name
    user = aws.iam.User(
        f"user-{username}",
        name=username,
        path=user_path,
        tags={
            "Name": username,
            "Path": user_path,
            "Created": "PulumiManaged",
            "Groups": ",".join(groups) if groups else "None"
        },
    )

    if groups:
        # For each group in the list, look up its group name
        group_names_outputs = [
            aws.iam.get_group_output(group_name=g).apply(lambda r: r.group_name)
            for g in groups
        ]
        combined_group_names = Output.all(*group_names_outputs)
        aws.iam.UserGroupMembership(
            f"userGroupMembership-{username}",
            user=user.name,
            groups=combined_group_names,
        )

    if create_key_flag == "yes":
        access_key = aws.iam.AccessKey(f"accessKey-{username}", user=user.name)
        pulumi.export(f"{username}_accessKeyId", access_key.id)
        pulumi.export(f"{username}_secretAccessKey", access_key.secret)
    
    # Create login profile if console access is enabled
    if has_console_access == "yes":
        # Instead of directly setting password, let AWS generate one
        login_profile = aws.iam.UserLoginProfile(
            f"login-{username}",
            user=user.name,
            password_length=16,  # Generate a 16-character password
            password_reset_required=True,
        )
        # The generated password will be exported
        pulumi.export(f"{username}_generatedPassword", login_profile.password)