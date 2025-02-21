import yaml
import json
import os
import subprocess

def delete_user_from_yaml(file_path):
    # Check if the YAML file exists.
    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        return

    # Load the YAML file.
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)

    # Navigate to the configuration section.
    config = data.get("config", {})

    # Get the "Create_users:users" value (expected to be a JSON string).
    users_str = config.get("Create_users:users", "{}")

    # Convert the JSON string to a dictionary.
    try:
        users_dict = json.loads(users_str)
    except json.JSONDecodeError:
        print("Error: 'Create_users:users' is not valid JSON.")
        return

    # Prompt the operator for the username to delete.
    username_to_delete = input("Enter the username to delete: ").strip()

    # Check if the username exists in the dictionary.
    if username_to_delete in users_dict:
        del users_dict[username_to_delete]
        print(f"User '{username_to_delete}' has been deleted from the configuration.")
    else:
        print(f"User '{username_to_delete}' not found in the configuration.")

    # Update the users value in the YAML data.
    config["Create_users:users"] = json.dumps(users_dict)
    data["config"] = config

    # Write the updated YAML back to the file.
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    
    # Run "pulumi up --yes" automatically to apply changes.
    print("Running 'pulumi up --yes' to deploy changes...")
    subprocess.run(["pulumi", "up", "--yes"])

if __name__ == "__main__":
    yaml_file = "Pulumi.Rajas.yaml"  # Adjust this path if needed.
    delete_user_from_yaml(yaml_file)
