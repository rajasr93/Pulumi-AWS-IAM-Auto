import json
import pulumi
import pulumi_aws as aws
from pulumi import Config, Output

config = Config()

# Get imported groups from config (JSON string)
imported_groups_config = config.get("imported_groups") or "{}"

try:
    imported_groups = json.loads(imported_groups_config)
except json.JSONDecodeError as e:
    pulumi.log.error(f"Failed to parse imported_groups config: {e}")
    pulumi.log.error("Please run 'python import_groups.py' from the groups_stack directory first.")
    imported_groups = {}

if not imported_groups:
    pulumi.log.warn("No imported groups found in configuration.")
    pulumi.log.warn("Run 'python import_groups.py' to import existing IAM groups.")
    pulumi.log.warn("Skipping group creation...")
else:
    pulumi.log.info(f"Found {len(imported_groups)} imported groups to manage.")

# Create IAM groups and attach policies for each imported group
for group_name, group_config in imported_groups.items():
    group_path = group_config.get("path", "/")
    
    pulumi.log.info(f"Creating group: {group_name} with path: {group_path}")
    
    # Create the IAM group
    group = aws.iam.Group(
        f"group-{group_name}",  # Pulumi resource name
        name=group_name,        # Actual IAM group name in AWS
        path=group_path,
        opts=pulumi.ResourceOptions(
            import_=group_name if group_name else None  # Import existing group
        )
    )
    
    # Attach AWS managed policies
    aws_managed_policies = group_config.get("managed_policy_arns", [])
    for idx, policy_arn in enumerate(aws_managed_policies):
        policy_name = policy_arn.split("/")[-1]  # Extract policy name from ARN
        
        aws.iam.GroupPolicyAttachment(
            f"group-{group_name}-aws-policy-{idx}",
            group=group.name,
            policy_arn=policy_arn,
            opts=pulumi.ResourceOptions(depends_on=[group])
        )
        
        pulumi.log.info(f"  Attached AWS managed policy: {policy_name}")
    
    # Attach customer managed policies
    customer_managed_policies = group_config.get("customer_managed_policies", [])
    for idx, policy_info in enumerate(customer_managed_policies):
        if isinstance(policy_info, dict):
            policy_arn = policy_info.get("policy_arn")
            policy_name = policy_info.get("policy_name", f"policy-{idx}")
        else:
            # Handle case where it might be just a string (for backward compatibility)
            policy_arn = policy_info
            policy_name = f"policy-{idx}"
        
        if policy_arn:
            aws.iam.GroupPolicyAttachment(
                f"group-{group_name}-customer-policy-{idx}",
                group=group.name,
                policy_arn=policy_arn,
                opts=pulumi.ResourceOptions(depends_on=[group])
            )
            
            pulumi.log.info(f"  Attached customer managed policy: {policy_name}")
    
    # Create and attach inline policies
    inline_policies = group_config.get("inline_policies", {})
    for policy_name, policy_document in inline_policies.items():
        aws.iam.GroupPolicy(
            f"group-{group_name}-inline-{policy_name}",
            group=group.name,
            name=policy_name,
            policy=json.dumps(policy_document) if isinstance(policy_document, dict) else policy_document,
            opts=pulumi.ResourceOptions(depends_on=[group])
        )
        
        pulumi.log.info(f"  Created inline policy: {policy_name}")
    
    # Export group information for reference
    pulumi.export(f"group_{group_name}_arn", group.arn)
    pulumi.export(f"group_{group_name}_path", group.path)
    
    # Export policy counts for monitoring
    total_policies = len(aws_managed_policies) + len(customer_managed_policies) + len(inline_policies)
    pulumi.export(f"group_{group_name}_policy_count", total_policies)

# Export summary information
pulumi.export("total_groups_managed", len(imported_groups))
pulumi.export("groups_list", list(imported_groups.keys()) if imported_groups else [])

# Provide helpful information in outputs
if imported_groups:
    pulumi.log.info("All imported groups have been processed successfully.")
    pulumi.log.info(f"Total groups managed: {len(imported_groups)}")
    pulumi.log.info("Groups available for user assignment:")
    for group_name in imported_groups.keys():
        pulumi.log.info(f"  • {group_name}")
else:
    pulumi.log.warn("No groups were processed.")
    pulumi.log.warn("To import groups:")
    pulumi.log.warn("1. Run 'python import_groups.py' from this directory")
    pulumi.log.warn("2. Then run 'pulumi up' to deploy the imported groups")