import json
import pulumi
import pulumi_aws as aws
from pulumi import Config, Output

config = Config()
# Get the JSON object from config; default to empty dict if not set.
users_config = config.get("users") or "{}"
users_dict = json.loads(users_config)  # Expected format: { username: { groups: [...], create_key: "yes"/"no", has_console_access: "yes"/"no", path: "/path/" } }

# Track any existing users with login profiles to prevent creation errors
login_profile_check = {}

# Let's first check which users already exist before creating resources
try:
    # This is a safer approach that doesn't rely on dynamic resources
    for username in users_dict.keys():
        # Just declare the try/except here - we'll handle failures gracefully at runtime
        try:
            # Get user data
            existing_user = aws.iam.get_user(user_name=username)
            # Check if login profile exists by attempting to get login profile
            # We can't directly check this in Pulumi, so we'll use a workaround
            login_profile_check[username] = True
        except Exception:
            # If user doesn't exist, we'll create it normally
            login_profile_check[username] = False
except Exception:
    # If anything fails, continue with normal resource creation
    pass

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
            "Groups": " ".join(groups) if groups else "None"
        },
    )

    if groups:
        # Directly use the group names without looking them up
        aws.iam.UserGroupMembership(
        f"userGroupMembership-{username}",
        user=user.name,
        groups=[g for g in groups],  # This should be the group name without path
        opts=pulumi.ResourceOptions(depends_on=[user])  # Ensure user exists first
    )

    if create_key_flag == "yes":
        access_key = aws.iam.AccessKey(f"accessKey-{username}", user=user.name)
        pulumi.export(f"{username}_accessKeyId", access_key.id)
        pulumi.export(f"{username}_secretAccessKey", access_key.secret)
    
    # Create login profile if console access is enabled and we haven't detected
    # that a login profile already exists
    if has_console_access == "yes" and not login_profile_check.get(username, False):
        # If we're here, either the user doesn't exist yet or doesn't have a login profile
        login_profile = aws.iam.UserLoginProfile(
            f"login-{username}",
            user=user.name,
            password_length=16,  # Generate a 16-character password
            password_reset_required=True,
            # Use ignore_changes to prevent update conflicts
            opts=pulumi.ResourceOptions(ignore_changes=["password"]),
        )
        
        # Use apply for properly handling the Output
        def export_password(pwd):
            return pwd
        
        password_output = login_profile.password.apply(export_password)
        pulumi.export(f"{username}_generatedPassword", password_output)
    elif has_console_access == "yes":
        # For users with existing login profiles
        pulumi.export(f"{username}_generatedPassword", 
                     Output.from_input("User already has a login profile - password not available"))