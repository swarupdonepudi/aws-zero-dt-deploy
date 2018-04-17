import sys
import boto3
import os
import time
from config import ApplicationConfig

elb_client = None
ec2_client = None
ec2_resource_client = None


def sample_function():
    return "Hello World!!"


def setup_clients(aws_region):
    os.environ["AWS_DEFAULT_REGION"] = aws_region
    global elb_client
    global ec2_resource_client
    global ec2_client

    elb_client= boto3.client(
        'elb'
    )
    ec2_client= boto3.client(
        'ec2'
    )
    ec2_resource_client= boto3.resource(
        'ec2'
    )


def get_instances_in_elb(elb_name):
    instance_ids = []
    response = elb_client.describe_instance_health(
        LoadBalancerName=elb_name
    )
    for instance in response["InstanceStates"]:
        if instance["State"] == "InService":
            instance_ids.append(instance["InstanceId"])
    return instance_ids


def get_instance_details(instance_id):
    print("Getting details of instance : " + instance_id)
    instance_details = {}
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance_details["availability_zone"] = response["Reservations"][0]["Instances"][0]["Placement"]["AvailabilityZone"]
    instance_details["instance_type"] = response["Reservations"][0]["Instances"][0]["InstanceType"]
    instance_details["subnet_id"] = response["Reservations"][0]["Instances"][0]["SubnetId"]
    security_group_ids = []
    for security_group in response["Reservations"][0]["Instances"][0]["SecurityGroups"]:
        security_group_ids.append(security_group['GroupId'])
    instance_details["security_group_ids"] = security_group_ids
    instance_details["instance_state"] = response["Reservations"][0]["Instances"][0]["State"]["Name"]
    return instance_details


def launch_instance(instance_details):
    print("Launching instance with " + str(instance_details))
    user_data_script = "sudo docker run -p 80:80 --name exr-app -d nginx"
    response = ec2_resource_client.create_instances(
        ImageId=instance_details["ami_id"],
        InstanceType=instance_details["instance_type"],
        KeyName="bbutter_shared_key",
        UserData=user_data_script,
        Placement={
            'AvailabilityZone':instance_details["availability_zone"]
        },
        SecurityGroupIds=instance_details["security_group_ids"],
        SubnetId=instance_details["subnet_id"],
        MinCount=1,
        MaxCount=1)
    return response[0].id


def is_instance_running(instance_details):
    return get_instance_details(instance_details["instance_id"])["instance_state"] == "running"


def wait_for_replacement_instances_to_be_ready(replacement_mappings):
    running_instances = 0
    instance_running_waiter = ec2_client.get_waiter('instance_running')
    while running_instances != len(replacement_mappings):
        for replacement_mapping in replacement_mappings:
            print(str(running_instances) + " new instances are in Running status... Waiting for "
                  + (str(len(replacement_mappings) - running_instances))
                  + " more instances to be in Running status...")
            print("Waiting for " + replacement_mapping["replacement_instance_details"]["instance_id"]
                  + " instance to be in running state...")
            instance_running_waiter.wait(
                InstanceIds=[
                    replacement_mapping["replacement_instance_details"]["instance_id"],
                ],
                WaiterConfig={
                    'Delay': ApplicationConfig.WAITERS_DELAY_SECONDS,
                    'MaxAttempts': ApplicationConfig.WAITERS_MAX_ATTEMPTS
                }
            )
            print(replacement_mapping["replacement_instance_details"]["instance_id"]
                  + " instance is in running state...")
            running_instances = running_instances + 1


def start_deploy(elb_name, old_ami_id, new_ami_id, aws_region):
    setup_clients(aws_region)
    replacement_mappings = []
    print("Getting current instances fronted by ELB : " + elb_name)
    instance_ids = get_instances_in_elb(elb_name)
    if len(instance_ids) > 0:
        for instance_id in instance_ids:
            replacement_mapping = {}
            replacement_instance_details = get_instance_details(instance_id)
            replacement_instance_details["ami_id"] = new_ami_id
            replacement_mapping["old_instance_id"] = instance_id
            replacement_mapping["replacement_instance_details"] = replacement_instance_details
            replacement_mappings.append(replacement_mapping)

        for replacement_mapping in replacement_mappings:
            instance_id = launch_instance(replacement_mapping["replacement_instance_details"])
            replacement_mapping["replacement_instance_details"]["instance_id"] = instance_id

        wait_for_replacement_instances_to_be_ready(replacement_mappings)

        for replacement_mapping in replacement_mappings:
            print("Registering new instance " + replacement_mapping["replacement_instance_details"]["instance_id"]
                  + " with " + elb_name + " load balancer..." )
            elb_client.register_instances_with_load_balancer(
                LoadBalancerName=elb_name,
                Instances=[
                    {
                        'InstanceId': replacement_mapping["replacement_instance_details"]["instance_id"]
                    }
                ]
            )

            print("Waiting for " + replacement_mapping["replacement_instance_details"]["instance_id"]
                  + " to be in InService status")

            instance_in_service_waiter = elb_client.get_waiter('instance_in_service')

            instance_in_service_waiter.wait(
                LoadBalancerName=elb_name,
                Instances=[
                    {
                        'InstanceId': replacement_mapping["replacement_instance_details"]["instance_id"]
                    },
                ],
                WaiterConfig={
                    'Delay': ApplicationConfig.WAITERS_DELAY_SECONDS,
                    'MaxAttempts': ApplicationConfig.WAITERS_MAX_ATTEMPTS
                }
            )
            print("Instance " + replacement_mapping["replacement_instance_details"]["instance_id"]
                  + " is in InService status...")

            print("De-registering old instance " + replacement_mapping["old_instance_id"]
                  + " from " + elb_name + " load balancer...")

            elb_client.deregister_instances_from_load_balancer(
                LoadBalancerName=elb_name,
                Instances=[
                    {
                        'InstanceId': replacement_mapping["old_instance_id"]
                    },
                ]
            )

            # Could use some exception handling or waiting logic here...

            print("De-registered instance" + replacement_mapping["old_instance_id"]
                  + " from elb...Now Terminating the instance...")
            ec2_client.terminate_instances(
                InstanceIds=[
                    replacement_mapping["old_instance_id"]
                ]
            )
        print("Ohooooo!!! Successfully replaced all the old instances running " + old_ami_id
              + " with new instances running " + new_ami_id)
    else:
        print("There are no instances registered with ELB " + elb_name)
        print("Exiting now...")


if __name__ == "__main__":
    required_number_of_args=4
    if len(sys.argv)-1 == required_number_of_args:
        old_ami_id = sys.argv[1]
        new_ami_id = sys.argv[2]
        elb_name = sys.argv[3]
        aws_region = sys.argv[4]
        start_deploy(elb_name, old_ami_id, new_ami_id, aws_region)
    else:
        print("\nInvalid number of arguments passed. Required # of arguments : " + str(required_number_of_args) + "\nList of arguments:\n \
                    1) Old AMI ID\n \
                    2) New AMI ID\n \
                    3) ELB Name\n \
                    4) AWS Region")
