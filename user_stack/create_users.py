import subprocess

def main():
    username = input("Enter the new IAM username: ").strip()
    groups = input("Enter comma-separated groups to assign (e.g., Beneficiary,Volunteer): ").strip()
    create_key = input("Create an access key? (yes/no): ").strip().lower()

    # Set Pulumi config for the 'users_stack'
    subprocess.run(["pulumi", "config", "set", "username", username])
    subprocess.run(["pulumi", "config", "set", "groups", groups])
    subprocess.run(["pulumi", "config", "set", "createKey", create_key])

    # Now run pulumi up
    subprocess.run(["pulumi", "up"])

if __name__ == "__main__":
    main()
