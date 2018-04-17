# AWS Rolling Deployer

Purpose: This python tool will do a rolling deploy of a new version of an app running behind an ELB on AWS

#### Assumptions:

* Your application is completely packaged using packer
* Application launch is already built into AMI as part of packer build
* Your application is completely stateless/ You have session-stickiness enabled on your elb
* You have AWS Access credentials with required privileges
* AWS Credentials are either stored in ~/.aws/credentials file of are declared as environment variables
* Your application is not running inside an Auto Scaling Group

#### Inputs

1. Old AMI ID(Not really used)
2. New AMI ID
3. ELB Name
4. AWS Region

#### How to use:

##### Build

```
docker build -r rolling-deployer .
```

##### Run

```
docker run -v ~/.aws/credentials:/root/.aws/credentials rolling-deployer <old-ami-id> <new-ami-id> <elb-name> <aws-region>
```

#### Deployment Flow Steps:

1. Get list of InService instances registered with ELB
2. Create a 1:1 mapping of running instances by reading the attributes of old instances to ensure that we are replacing the machine in the same AZ.
3. Replace the value of AMI ID of the replacement instance with ** new ami-id **
4. Launch replacement instances
5. Wait until all new replacement instances are in ** running ** state
6. Register one instance with ELB and wait until that instance is in ** "InService" ** status
7. Deregister the corresponding old instance
8. Terminate the deregistered instance
9. Repeat Steps 6, 7 & 8 until all the old instances are replaced by new instances
10. Brew some good coffee and listen to your favorite band


** Demo: **

[![asciicast](https://asciinema.org/a/040ziS6w5VcHuBYcGXUU6K5HB.png)](https://asciinema.org/a/040ziS6w5VcHuBYcGXUU6K5HB)
