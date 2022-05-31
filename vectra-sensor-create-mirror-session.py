#!/usr/bin/env python
"""
AWS Lambda to create Traffic Mirroring sessions for all newly deployed EC2 instances. 
This lambda MUST be triggered by using the appropriate EC2 creation CloudTrail event. 
It's possible to trigger such a creation event for all existing EC2 instances to ensure Traffic Mirroring sessions
are created for all existing instances on the first deployment of this lambda.
Refer to the REAMDE for more informations. 
"""

import json
import boto3
import os
import logging


__author__ = "Aurélien Hess"
__copyright__ = "Copyright 2020, Vectra AI"
__credits__ = []
__license__ = "Apache 2.0"
__version__ = "1.0.1"
__maintainer__ = "Aurélien Hess"
__email__ = "ahess@vectra.ai"
__status__ = "Production"


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# get environment variables
traffic_mirror_target_id = os.environ.get('TRAFFIC_MIRROR_TARGET_ID')
traffic_mirror_filter_id = os.environ.get('TRAFFIC_MIRROR_FILTER_ID')
vectra_sensor_tag_key = os.environ.get('VECTRA_SENSOR_TAG_KEY')
vectra_sensor_tag_value = os.environ.get('VECTRA_SENSOR_TAG_VALUE')


def lambda_handler(event, context):

    event_json = json.dumps(event, indent=2)
    # get state of ec2 instance
    state = event['detail']['state']

    # terminated: When you delete a network interface that is a traffic mirror source,
    #             the traffic mirror sessions that are associated with the source are
    #             automatically deleted.
    # Source: https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-considerations.html
    if state == 'shutting-down' or state == 'stopped' or state == 'stopping' or state == 'terminated':
        logger.info('Ignore EC2 state change event: ' + state)
        return True

    # get ec2 instance details
    ec2 = boto3.client('ec2')
    instance_id = event['detail']['instance-id']
    ec2_described = ec2.describe_instances(InstanceIds=[instance_id])
    network_interface_list = ec2_described['Reservations'][0]['Instances'][0]['NetworkInterfaces']

    # check if instance is vectra sensor, we do not want to mirror sensor traffic
    if 'Tags' in ec2_described['Reservations'][0]['Instances'][0]:
        for tag in ec2_described['Reservations'][0]['Instances'][0]['Tags']:
            if vectra_sensor_tag_key in tag['Key'] and vectra_sensor_tag_value in tag['Value']:
                logger.info('This is a Vectra Sensor (' + instance_id + ') and doesn\'t need a Traffic Mirror Session')
                return #exit function

    logger.info("Processing a total of {} ENIs".format(str(len(network_interface_list))))
    # get all mirror sessions
    traffic_mirror_sessions = ec2.describe_traffic_mirror_sessions()['TrafficMirrorSessions']
    for network_interface in network_interface_list:
        already_tapped = False
        network_interface_id = network_interface['NetworkInterfaceId']
        logger.info('Processing ENI ID {}'.format(network_interface_id))
         # check state of ec2 instance and create mirror session if needed
        if state == 'running':
            logger.info('EC2 instance is running: Create Traffic Mirror Session')
            for traffic_mirror_session in traffic_mirror_sessions:
                if traffic_mirror_session['NetworkInterfaceId'] == network_interface_id:
                    logger.info('EC2 has already a Traffic Mirror Session: ' + traffic_mirror_session['TrafficMirrorSessionId'])
                    already_tapped = True
                    break
            if not already_tapped:
                # create mirror session for ec2 instance
                print('Create new Traffic Mirror Session for EC2 instance ID: ' + instance_id)
                create_traffic_mirror_session_response = ec2.create_traffic_mirror_session(
                    NetworkInterfaceId = network_interface_id,
                    TrafficMirrorTargetId = traffic_mirror_target_id,
                    TrafficMirrorFilterId = traffic_mirror_filter_id,
                    SessionNumber = 1,
                    Description = 'Vectra Sensor Mirror Session',
                    DryRun = False,
                    TagSpecifications = [
                        {
                            'ResourceType': 'traffic-mirror-session',
                            'Tags': [
                                {
                                    'Key': 'Name',
                                    'Value': 'Vectra Traffic Mirror Session: ' + instance_id
                                }
                            ]
                        }  
                        ]
                    )
                print(create_traffic_mirror_session_response)
        else:
            logger.info('EC2 instance is not running: skipping..')