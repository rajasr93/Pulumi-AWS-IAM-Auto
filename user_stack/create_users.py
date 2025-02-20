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

    # Add the new user object to the dictionary.
    current_users[new_username] = {
        "groups": groups_list,
        "create_key": create_key
    }

    updated_users = json.dumps(current_users)
    subprocess.run(["pulumi", "config", "set", "users", updated_users])
    subprocess.run(["pulumi", "up", "--yes"])

if __name__ == "__main__":
    main()
