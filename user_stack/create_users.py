import json
import subprocess

def main():
    # Retrieve the current 'users' config as a JSON object (dictionary).
    result = subprocess.run(["pulumi", "config", "get", "users"], capture_output=True, text=True)
    try:
        current_users = json.loads(result.stdout.strip() or "{}")
    except Exception:
        current_users = {}

    new_username = input("Enter the new IAM username: ").strip()

    # Check if this username already exists
    if new_username in current_users:
        print(f"User '{new_username}' already exists in the configuration. Skipping creation.")
        return

    groups_input = input("Enter comma-separated groups to assign (e.g., Beneficiary,Volunteer): ").strip()
    groups_list = [g.strip() for g in groups_input.split(",") if g.strip()]
    create_key = input("Create an access key? (yes/no): ").strip().lower()
    has_console_access = input("Enable console access? (yes/no): ").strip().lower()
    
    # Use AWS Console default behavior (root path) for new users
    user_path = "/"
    
    # Add the new user object to the dictionary.
    current_users[new_username] = {
        "groups": groups_list,
        "create_key": create_key,
        "has_console_access": has_console_access,
        "path": user_path
    }

    updated_users = json.dumps(current_users)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    
    print(f"User '{new_username}' added to configuration with path '{user_path}' and groups: {groups_list}")
    if has_console_access.lower() == "yes":
        print(f"A random password will be generated and password change will be required on first login")
        print(f"The generated password will be available in the Pulumi outputs after deployment")
    
    deploy = input("Deploy changes now? (yes/no): ").strip().lower()
    if deploy == "yes":
        subprocess.run(["pulumi", "up", "--yes"])
        
        if has_console_access.lower() == "yes":
            print("\nTo get the generated password, run:")
            print(f"pulumi stack output {new_username}_generatedPassword")

if __name__ == "__main__":
    main()