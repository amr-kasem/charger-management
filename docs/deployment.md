# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the OCPP Management System to your AWS account. The deployment uses AWS CDK (Cloud Development Kit) to provision all required resources.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Custom Domain Setup](#custom-domain-setup)
7. [Troubleshooting Deployment](#troubleshooting-deployment)
8. [Environment-Specific Deployments](#environment-specific-deployments)

## Prerequisites

### Required Software

Before starting, ensure you have the following software installed:

1. **AWS CLI** (v2.0+)
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Verify installation
   aws --version
   ```

2. **Node.js** (v16+)
   ```bash
   # Install Node.js (using NodeSource repository)
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   
   # Verify installation
   node --version
   npm --version
   ```

3. **TypeScript** (v4.0+)
   ```bash
   npm install -g typescript
   tsc --version
   ```

4. **AWS CDK CLI** (v2.0+)
   ```bash
   npm install -g aws-cdk
   cdk --version
   ```

5. **Docker** (for container builds)
   ```bash
   # Install Docker Engine
   sudo apt-get update
   sudo apt-get install -y docker.io
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   
   # Verify installation
   docker --version
   ```

6. **Python 3.8+** (for Lambda functions)
   ```bash
   python3 --version
   pip3 --version
   ```

### AWS Account Requirements

1. **AWS Account**: Active AWS account with billing enabled
2. **IAM Permissions**: Administrator access (or specific permissions listed below)
3. **Service Limits**: Ensure sufficient limits for ECS, Lambda, and IoT Core
4. **Regions**: Deploy in regions that support all required services

### Required IAM Permissions

If not using Administrator access, ensure your IAM user/role has these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:*",
        "ec2:*",
        "ecs:*",
        "lambda:*",
        "iot:*",
        "dynamodb:*",
        "sqs:*",
        "logs:*",
        "secretsmanager:*",
        "elasticloadbalancing:*",
        "route53:*",
        "acm:*",
        "ecr:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Initial Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/aws-samples/aws-ocpp-gateway.git
cd aws-ocpp-gateway
```

### 2. Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# Enter your credentials:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: [e.g., us-east-1]
# Default output format: json
```

### 3. Verify AWS Configuration

```bash
# Test AWS connectivity
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDACKCEVSQ6C2EXAMPLE",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

### 4. Install Project Dependencies

```bash
# Install NPM dependencies
npm install

# Verify installation
npm list --depth=0
```

## Configuration

### 1. Set Environment Variables

```bash
# Set your target AWS account and region
export CDK_DEPLOY_ACCOUNT=123456789012  # Your AWS Account ID
export CDK_DEPLOY_REGION=us-east-1      # Your preferred region

# Verify environment variables
echo "Account: $CDK_DEPLOY_ACCOUNT"
echo "Region: $CDK_DEPLOY_REGION"
```

### 2. Architecture Selection (Optional)

Edit `bin/aws-ocpp-gateway.ts` to choose CPU architecture:

```typescript
new AwsOcppGatewayStack(app, 'AwsOcppGatewayStack', {
  env: {
    account: process.env.CDK_DEPLOY_ACCOUNT,
    region: process.env.CDK_DEPLOY_REGION,
  },
  
  // Choose architecture: 'arm64' (default) or 'X86_64'
  architecture: 'arm64',  // ARM is cheaper and faster for most workloads
  // architecture: 'X86_64',  // Use if you have compatibility requirements
});
```

### 3. Custom Domain Configuration (Optional)

If you have a Route53 hosted zone, you can enable HTTPS:

```typescript
new AwsOcppGatewayStack(app, 'AwsOcppGatewayStack', {
  env: {
    account: process.env.CDK_DEPLOY_ACCOUNT,
    region: process.env.CDK_DEPLOY_REGION,
  },
  
  // Enable custom domain (replace with your domain)
  domainName: 'yourdomain.com',  // Uncomment and replace
});
```

## Deployment Process

### 1. Bootstrap CDK (First Time Only)

If this is your first CDK deployment in this account/region:

```bash
# Bootstrap CDK for your account/region
npx cdk bootstrap aws://$CDK_DEPLOY_ACCOUNT/$CDK_DEPLOY_REGION

# Expected output:
# ⏳  Bootstrapping environment aws://123456789012/us-east-1...
# ✅  Environment aws://123456789012/us-east-1 bootstrapped.
```

### 2. Verify Docker is Running

```bash
# Check Docker status
docker version

# If Docker is not running:
sudo systemctl start docker
```

### 3. Synthesize CloudFormation Template (Optional)

Preview the resources that will be created:

```bash
# Generate CloudFormation template
npx cdk synth

# This will output a large CloudFormation template
# Review it to understand what resources will be created
```

### 4. Deploy the Stack

```bash
# Deploy the OCPP Gateway stack
npx cdk deploy

# You'll see a confirmation prompt:
# Do you wish to deploy these changes (y/n)? y
```

**Expected Deployment Output:**
```
✨  Synthesis time: 5.2s

AwsOcppGatewayStack: deploying...
[█████████████████████████████████████████████████████] (34/34)

✅  AwsOcppGatewayStack

✨  Deployment time: 542.91s

Outputs:
AwsOcppGatewayStack.loadBalancerDnsName = ocpp-gateway-1234567890.elb.us-east-1.amazonaws.com
AwsOcppGatewayStack.websocketURL = ws://ocpp-gateway-1234567890.elb.us-east-1.amazonaws.com
AwsOcppGatewayStack.RemoteStartTransactionUrl = https://abc123.lambda-url.us-east-1.on.aws/
AwsOcppGatewayStack.RemoteStopTransactionUrl = https://def456.lambda-url.us-east-1.on.aws/

Stack ARN:
arn:aws:cloudformation:us-east-1:123456789012:stack/AwsOcppGatewayStack/12345678-1234-1234-1234-123456789012
```

### 5. Save Deployment Outputs

```bash
# Save outputs to environment variables for later use
export WEBSOCKET_URL=$(aws cloudformation describe-stacks \
  --stack-name AwsOcppGatewayStack \
  --query 'Stacks[0].Outputs[?OutputKey==`websocketURL`].OutputValue' \
  --output text)

export REMOTE_START_URL=$(aws cloudformation describe-stacks \
  --stack-name AwsOcppGatewayStack \
  --query 'Stacks[0].Outputs[?OutputKey==`RemoteStartTransactionUrl`].OutputValue' \
  --output text)

export REMOTE_STOP_URL=$(aws cloudformation describe-stacks \
  --stack-name AwsOcppGatewayStack \
  --query 'Stacks[0].Outputs[?OutputKey==`RemoteStopTransactionUrl`].OutputValue' \
  --output text)

# Verify outputs
echo "WebSocket URL: $WEBSOCKET_URL"
echo "Remote Start URL: $REMOTE_START_URL"
echo "Remote Stop URL: $REMOTE_STOP_URL"
```

## Post-Deployment Verification

### 1. Verify AWS Resources

#### Check ECS Service
```bash
# List ECS clusters
aws ecs list-clusters

# Describe the OCPP Gateway service
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service

# Check service is running
aws ecs list-tasks \
  --cluster AwsOcppGatewayStack-Cluster \
  --service-name AwsOcppGatewayStack-Service
```

#### Check Lambda Functions
```bash
# List Lambda functions
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `AwsOcppGatewayStack`)].FunctionName'

# Test message processor function
aws lambda invoke \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  test-output.json

cat test-output.json
```

#### Check DynamoDB Table
```bash
# Describe the charge point table
aws dynamodb describe-table \
  --table-name AwsOcppGatewayStack-ChargePointTable

# Check table status (should be ACTIVE)
aws dynamodb describe-table \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --query 'Table.TableStatus'
```

#### Check Load Balancer
```bash
# Describe load balancer
aws elbv2 describe-load-balancers \
  --names ocpp-gateway

# Check target group health
aws elbv2 describe-target-groups \
  --names AwsOcppGatewayStack-LoadBalancer
```

### 2. Test Basic Connectivity

#### Test WebSocket Gateway
```bash
# Install wscat if not already installed
npm install -g wscat

# Test WebSocket connection (should fail for unregistered CP)
timeout 5 wscat -c $WEBSOCKET_URL/TEST_CP -s ocpp2.0.1 || echo "Expected failure for unregistered CP"
```

#### Test REST APIs
```bash
# Test Remote Start API (should return 400 for unregistered CP)
curl -X POST $REMOTE_START_URL \
  -H "Content-Type: application/json" \
  -d '{"chargePointId": "TEST_CP", "idTag": "test-user"}'

# Test Remote Stop API (should return 400 for unregistered CP)
curl -X POST $REMOTE_STOP_URL \
  -H "Content-Type: application/json" \
  -d '{"chargePointId": "TEST_CP", "transactionId": 123}'
```

### 3. Create Test Charge Point

```bash
# Create a test charge point in IoT Core
aws iot create-thing --thing-name "CP_TEST_001"

# Verify creation
aws iot describe-thing --thing-name "CP_TEST_001"

# Check DynamoDB entry (may take a few seconds)
sleep 5
aws dynamodb get-item \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --key '{"chargePointId":{"S":"CP_TEST_001"}}'
```

### 4. Test Complete Flow

```bash
# Test WebSocket connection with registered CP
timeout 10 wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp2.0.1 &
sleep 2

# Send a test message (BootNotification)
echo '[2,"test123","BootNotification",{"chargingStation":{"model":"TestCP","vendorName":"TestVendor","firmwareVersion":"1.0","serialNumber":"TEST001"},"reason":"PowerUp"}]' | wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp2.0.1
```

## Custom Domain Setup

### Prerequisites

1. **Domain Registration**: Own a domain name
2. **Route53 Hosted Zone**: Domain managed in Route53
3. **Certificate Manager**: AWS Certificate Manager access

### Setup Process

#### 1. Verify Hosted Zone

```bash
# List your hosted zones
aws route53 list-hosted-zones-by-name

# Note the hosted zone ID for your domain
export DOMAIN_NAME="yourdomain.com"
export HOSTED_ZONE_ID="Z1234567890ABC"
```

#### 2. Update CDK Configuration

Edit `bin/aws-ocpp-gateway.ts`:

```typescript
new AwsOcppGatewayStack(app, 'AwsOcppGatewayStack', {
  env: {
    account: process.env.CDK_DEPLOY_ACCOUNT,
    region: process.env.CDK_DEPLOY_REGION,
  },
  
  // Enable custom domain
  domainName: 'yourdomain.com',
});
```

#### 3. Redeploy with Custom Domain

```bash
# Deploy with custom domain configuration
npx cdk deploy

# The deployment will:
# 1. Create ACM certificate
# 2. Create DNS validation records
# 3. Create gateway.yourdomain.com A record
# 4. Configure TLS listener on load balancer
```

#### 4. Verify TLS Setup

```bash
# Test HTTPS WebSocket connection
wscat -c wss://gateway.yourdomain.com/CP_TEST_001 -s ocpp2.0.1

# Verify certificate
echo | openssl s_client -connect gateway.yourdomain.com:443 -servername gateway.yourdomain.com 2>/dev/null | openssl x509 -noout -subject
```

## Troubleshooting Deployment

### Common Issues and Solutions

#### 1. CDK Bootstrap Required

**Error**: `Need to perform AWS CDK bootstrap`

**Solution**:
```bash
npx cdk bootstrap aws://$CDK_DEPLOY_ACCOUNT/$CDK_DEPLOY_REGION
```

#### 2. Docker Not Running

**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and log back in
```

#### 3. Insufficient IAM Permissions

**Error**: `User: arn:aws:iam::123456789012:user/username is not authorized`

**Solution**:
- Grant Administrator access, or
- Add specific permissions listed in [Prerequisites](#prerequisites)

#### 4. Region Not Supported

**Error**: Service not available in region

**Solution**:
```bash
# Use a supported region
export CDK_DEPLOY_REGION=us-east-1  # or us-west-2, eu-west-1, etc.
```

#### 5. Docker Image Platform Mismatch

**Error**: `The requested image's platform (linux/arm64/v8) does not match`

**Solution**:
Edit `bin/aws-ocpp-gateway.ts`:
```typescript
architecture: 'X86_64',  // Change from 'arm64'
```

#### 6. Stack Already Exists

**Error**: `Stack AwsOcppGatewayStack already exists`

**Solution**:
```bash
# Either destroy existing stack
npx cdk destroy

# Or use a different stack name
cdk deploy --stack-name AwsOcppGatewayStack-Dev
```

### Deployment Logs

#### View CloudFormation Events
```bash
# Monitor deployment progress
aws cloudformation describe-stack-events \
  --stack-name AwsOcppGatewayStack \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

#### View ECS Deployment Logs
```bash
# Check ECS service events
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service \
  --query 'services[0].events'

# Check container logs
aws logs tail /aws/ecs/AwsOcppGatewayStack-LogGroup --follow
```

## Environment-Specific Deployments

### Development Environment

```bash
# Use separate stack for development
export CDK_DEPLOY_ACCOUNT=123456789012
export CDK_DEPLOY_REGION=us-east-1

npx cdk deploy --stack-name AwsOcppGatewayStack-Dev \
  --context environment=dev
```

### Staging Environment

```bash
# Deploy to staging with different configuration
export CDK_DEPLOY_ACCOUNT=123456789012
export CDK_DEPLOY_REGION=us-west-2

npx cdk deploy --stack-name AwsOcppGatewayStack-Staging \
  --context environment=staging
```

### Production Environment

```bash
# Deploy to production with high availability
export CDK_DEPLOY_ACCOUNT=987654321098
export CDK_DEPLOY_REGION=us-east-1

npx cdk deploy --stack-name AwsOcppGatewayStack-Prod \
  --context environment=production
```

### Multi-Region Deployment

```bash
# Deploy to multiple regions for high availability
regions=("us-east-1" "us-west-2" "eu-west-1")

for region in "${regions[@]}"; do
  export CDK_DEPLOY_REGION=$region
  npx cdk deploy --stack-name AwsOcppGatewayStack-$region
done
```

## Post-Deployment Configuration

### 1. Set Up Monitoring

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "OCPP-Gateway" \
  --dashboard-body file://monitoring/dashboard.json
```

### 2. Configure Alarms

```bash
# Create CloudWatch alarms for critical metrics
aws cloudwatch put-metric-alarm \
  --alarm-name "OCPP-Gateway-High-CPU" \
  --alarm-description "OCPP Gateway high CPU usage" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 3. Set Up Log Aggregation

```bash
# Create log insights queries
aws logs put-query-definition \
  --name "OCPP-Gateway-Errors" \
  --log-group-names "/aws/ecs/AwsOcppGatewayStack-LogGroup" \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc'
```

## Cleanup

### Remove All Resources

```bash
# Destroy the stack and all resources
npx cdk destroy

# Confirm deletion when prompted
# Are you sure you want to delete: AwsOcppGatewayStack (y/n)? y
```

### Manual Cleanup (if needed)

```bash
# Remove any remaining IoT things
aws iot list-things --query 'things[?starts_with(thingName, `CP_`)].thingName' \
  --output text | xargs -I {} aws iot delete-thing --thing-name {}

# Empty and delete S3 buckets (if any created)
aws s3 ls | grep cdk | awk '{print $3}' | xargs -I {} aws s3 rb s3://{} --force
```

---

## Next Steps

After successful deployment:

1. **[Testing Guide](./testing.md)**: Test your deployment
2. **[API Reference](./api-reference.md)**: Learn the APIs
3. **[Monitoring](./monitoring.md)**: Set up monitoring and alerts
4. **[Security](./security.md)**: Implement security best practices

## Support

For deployment issues:
- Check [Troubleshooting Guide](./troubleshooting.md)
- Review CloudFormation events in AWS Console
- Check AWS service status in your region
- Ensure all prerequisites are met 