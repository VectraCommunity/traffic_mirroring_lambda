# Introduction

This is meant to be deployed as an AWS lambda function. This lambda listens to CLoudTrail event for Instance State Event change events (triggered each time an EC2 instance's state changes). The goal is to automatically enable/configure traffic mirroring for any new EC2 instances being created in the VPC. 

For terminated instances, the traffic mirroring sessions are automatically destroyed by AWS.

# Setup

This script uses four environment variables, which need to be added to the lambda function: 
- TRAFFIC_MIRROR_TARGET_ID: ARN of the traffic mirroring target to use for hte newly created sessions
- TRAFFIC_MIRROR_FILTER_ID: ARN of the traffic mirroring filter to use, this should be a passthrough filter (any->any) 
- VECTRA_SENSOR_TAG_KEY: Key name of the tag used to identify Vectra sensors
- VECTRA_SENSOR_TAG_VALUE Value of the tag used to identify Vectra sensors

By default, based on the configured key/value pair for Vectra sensor tags, Vectra sensors are excluded from traffic mirroring as there is no value in monitoring the traffic from the sensors themselves (and this would create a loop). This can also be used to exclude other machines, since the tag does not need to be exclusive to Vectra sensors. 


# First execution

When newly deploying a Vectra sensor in a VPC, there will most probably already be instances present, and customers will most probably not want to power cycle them all to trigger appropriate CLoudTrail events. 

We can trigger such events manually for all EC2 instances present in the VPC using the AWS shell: 

```bash
export instance_ids=$(aws ec2 describe-instances | jq '.Reservations[].Instances[].InstanceId' -r)
while IFS= read -r line; do aws lambda invoke --function-name vectra-sensor-create-mirror-session --cli-binary-format raw-in-base64-out --payload "{\"detail\":{\"state\":\"running\",\"instance-id\": \"$line\"}}" response.json; done <<< "$instance_ids";
```

