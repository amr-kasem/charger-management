# Quick Start Guide

## Overview

Get your OCPP Management System up and running in 30 minutes with this streamlined guide. For detailed information, see the [complete documentation](./README.md).

## Prerequisites Checklist

✅ **AWS Account** with billing enabled  
✅ **Administrator IAM permissions** (or [specific permissions](./deployment.md#required-iam-permissions))  
✅ **AWS CLI** installed and configured  
✅ **Node.js 16+** installed  
✅ **Docker** installed and running  
✅ **Git** for cloning the repository  

### Quick Setup

```bash
# Install AWS CLI (if needed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure AWS
aws configure  # Enter your access key, secret, region

# Install Node.js (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install CDK CLI
npm install -g aws-cdk

# Verify Docker is running
docker version
```

## 5-Minute Deployment

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/aws-samples/aws-ocpp-gateway.git
cd aws-ocpp-gateway

# Install dependencies
npm install
```

### 2. Configure Environment

```bash
# Set deployment target (replace with your account ID and region)
export CDK_DEPLOY_ACCOUNT=123456789012
export CDK_DEPLOY_REGION=us-east-1

# Verify settings
echo "Deploying to Account: $CDK_DEPLOY_ACCOUNT, Region: $CDK_DEPLOY_REGION"
```

### 3. Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK (only needed once per account/region)
npx cdk bootstrap aws://$CDK_DEPLOY_ACCOUNT/$CDK_DEPLOY_REGION
```

### 4. Deploy System

```bash
# Deploy the OCPP Gateway (takes ~8-10 minutes)
npx cdk deploy

# Confirm deployment when prompted
# Do you wish to deploy these changes (y/n)? y
```

### 5. Save Deployment URLs

```bash
# Extract and save important URLs
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

# Display URLs
echo "🚀 Deployment Complete!"
echo "WebSocket URL: $WEBSOCKET_URL"
echo "Remote Start API: $REMOTE_START_URL"
echo "Remote Stop API: $REMOTE_STOP_URL"
```

## 10-Minute Testing

### 1. Create Test Charge Point

```bash
# Create a test charge point in AWS IoT
aws iot create-thing --thing-name "CP001"

# Verify creation
aws iot describe-thing --thing-name "CP001"
```

### 2. Test WebSocket Connection

```bash
# Install WebSocket client
npm install -g wscat

# Test connection (should connect successfully)
wscat -c $WEBSOCKET_URL/CP001 -s ocpp2.0.1
```

### 3. Send Boot Notification

In the wscat terminal, send:
```json
[2,"boot1","BootNotification",{"chargingStation":{"model":"TestCP","vendorName":"TestVendor","firmwareVersion":"1.0","serialNumber":"TEST001"},"reason":"PowerUp"}]
```

Expected response:
```json
[3,"boot1",{"currentTime":"2023-12-01T10:00:00Z","interval":10,"status":"Accepted"}]
```

### 4. Test Remote Transaction API

```bash
# Test Remote Start Transaction
curl -X POST $REMOTE_START_URL \
  -H "Content-Type: application/json" \
  -d '{
    "chargePointId": "CP001",
    "idTag": "user-123",
    "connectorId": 1
  }'
```

Expected response:
```json
{
  "message": "RequestStartTransaction command sent successfully",
  "messageId": "uuid-123",
  "chargePointId": "CP001",
  "remoteStartId": 1234567890
}
```

### 5. Verify Device Shadow

```bash
# Check charge point shadow after boot notification
aws iot-data get-thing-shadow \
  --thing-name "CP001" \
  shadow.json && cat shadow.json | jq .
```

Expected shadow content:
```json
{
  "state": {
    "reported": {
      "chargingStation": {
        "model": "TestCP",
        "vendorName": "TestVendor",
        "firmwareVersion": "1.0",
        "serialNumber": "TEST001"
      }
    }
  }
}
```

## Using the Charge Point Simulator

### 1. Setup Simulator

```bash
# Navigate to simulator directory
cd ev-charge-point-simulator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Simulator

```bash
# Run simulator with your WebSocket URL
python3 simulate.py \
  --url $WEBSOCKET_URL \
  --cp-id CP001 \
  --cp-model "Quick Start CP" \
  --cp-vendor "AWS Demo"
```

Expected output:
```
INFO:root:CP001: connected to central system
INFO:root:CP001: heartbeat interval set to 10
INFO:ocpp:CP001: send [2,"uuid","Heartbeat",{}]
INFO:ocpp:CP001: receive message [3,"uuid",{"currentTime":"2023-12-01T10:00:00Z"}]
```

## Quick Monitoring Setup

### 1. View Logs

```bash
# View gateway container logs
aws logs tail /aws/ecs/AwsOcppGatewayStack-LogGroup --follow

# View Lambda function logs
aws logs tail /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor --follow
```

### 2. Monitor IoT Topics

```bash
# Subscribe to MQTT topics to see message flow
aws iot-data subscribe-to-topic --topic-name "CP001/in"  # Charge point to cloud
aws iot-data subscribe-to-topic --topic-name "CP001/out" # Cloud to charge point
```

### 3. Check System Health

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service \
  --query 'services[0].runningCount'

# Check Lambda function status
aws lambda get-function \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --query 'Configuration.State'
```

## Testing Remote Transaction APIs

### Remote Start Transaction

```bash
# Start a charging transaction
curl -X POST $REMOTE_START_URL \
  -H "Content-Type: application/json" \
  -d '{
    "chargePointId": "CP001",
    "idTag": "test-user-456",
    "connectorId": 1
  }'
```

### Remote Stop Transaction

```bash
# Stop a transaction (use transaction ID from your system)
curl -X POST $REMOTE_STOP_URL \
  -H "Content-Type: application/json" \
  -d '{
    "chargePointId": "CP001",
    "transactionId": 123456789
  }'
```

## Common Quick Fixes

### Issue: WebSocket Connection Rejected

**Cause**: Charge point not registered in IoT Core

**Fix**:
```bash
# Create the charge point
aws iot create-thing --thing-name "YOUR_CP_ID"
```

### Issue: Docker Permission Denied

**Cause**: User not in docker group

**Fix**:
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Issue: CDK Bootstrap Required

**Cause**: First CDK deployment in account/region

**Fix**:
```bash
npx cdk bootstrap aws://$CDK_DEPLOY_ACCOUNT/$CDK_DEPLOY_REGION
```

### Issue: Lambda Function Errors

**Cause**: Various configuration issues

**Debug**:
```bash
# Check recent Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

## Quick Load Test

Test with multiple charge points:

```bash
# Create multiple test charge points
for i in {1..10}; do
  aws iot create-thing --thing-name "CP$(printf "%03d" $i)"
done

# Run multiple simulators
cd ev-charge-point-simulator
for i in {1..5}; do
  python3 simulate.py --url $WEBSOCKET_URL --cp-id "CP$(printf "%03d" $i)" &
done
```

## Cost Estimation

**Quick Cost Calculation** (500 charge points, 24/7 operation):

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate | ~$55 |
| IoT Core | ~$30 |
| NAT Gateway | ~$25 |
| Load Balancer | ~$20 |
| Lambda | ~$4 |
| Other Services | ~$41 |
| **Total** | **~$175** |

*Costs vary by region and usage patterns*

## Next Steps

🎯 **You're now ready to:**

1. **[Integrate Real Charge Points](./api-reference.md#websocket-api)** - Connect actual OCPP devices
2. **[Set Up Monitoring](./monitoring.md)** - Configure alerts and dashboards  
3. **[Add Security](./security.md)** - Implement production security measures
4. **[Scale the System](./scaling.md)** - Configure auto-scaling and high availability
5. **[Develop Applications](./api-reference.md#sdk-examples)** - Build management applications

## Quick Reference Card

### Essential URLs
```bash
# WebSocket Gateway
$WEBSOCKET_URL/{chargePointId}

# Remote Start Transaction
POST $REMOTE_START_URL
{"chargePointId": "string", "idTag": "string", "connectorId": 1}

# Remote Stop Transaction  
POST $REMOTE_STOP_URL
{"chargePointId": "string", "transactionId": 123456789}
```

### Key Commands
```bash
# Create charge point
aws iot create-thing --thing-name "CP_ID"

# Check logs
aws logs tail /aws/ecs/AwsOcppGatewayStack-LogGroup --follow

# Test connection
wscat -c $WEBSOCKET_URL/CP_ID -s ocpp2.0.1

# Clean up
npx cdk destroy
```

### OCPP Message Examples
```json
// Boot Notification
[2,"id","BootNotification",{"chargingStation":{"model":"X","vendorName":"Y"},"reason":"PowerUp"}]

// Heartbeat
[2,"id","Heartbeat",{}]

// Transaction Event
[2,"id","TransactionEvent",{"eventType":"Started","timestamp":"2023-12-01T10:00:00Z","transactionInfo":{"transactionId":"123"}}]
```

---

🚀 **Congratulations!** You now have a fully functional OCPP Management System running on AWS.

For detailed documentation, troubleshooting, and advanced configuration, see:
- **[Complete Documentation](./README.md)**
- **[Deployment Guide](./deployment.md)**
- **[Testing Guide](./testing.md)**
- **[Troubleshooting](./troubleshooting.md)** 