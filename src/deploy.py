import json
import sys
from config import ApplicationConfig

def sample_function():
    return "Hello World!!"

if __name__ == "__main__":
    required_number_of_args=2
    if len(sys.argv)-1 == required_number_of_args:
        old_ami_id = sys.argv[1]
        new_ami_id = sys.argv[2]
        print("\n**** Replacing instances fronted by ELB : " + ApplicationConfig.ELB_ID + " running AMI : " + old_ami_id + " with new instances running AMI : " + new_ami_id + " ****")
    else:
        print("\nInvalid number of arguments passed. Required # of arguments : " + str(required_number_of_args) + "\nList of arguments:\n \
                    1) Old AMI ID\n \
                    2) New AMI ID")
