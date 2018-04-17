#AWS Rolling Deployer

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
docker run rolling-deployer <old-ami-id> <new-ami-id> <elb-name> <aws-region>
```