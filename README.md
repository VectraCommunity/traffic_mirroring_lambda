# Introduction

This CloudFormation template and linked resources will provision all required AWS resources to automatically enable traffic mirroring on all EC2 instances in a given account. 

The main component is a lambda function which has an EventBridge listener for Instance State Event change events (triggered each time an EC2 instance's state changes). The goal is to automatically enable/configure traffic mirroring for any ENI of those newly created EC2 instances. 

For terminated instances, the traffic mirroring sessions are automatically destroyed by AWS, so the lifecycle handling is automatically provided by AWS. 

The CloudFormation template will also take care of creating a "passthrough" traffic mirroring filter, as a filter is required for any AWS traffic mirroring session, but we want to see all traffic.

The traffic mirroring target will typically be created separately when deploying the Vectra sensor(s), and might be in a different account, shared through AWS RAM. 

# Deploying the CloudFormation

The CloudFormation template has four parameters that need to be defined upon deployment: 
- TrafficMirroringTargetID: ID of the traffic mirroring target to use for the newly created sessions (tmt-xxxx). 
- ExcludedTagKey: Key name of the tag used to identify EC2 instances to exclude (typically Vectra sensors whose traffic we don't want to see). 
- ExcludedTagValue: Value of the tag used to identify EC2 instances to exclude (typically Vectra sensors whose traffic we don't want to see). 
- ExcludeEKS: Boolean value to automatically exclude any EC2 instance that are part of an EKS cluster from traffic mirroring. 

By default, based on the configured key/value pair for Vectra sensor tags, Vectra sensors are excluded from traffic mirroring as there is no value in monitoring the traffic from the sensors themselves (and this would create a loop). This can also be used to exclude other machines, since the tag does not need to be exclusive to Vectra sensors. 

# Resources created

This will create the following resources: 

1. An execution role based on the service-role "AWSLambdaBasicExecutionRole"
2. An additional Inline Policy for this role to allow for creation of Traffic Mirrorign sessions. 
3. An Event Rule which will be used to invoke the lambda based on EC2 Instance State Change events. 
4. Appropriate permissions to allow the lambda to be run by the Event Rule
5. A Traffic Mirroring Filter that will automatically be linked to any newm traffic mirroring session created by the lambda. 
6. Egress and Ingress Traffic Mirroring Filter Rules, allowing for any kind of traffic. 
7. The actual lambda function which takes care of listing all ENIs of newly started EC2 instances and enabling traffic mirroring on all those. 

# First execution

When newly deploying Vectra in an AWS environemnt, there will most probably already be instances present, and customers will most probably not want to power cycle them all to trigger appropriate CLoudTrail events. 

We can trigger such events manually for all EC2 instances present in the VPC using the AWS shell: 

```bash
export instance_ids=$(aws ec2 describe-instances | jq '.Reservations[].Instances[].InstanceId' -r)
while IFS= read -r line; do aws lambda invoke --function-name <lambda_function_name> --cli-binary-format raw-in-base64-out --payload "{\"detail\":{\"state\":\"running\",\"instance-id\": \"$line\"}}" response.json; done <<< "$instance_ids";
```

