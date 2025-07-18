# AWS IAM User and Group Management Automation

This project automates the process of managing AWS IAM users and groups using Pulumi. It includes tools to import existing IAM groups from AWS, save them to a Pulumi configuration file, and then use that configuration to manage user creation dynamically.

## Prerequisites

1. **AWS CLI**: Ensure you have the AWS Command Line Interface (CLI) installed and configured on your machine.
2. **Pulumi**: Install the Pulumi CLI if you haven't already: [Pulumi Installation Guide](https://www.pulumi.com/docs/get-started/install/)
3. **Python 3.x**: The project requires Python 3.x to run.

## Setup

1. **AWS Profile Configuration**:
   Configure your AWS profile for use with the Pulumi automation tool. You can do this by running the following command in your terminal:

   ```sh
   aws configure --profile <profile-name>
   AccessKeyId: [your_access_key_id]
   SecretAccessKey: [your_secret_access_key]
   Region: us-east-1
   Output Format: json

   ```

2. **Clone the Repository**:
   Clone this repository to your local machine.

   ```sh
   git clone https://github.com/rajasr93/Pulumi-AWS-IAM-Auto.git
   cd aws-iam-automation
   ```

3. **Create and Activate a Virtual Environment** (optional but recommended):
   It's a good practice to use a virtual environment for Python projects. You can create and activate one using the following commands:

   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

4. **Install Dependencies**:
   Install the necessary Python dependencies using `pip`.

   ```sh
   pip install -r ./user_stack/requirements.txt
   ```

## Running the Automation

1. **Manage Users with Imported Groups**:
   You can manage users with the imported groups by running the `manage_users.py` script directly. This script includes all the subprograms needed for automation.

   ```sh
   AWS_PROFILE=<profile-name> python3 user_stack/manage_users.py
   ```

## Additional Notes

- Ensure you are running all commands from the root directory of your repository.
- Modify the `AWS_PROFILE` environment variable as needed to match your AWS profile configuration.
- The project assumes that you have the necessary IAM permissions to list groups and perform other operations in AWS.

For more detailed information, please refer to the [Pulumi Documentation](https://www.pulumi.com/docs/) and the [AWS IAM User Guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html).

Copyright 2025 Rajas Ronghe

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
