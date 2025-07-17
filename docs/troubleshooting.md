# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the OCPP Management System. Issues are organized by component and include step-by-step diagnostic procedures.

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [WebSocket Connection Problems](#websocket-connection-problems)
3. [Lambda Function Errors](#lambda-function-errors)
4. [OCPP Message Processing Issues](#ocpp-message-processing-issues)
5. [Performance Problems](#performance-problems)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Network and Security Issues](#network-and-security-issues)
8. [Cost and Billing Concerns](#cost-and-billing-concerns)

## Deployment Issues

### CDK Bootstrap Required

**Symptoms**:
```
Error: Need to perform AWS CDK bootstrap
```

**Cause**: CDK not bootstrapped in target account/region

**Solution**:
```bash
# Bootstrap CDK for your account/region
npx cdk bootstrap aws://$CDK_DEPLOY_ACCOUNT/$CDK_DEPLOY_REGION

# Verify bootstrap
aws cloudformation describe-stacks --stack-name CDKToolkit
```

**Prevention**: Always bootstrap before first CDK deployment in new account/region

---

### Docker Daemon Not Running

**Symptoms**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Cause**: Docker service not started or user lacks permissions

**Diagnosis**:
```bash
# Check Docker status
systemctl status docker

# Check if Docker is running
docker version
```

**Solution**:
```bash
# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, then verify
docker run hello-world
```

---

### Insufficient IAM Permissions

**Symptoms**:
```
User: arn:aws:iam::123456789012:user/username is not authorized to perform: action
```

**Diagnosis**:
```bash
# Check current user/role
aws sts get-caller-identity

# Test specific permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/username \
  --action-names cloudformation:CreateStack
```

**Solution**:
1. **Quick Fix** (Development): Attach `AdministratorAccess` policy
2. **Production Fix**: Use [minimal permissions](./deployment.md#required-iam-permissions)

---

### Platform Architecture Mismatch

**Symptoms**:
```
The requested image's platform (linux/arm64/v8) does not match the detected host platform
```

**Cause**: Docker image built for different architecture than host

**Solution**:
Edit `bin/aws-ocpp-gateway.ts`:
```typescript
new AwsOcppGatewayStack(app, 'AwsOcppGatewayStack', {
  // Change architecture to match your environment
  architecture: 'X86_64',  // Instead of 'arm64'
});
```

**Alternative**: Use Docker buildx for multi-platform builds

---

### Stack Already Exists

**Symptoms**:
```
Stack AwsOcppGatewayStack already exists
```

**Diagnosis**:
```bash
# Check existing stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Get stack details
aws cloudformation describe-stacks --stack-name AwsOcppGatewayStack
```

**Solutions**:
1. **Update existing stack**: `npx cdk deploy`
2. **Delete and recreate**: `npx cdk destroy && npx cdk deploy`
3. **Use different name**: `npx cdk deploy --stack-name AwsOcppGatewayStack-Dev`

---

## WebSocket Connection Problems

### Connection Immediately Rejected

**Symptoms**:
```
error: Unexpected server response: 502
```

**Diagnosis**:
```bash
# Check load balancer health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names AwsOcppGatewayStack-LoadBalancer* \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# Check ECS service status
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service \
  --query 'services[0].runningCount'
```

**Common Causes & Solutions**:

1. **ECS Service Not Running**:
   ```bash
   # Check service status
   aws ecs describe-services \
     --cluster AwsOcppGatewayStack-Cluster \
     --services AwsOcppGatewayStack-Service
   
   # Force new deployment
   aws ecs update-service \
     --cluster AwsOcppGatewayStack-Cluster \
     --service AwsOcppGatewayStack-Service \
     --force-new-deployment
   ```

2. **Target Group Unhealthy**:
   ```bash
   # Check health check settings
   aws elbv2 describe-target-groups \
     --names AwsOcppGatewayStack-LoadBalancer*
   ```

---

### Charge Point Not Registered Error

**Symptoms**:
```
Disconnected (code: 1008, reason: "Charge Point CP001 not registered as an IoT Thing")
```

**Diagnosis**:
```bash
# Check if IoT Thing exists
aws iot describe-thing --thing-name CP001

# Check DynamoDB entry
aws dynamodb get-item \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --key '{"chargePointId":{"S":"CP001"}}'
```

**Solution**:
```bash
# Create IoT Thing
aws iot create-thing --thing-name CP001

# Verify DynamoDB entry appears (may take a few seconds)
sleep 5
aws dynamodb get-item \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --key '{"chargePointId":{"S":"CP001"}}'
```

---

### Protocol Negotiation Failed

**Symptoms**:
```
Protocols Mismatched | Expected Subprotocols: ocpp2.0.1, but client supports ocpp1.6
```

**Solution**:
Use correct subprotocol version:
```bash
# For OCPP 2.0.1
wscat -c $WEBSOCKET_URL/CP001 -s ocpp2.0.1

# For OCPP 1.6 (if supported)
wscat -c $WEBSOCKET_URL/CP001 -s ocpp1.6
```

---

### Connection Timeout

**Symptoms**: Connection hangs without response

**Diagnosis**:
```bash
# Test connectivity to load balancer
telnet your-load-balancer-dns-name 80

# Check security groups
aws ec2 describe-security-groups \
  --group-ids $(aws ecs describe-services \
    --cluster AwsOcppGatewayStack-Cluster \
    --services AwsOcppGatewayStack-Service \
    --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]' \
    --output text)
```

**Solution**: Verify security group allows inbound traffic on port 8080

---

## Lambda Function Errors

### SQS Message Processing Failures

**Symptoms**: Messages stuck in SQS queue, not being processed

**Diagnosis**:
```bash
# Check SQS queue statistics
aws sqs get-queue-attributes \
  --queue-url $(aws sqs list-queues \
    --queue-name-prefix AwsOcppGatewayStack-IncomingMessages \
    --query 'QueueUrls[0]' --output text) \
  --attribute-names All

# Check Lambda function logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Common Solutions**:

1. **Lambda Function Timeout**:
   ```bash
   # Check function configuration
   aws lambda get-function-configuration \
     --function-name AwsOcppGatewayStack-OCPPMessageProcessor
   
   # Increase timeout if needed (via CDK)
   ```

2. **Memory Limit Exceeded**:
   ```bash
   # Check memory usage in logs
   aws logs filter-log-events \
     --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
     --filter-pattern "Memory Size"
   ```

3. **Dead Letter Queue Messages**:
   ```bash
   # Check dead letter queue
   aws sqs receive-message \
     --queue-url $(aws sqs list-queues \
       --queue-name-prefix AwsOcppGatewayStack-DeadLetterQueue \
       --query 'QueueUrls[0]' --output text)
   ```

---

### IoT Publish Permission Denied

**Symptoms**:
```
An error occurred (UnauthorizedOperation) when calling the Publish operation
```

**Diagnosis**:
```bash
# Check Lambda function role
aws lambda get-function \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --query 'Configuration.Role'

# Check role policies
aws iam list-role-policies --role-name ROLE_NAME
```

**Solution**: Verify IAM role has IoT publish permissions

---

### Import/Module Errors

**Symptoms**:
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'messages_lambda_handler'
```

**Diagnosis**:
```bash
# Check Lambda deployment package
aws lambda get-function \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --query 'Code.Location'

# Download and inspect package
curl -o function.zip "LOCATION_URL"
unzip -l function.zip
```

**Solution**: Redeploy with proper dependencies:
```bash
npx cdk deploy --force
```

---

## OCPP Message Processing Issues

### Invalid JSON Messages

**Symptoms**: Messages not processed, JSON parsing errors in logs

**Diagnosis**:
```bash
# Monitor IoT Core messages
aws iot-data subscribe-to-topic --topic-name "CP001/in"

# Check message format
aws logs filter-log-events \
  --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
  --filter-pattern "JSON"
```

**Solution**: Ensure OCPP messages follow correct format:
```json
[2, "message-id", "Action", {"payload": "object"}]
```

---

### Unsupported Message Types

**Symptoms**: Messages logged but not processed

**Diagnosis**:
```bash
# Check for unsupported message logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
  --filter-pattern "Received unsupported message"
```

**Solution**: Implement handlers for new message types or verify message format

---

### Device Shadow Update Failures

**Symptoms**: Shadow not updating after messages

**Diagnosis**:
```bash
# Check shadow update permissions
aws iot get-policy \
  --policy-name AwsOcppGatewayStack-Policy

# Test shadow update manually
aws iot-data update-thing-shadow \
  --thing-name CP001 \
  --payload '{"state":{"reported":{"test":"value"}}}' \
  test-shadow.json
```

**Solution**: Verify IoT policies allow shadow updates

---

## Performance Problems

### High Latency

**Symptoms**: Slow response times for OCPP messages

**Diagnosis**:
```bash
# Check ECS service metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=AwsOcppGatewayStack-Service \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-01T23:59:59Z \
  --period 300 \
  --statistics Average

# Check Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=AwsOcppGatewayStack-OCPPMessageProcessor \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-01T23:59:59Z \
  --period 300 \
  --statistics Average
```

**Solutions**:

1. **Scale up ECS service**:
   ```bash
   aws ecs update-service \
     --cluster AwsOcppGatewayStack-Cluster \
     --service AwsOcppGatewayStack-Service \
     --desired-count 3
   ```

2. **Optimize Lambda memory**:
   Edit CDK configuration to increase memory allocation

---

### Connection Drops

**Symptoms**: Frequent WebSocket disconnections

**Diagnosis**:
```bash
# Check ECS service stability
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service \
  --query 'services[0].events'

# Check load balancer metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/NetworkELB \
  --metric-name UnHealthyHostCount \
  --dimensions Name=LoadBalancer,Value=net/ocpp-gateway/LOAD_BALANCER_ID \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-01T23:59:59Z \
  --period 300 \
  --statistics Maximum
```

**Solutions**:
1. Increase health check grace period
2. Review auto-scaling policies
3. Check for resource limits

---

## Monitoring and Logging

### Missing Log Entries

**Symptoms**: Expected log entries not appearing in CloudWatch

**Diagnosis**:
```bash
# Check log group retention
aws logs describe-log-groups \
  --log-group-name-prefix /aws/ecs/AwsOcppGatewayStack

# Check ECS logging configuration
aws ecs describe-task-definition \
  --task-definition AwsOcppGatewayStack-Task
```

**Solution**: Verify log group permissions and retention settings

---

### High CloudWatch Costs

**Symptoms**: Unexpected charges for CloudWatch Logs

**Diagnosis**:
```bash
# Check log group sizes
aws logs describe-log-groups \
  --query 'logGroups[*].[logGroupName,storedBytes]' \
  --output table

# Check log retention settings
aws logs describe-log-groups \
  --query 'logGroups[*].[logGroupName,retentionInDays]' \
  --output table
```

**Solution**: Adjust log retention periods in CDK configuration

---

## Network and Security Issues

### TLS Certificate Problems

**Symptoms**: SSL/TLS connection errors with custom domain

**Diagnosis**:
```bash
# Check certificate status
aws acm list-certificates \
  --certificate-statuses ISSUED

# Test certificate
echo | openssl s_client -connect gateway.yourdomain.com:443 -servername gateway.yourdomain.com
```

**Solution**: Ensure DNS validation is complete for ACM certificate

---

### DNS Resolution Issues

**Symptoms**: Cannot connect to custom domain

**Diagnosis**:
```bash
# Check DNS resolution
nslookup gateway.yourdomain.com

# Check Route53 records
aws route53 list-resource-record-sets \
  --hosted-zone-id YOUR_HOSTED_ZONE_ID
```

**Solution**: Verify Route53 A record points to load balancer

---

## Cost and Billing Concerns

### Unexpected High Costs

**Diagnosis**:
```bash
# Check service costs using AWS Cost Explorer API
aws ce get-cost-and-usage \
  --time-period Start=2023-12-01,End=2023-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**Common Cost Drivers**:
1. **NAT Gateway**: $45/month per gateway
2. **Load Balancer**: $16-20/month
3. **ECS Fargate**: $24/month per running task
4. **IoT Core**: $0.08 per 100K messages

**Cost Optimization**:
1. Use VPC endpoints instead of NAT Gateway
2. Implement auto-scaling to reduce idle time
3. Optimize message frequency
4. Use reserved capacity for predictable workloads

---

## General Debugging Workflow

### 1. Identify the Component

```bash
# Check overall system health
aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service

aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `AwsOcppGatewayStack`)].FunctionName'

aws dynamodb describe-table \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --query 'Table.TableStatus'
```

### 2. Check Recent Logs

```bash
# Gateway logs
aws logs tail /aws/ecs/AwsOcppGatewayStack-LogGroup --since 1h

# Lambda logs
aws logs tail /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor --since 1h

# Error-specific search
aws logs filter-log-events \
  --log-group-name /aws/ecs/AwsOcppGatewayStack-LogGroup \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

### 3. Test Individual Components

```bash
# Test WebSocket connectivity
wscat -c $WEBSOCKET_URL/TEST_CP -s ocpp2.0.1

# Test Lambda function
aws lambda invoke \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --payload '{"Records":[{"body":"{\"test\":\"message\"}"}]}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Test API endpoints
curl -X POST $REMOTE_START_URL \
  -H "Content-Type: application/json" \
  -d '{"chargePointId":"TEST","idTag":"test"}'
```

### 4. Check Metrics and Alarms

```bash
# Check CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-names $(aws cloudwatch describe-alarms \
    --query 'MetricAlarms[?contains(AlarmName, `OCPP`)].AlarmName' \
    --output text)

# Get system metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=AwsOcppGatewayStack-Service \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```

---

## Getting Help

### Gather Information for Support

When reporting issues, include:

1. **Error Messages**: Complete error text and stack traces
2. **CloudFormation Stack Events**: Deployment failures
3. **CloudWatch Logs**: Recent log entries showing the issue
4. **System Configuration**: CDK version, AWS region, architecture
5. **Reproduction Steps**: Exact steps to reproduce the issue

### Useful Diagnostic Commands

```bash
# System information
echo "CDK Version: $(cdk --version)"
echo "AWS CLI Version: $(aws --version)"
echo "Node Version: $(node --version)"
echo "Docker Version: $(docker --version)"

# AWS environment
aws sts get-caller-identity
aws configure list

# Stack information
aws cloudformation describe-stacks \
  --stack-name AwsOcppGatewayStack \
  --query 'Stacks[0].{Status:StackStatus,Created:CreationTime}'
```

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **AWS Forums**: General AWS service questions
- **Stack Overflow**: Programming and configuration questions
- **AWS Support**: For AWS account-specific issues

---

## Preventive Measures

### Regular Health Checks

```bash
#!/bin/bash
# health-check.sh - Run daily to monitor system health

# Check ECS service
SERVICE_COUNT=$(aws ecs describe-services \
  --cluster AwsOcppGatewayStack-Cluster \
  --services AwsOcppGatewayStack-Service \
  --query 'services[0].runningCount')

if [ "$SERVICE_COUNT" -eq 0 ]; then
  echo "ALERT: ECS service not running"
fi

# Check recent errors
ERROR_COUNT=$(aws logs filter-log-events \
  --log-group-name /aws/ecs/AwsOcppGatewayStack-LogGroup \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'length(events)')

if [ "$ERROR_COUNT" -gt 10 ]; then
  echo "ALERT: High error rate detected"
fi
```

### Monitoring Best Practices

1. **Set up CloudWatch Alarms** for critical metrics
2. **Enable AWS X-Ray** for distributed tracing
3. **Use AWS Config** for configuration compliance
4. **Implement synthetic monitoring** with CloudWatch Synthetics
5. **Regular backup** of DynamoDB tables

---

## Next Steps

For more information:
- **[Monitoring Guide](./monitoring.md)**: Set up comprehensive monitoring
- **[Security Guide](./security.md)**: Implement security best practices
- **[Performance Tuning](./scaling.md)**: Optimize system performance
- **[API Reference](./api-reference.md)**: Complete API documentation 