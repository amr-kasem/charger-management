# Testing Guide

## Overview

This guide provides comprehensive testing procedures for the OCPP Management System, covering unit testing, integration testing, load testing, and manual validation. Follow these procedures to ensure system reliability and performance.

## Table of Contents

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Load Testing](#load-testing)
6. [API Testing](#api-testing)
7. [Charge Point Simulator Testing](#charge-point-simulator-testing)
8. [Monitoring and Validation](#monitoring-and-validation)
9. [Troubleshooting Tests](#troubleshooting-tests)

## Pre-Testing Setup

### Prerequisites

1. **Deployed System**: Complete CDK deployment
2. **AWS CLI**: Configured with appropriate permissions
3. **Python Environment**: Python 3.8+ with required packages
4. **Testing Tools**: curl, wscat, Python requests library

### Environment Configuration

```bash
# Set your deployment outputs
export WEBSOCKET_URL="ws://your-load-balancer-dns-name"
export REMOTE_START_URL="https://your-remote-start-lambda-url"
export REMOTE_STOP_URL="https://your-remote-stop-lambda-url"
export AWS_REGION="your-region"
```

### Test Data Setup

Create test charge points in AWS IoT Core:

```bash
# Create IoT Thing for testing
aws iot create-thing --thing-name "CP_TEST_001" --region $AWS_REGION
aws iot create-thing --thing-name "CP_TEST_002" --region $AWS_REGION
```

## Unit Testing

### Lambda Function Tests

#### Testing Message Processor

**Test File**: `test_message_processor.py`

```python
import pytest
import json
from unittest.mock import Mock, patch
from ocpp_message_processor.message_processor import MessageProcessor
from ocpp.v201 import call

class TestMessageProcessor:
    def setup_method(self):
        self.processor = MessageProcessor()
        
    @patch('boto3.client')
    def test_boot_notification_processing(self, mock_boto):
        # Mock IoT client
        mock_iot = Mock()
        mock_boto.return_value = mock_iot
        
        # Create test message
        message = call.BootNotification(
            charging_station={
                "model": "Test Model",
                "vendor_name": "Test Vendor"
            },
            reason="PowerUp"
        )
        
        # Process message
        self.processor.process_message("CP_TEST_001", message)
        
        # Verify IoT publish was called
        mock_iot.publish.assert_called()
        
    def test_heartbeat_processing(self):
        message = call.Heartbeat()
        result = self.processor.process_message("CP_TEST_001", message)
        # Verify heartbeat response contains current time
        assert 'currentTime' in str(result)
```

**Run Unit Tests**:
```bash
cd aws-ocpp-gateway/src/lambdas
python -m pytest test_message_processor.py -v
```

#### Testing Remote Transaction Functions

**Test File**: `test_remote_transactions.py`

```python
import json
import pytest
from unittest.mock import Mock, patch
from remote_start_transaction import lambda_handler as start_handler
from remote_stop_transaction import lambda_handler as stop_handler

class TestRemoteTransactions:
    
    @patch('boto3.client')
    def test_remote_start_success(self, mock_boto):
        mock_iot = Mock()
        mock_boto.return_value = mock_iot
        
        event = {
            'body': json.dumps({
                'chargePointId': 'CP_TEST_001',
                'idTag': 'test-user',
                'connectorId': 1
            })
        }
        
        response = start_handler(event, {})
        
        assert response['statusCode'] == 200
        mock_iot.publish.assert_called_once()
        
    @patch('boto3.client')
    def test_remote_stop_success(self, mock_boto):
        mock_iot = Mock()
        mock_boto.return_value = mock_iot
        
        event = {
            'body': json.dumps({
                'chargePointId': 'CP_TEST_001',
                'transactionId': 123456
            })
        }
        
        response = stop_handler(event, {})
        
        assert response['statusCode'] == 200
        mock_iot.publish.assert_called_once()
```

### Gateway Container Tests

**Test File**: `test_gateway.py`

```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from gateway import Gateway, ChargePointDoesNotExist

class TestGateway:
    
    @patch('boto3.resource')
    def test_charge_point_exists_true(self, mock_dynamo):
        mock_table = Mock()
        mock_table.get_item.return_value = {'Item': {'chargePointId': 'CP_TEST_001'}}
        mock_dynamo.return_value.Table.return_value = mock_table
        
        mock_websocket = Mock()
        gateway = Gateway('CP_TEST_001', mock_websocket)
        
        assert gateway.charge_point_exists() == True
        
    @patch('boto3.resource')
    def test_charge_point_exists_false(self, mock_dynamo):
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamo.return_value.Table.return_value = mock_table
        
        mock_websocket = Mock()
        
        with pytest.raises(ChargePointDoesNotExist):
            Gateway('CP_NONEXISTENT', mock_websocket)
```

## Integration Testing

### WebSocket Connection Testing

#### Basic Connection Test

```bash
# Test WebSocket connection with wscat
wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp2.0.1
```

**Expected Output**:
```
Connected (press CTRL+C to quit)
>
```

#### Protocol Negotiation Test

```bash
# Test invalid protocol
wscat -c $WEBSOCKET_URL/CP_TEST_001 -s invalid-protocol
```

**Expected Output**:
```
error: Unexpected server response: 400
```

#### Unregistered Charge Point Test

```bash
# Test connection with unregistered charge point
wscat -c $WEBSOCKET_URL/CP_UNREGISTERED -s ocpp2.0.1
```

**Expected Output**:
```
Connected (press CTRL+C to quit)
Disconnected (code: 1008, reason: "Charge Point CP_UNREGISTERED not registered as an IoT Thing")
```

### Message Flow Testing

#### Boot Notification Test

**Send via WebSocket**:
```json
[2,"12345","BootNotification",{"chargingStation":{"model":"Test Model","vendorName":"Test Vendor","firmwareVersion":"1.0","serialNumber":"TEST001"},"reason":"PowerUp"}]
```

**Expected Response**:
```json
[3,"12345",{"currentTime":"2023-12-01T10:00:00Z","interval":10,"status":"Accepted"}]
```

#### Heartbeat Test

**Send via WebSocket**:
```json
[2,"12346","Heartbeat",{}]
```

**Expected Response**:
```json
[3,"12346",{"currentTime":"2023-12-01T10:00:00Z"}]
```

### IoT Core Integration Testing

#### MQTT Topic Monitoring

```bash
# Subscribe to IoT Core topics for testing
aws iot-data subscribe-to-topic \
  --topic-name "CP_TEST_001/in" \
  --region $AWS_REGION
```

#### Device Shadow Verification

```bash
# Check device shadow after boot notification
aws iot-data get-thing-shadow \
  --thing-name "CP_TEST_001" \
  --region $AWS_REGION \
  shadow.json

cat shadow.json | jq '.state.reported'
```

## End-to-End Testing

### Complete Transaction Flow Test

**Test Script**: `test_complete_flow.py`

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import requests
import time

async def test_complete_transaction_flow():
    """Test complete charge point transaction flow"""
    
    # Step 1: Connect charge point
    uri = "ws://your-gateway-url/CP_TEST_001"
    
    async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as websocket:
        
        # Step 2: Send Boot Notification
        boot_msg = [2, "msg1", "BootNotification", {
            "chargingStation": {
                "model": "TestCP",
                "vendorName": "TestVendor",
                "firmwareVersion": "1.0",
                "serialNumber": "TEST001"
            },
            "reason": "PowerUp"
        }]
        
        await websocket.send(json.dumps(boot_msg))
        response = await websocket.recv()
        print(f"Boot Response: {response}")
        
        # Step 3: Send Heartbeat
        heartbeat_msg = [2, "msg2", "Heartbeat", {}]
        await websocket.send(json.dumps(heartbeat_msg))
        response = await websocket.recv()
        print(f"Heartbeat Response: {response}")
        
        # Step 4: Send Remote Start Transaction
        start_payload = {
            "chargePointId": "CP_TEST_001",
            "idTag": "test-user-123",
            "connectorId": 1
        }
        
        start_response = requests.post(
            "https://your-remote-start-url",
            json=start_payload
        )
        print(f"Remote Start Response: {start_response.json()}")
        
        # Step 5: Receive Remote Start Command
        command = await websocket.recv()
        print(f"Received Command: {command}")
        
        # Step 6: Send Remote Start Response
        cmd_data = json.loads(command)
        response_msg = [3, cmd_data[1], {"status": "Accepted"}]
        await websocket.send(json.dumps(response_msg))
        
        # Step 7: Send Transaction Event (Started)
        transaction_event = [2, "msg3", "TransactionEvent", {
            "eventType": "Started",
            "timestamp": "2023-12-01T10:00:00Z",
            "transactionInfo": {"transactionId": "12345"},
            "evse": {"id": 1}
        }]
        
        await websocket.send(json.dumps(transaction_event))
        response = await websocket.recv()
        print(f"Transaction Event Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_complete_transaction_flow())
```

**Run E2E Test**:
```bash
python test_complete_flow.py
```

## Load Testing

### Connection Load Test

**Test Script**: `load_test_connections.py`

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import time
from concurrent.futures import ThreadPoolExecutor

async def connect_charge_point(cp_id, duration=60):
    """Simulate a single charge point connection"""
    uri = f"ws://your-gateway-url/CP_LOAD_{cp_id:03d}"
    
    try:
        async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as websocket:
            
            # Send boot notification
            boot_msg = [2, f"boot_{cp_id}", "BootNotification", {
                "chargingStation": {
                    "model": f"LoadTest_{cp_id}",
                    "vendorName": "LoadTestVendor",
                    "firmwareVersion": "1.0",
                    "serialNumber": f"LOAD{cp_id:06d}"
                },
                "reason": "PowerUp"
            }]
            
            await websocket.send(json.dumps(boot_msg))
            await websocket.recv()
            
            # Send heartbeats for duration
            start_time = time.time()
            msg_count = 0
            
            while time.time() - start_time < duration:
                heartbeat_msg = [2, f"hb_{cp_id}_{msg_count}", "Heartbeat", {}]
                await websocket.send(json.dumps(heartbeat_msg))
                await websocket.recv()
                
                msg_count += 1
                await asyncio.sleep(10)  # 10-second heartbeat interval
                
            print(f"CP_{cp_id:03d}: Sent {msg_count} messages")
            
    except Exception as e:
        print(f"CP_{cp_id:03d}: Error - {e}")

async def run_load_test(num_connections, duration=300):
    """Run load test with specified number of connections"""
    
    # Create IoT Things for load test
    print(f"Creating {num_connections} IoT Things for load test...")
    for i in range(num_connections):
        try:
            import boto3
            iot = boto3.client('iot')
            iot.create_thing(thingName=f"CP_LOAD_{i:03d}")
        except Exception as e:
            print(f"Warning: Could not create CP_LOAD_{i:03d}: {e}")
    
    print(f"Starting load test with {num_connections} connections...")
    
    tasks = []
    for i in range(num_connections):
        task = connect_charge_point(i, duration)
        tasks.append(task)
    
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    # Test with 10 connections for 5 minutes
    asyncio.run(run_load_test(10, 300))
```

### Message Throughput Test

**Test Script**: `throughput_test.py`

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import time
import statistics

async def throughput_test(cp_id, messages_per_second=1, duration=60):
    """Test message throughput for a single connection"""
    uri = f"ws://your-gateway-url/CP_THROUGHPUT_{cp_id}"
    
    response_times = []
    
    async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as websocket:
        
        # Boot notification
        boot_msg = [2, "boot", "BootNotification", {
            "chargingStation": {"model": "ThroughputTest", "vendorName": "Test"},
            "reason": "PowerUp"
        }]
        await websocket.send(json.dumps(boot_msg))
        await websocket.recv()
        
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration:
            msg_start = time.time()
            
            # Send heartbeat
            msg = [2, f"msg_{message_count}", "Heartbeat", {}]
            await websocket.send(json.dumps(msg))
            await websocket.recv()
            
            response_time = time.time() - msg_start
            response_times.append(response_time)
            
            message_count += 1
            
            # Control message rate
            sleep_time = (1.0 / messages_per_second) - response_time
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Calculate statistics
        avg_response = statistics.mean(response_times)
        min_response = min(response_times)
        max_response = max(response_times)
        p95_response = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        print(f"CP {cp_id} Results:")
        print(f"  Messages: {message_count}")
        print(f"  Avg Response Time: {avg_response:.3f}s")
        print(f"  Min Response Time: {min_response:.3f}s")
        print(f"  Max Response Time: {max_response:.3f}s")
        print(f"  95th Percentile: {p95_response:.3f}s")

if __name__ == "__main__":
    # Create test thing
    import boto3
    iot = boto3.client('iot')
    try:
        iot.create_thing(thingName="CP_THROUGHPUT_001")
    except:
        pass
    
    # Run throughput test
    asyncio.run(throughput_test("001", messages_per_second=2, duration=60))
```

## API Testing

### Remote Transaction API Tests

#### Remote Start Transaction API

**Test Script**: `test_remote_start_api.py`

```python
#!/usr/bin/env python3
import requests
import json
import time

def test_remote_start_api():
    """Test Remote Start Transaction API"""
    
    url = "https://your-remote-start-lambda-url"
    
    # Test 1: Valid request
    payload = {
        "chargePointId": "CP_TEST_001",
        "idTag": "test-user-123",
        "connectorId": 1
    }
    
    response = requests.post(url, json=payload)
    
    print(f"Test 1 - Valid Request:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    # Test 2: Missing required field
    invalid_payload = {
        "idTag": "test-user-123",
        "connectorId": 1
        # Missing chargePointId
    }
    
    response = requests.post(url, json=invalid_payload)
    
    print(f"Test 2 - Missing chargePointId:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    # Test 3: Invalid JSON
    response = requests.post(url, data="invalid-json")
    
    print(f"Test 3 - Invalid JSON:")
    print(f"Status Code: {response.status_code}")
    print()

if __name__ == "__main__":
    test_remote_start_api()
```

#### Remote Stop Transaction API

**Test Script**: `test_remote_stop_api.py`

```python
#!/usr/bin/env python3
import requests
import json

def test_remote_stop_api():
    """Test Remote Stop Transaction API"""
    
    url = "https://your-remote-stop-lambda-url"
    
    # Test 1: Valid request
    payload = {
        "chargePointId": "CP_TEST_001",
        "transactionId": 123456789
    }
    
    response = requests.post(url, json=payload)
    
    print(f"Test 1 - Valid Request:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    # Test 2: Missing transaction ID
    invalid_payload = {
        "chargePointId": "CP_TEST_001"
        # Missing transactionId
    }
    
    response = requests.post(url, json=invalid_payload)
    
    print(f"Test 2 - Missing transactionId:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_remote_stop_api()
```

## Charge Point Simulator Testing

### Using the Built-in Simulator

The system includes a charge point simulator for testing. Here's how to use it:

#### Setup Simulator

```bash
cd aws-ocpp-gateway/ev-charge-point-simulator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Basic Simulator Test

```bash
# Create test charge point
aws iot create-thing --thing-name "CP_SIM_001"

# Run simulator
python3 simulate.py \
  --url $WEBSOCKET_URL \
  --cp-id CP_SIM_001 \
  --cp-model "Simulator Pro" \
  --cp-vendor "Test Systems" \
  --cp-version "2.0.1"
```

#### Multiple Simulator Instances

**Script**: `run_multiple_simulators.py`

```python
#!/usr/bin/env python3
import subprocess
import time
import boto3
from concurrent.futures import ThreadPoolExecutor

def create_and_run_simulator(cp_id, gateway_url):
    """Create IoT Thing and run simulator"""
    
    # Create IoT Thing
    iot = boto3.client('iot')
    try:
        iot.create_thing(thingName=cp_id)
        print(f"Created IoT Thing: {cp_id}")
    except Exception as e:
        print(f"Thing {cp_id} might already exist: {e}")
    
    # Run simulator
    cmd = [
        "python3", "simulate.py",
        "--url", gateway_url,
        "--cp-id", cp_id,
        "--cp-model", f"Simulator_{cp_id}",
        "--cp-vendor", "TestSystems"
    ]
    
    try:
        process = subprocess.run(cmd, timeout=300, capture_output=True, text=True)
        print(f"Simulator {cp_id} completed")
    except subprocess.TimeoutExpired:
        print(f"Simulator {cp_id} timed out (normal for long-running test)")
    except Exception as e:
        print(f"Simulator {cp_id} error: {e}")

def run_multiple_simulators(num_simulators, gateway_url):
    """Run multiple simulators concurrently"""
    
    with ThreadPoolExecutor(max_workers=num_simulators) as executor:
        futures = []
        
        for i in range(num_simulators):
            cp_id = f"CP_SIM_{i:03d}"
            future = executor.submit(create_and_run_simulator, cp_id, gateway_url)
            futures.append(future)
        
        # Wait for all simulators to complete
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Simulator error: {e}")

if __name__ == "__main__":
    gateway_url = "ws://your-gateway-url"
    run_multiple_simulators(5, gateway_url)
```

## Monitoring and Validation

### CloudWatch Metrics Validation

#### Check Gateway Metrics

```bash
# Get ECS service metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=AwsOcppGatewayStack-Service \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-01T23:59:59Z \
  --period 300 \
  --statistics Average
```

#### Check Lambda Metrics

```bash
# Get Lambda invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=AwsOcppGatewayStack-OCPPMessageProcessor \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-01T23:59:59Z \
  --period 300 \
  --statistics Sum
```

### Log Analysis

#### Check Gateway Logs

```bash
# Get recent gateway logs
aws logs filter-log-events \
  --log-group-name /aws/ecs/AwsOcppGatewayStack-LogGroup \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

#### Check Lambda Logs

```bash
# Get Lambda function logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

### Performance Validation

#### Connection Count Monitoring

```bash
# Check active connections (requires custom metric implementation)
aws cloudwatch get-metric-statistics \
  --namespace OCPP/Gateway \
  --metric-name ActiveConnections \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --period 300 \
  --statistics Maximum
```

#### Message Processing Rate

```bash
# Check message processing rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfMessagesSent \
  --dimensions Name=QueueName,Value=AwsOcppGatewayStack-IncomingMessagesQueue \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting Tests

### Common Test Failures

#### 1. WebSocket Connection Refused

**Symptoms**: Connection immediately rejected

**Test**:
```bash
# Check load balancer health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/target-group-name
```

#### 2. OCPP Protocol Errors

**Symptoms**: Protocol negotiation failures

**Test**:
```bash
# Test with specific protocol version
wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp1.6
wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp2.0
wscat -c $WEBSOCKET_URL/CP_TEST_001 -s ocpp2.0.1
```

#### 3. Lambda Function Timeouts

**Symptoms**: SQS messages not processed

**Test**:
```bash
# Check Lambda function errors
aws lambda invoke \
  --function-name AwsOcppGatewayStack-OCPPMessageProcessor \
  --payload '{"Records":[{"body":"{\"chargePointId\":\"CP_TEST_001\",\"message\":[2,\"test\",\"Heartbeat\",{}]}"}]}' \
  response.json

cat response.json
```

#### 4. DynamoDB Access Issues

**Symptoms**: Charge point validation failures

**Test**:
```bash
# Verify DynamoDB table access
aws dynamodb get-item \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --key '{"chargePointId":{"S":"CP_TEST_001"}}'
```

### Test Environment Cleanup

#### Remove Test Resources

```bash
#!/bin/bash
# cleanup_test_resources.sh

# Remove test IoT Things
for i in {1..100}; do
  aws iot delete-thing --thing-name "CP_TEST_$(printf "%03d" $i)" 2>/dev/null
  aws iot delete-thing --thing-name "CP_LOAD_$(printf "%03d" $i)" 2>/dev/null
  aws iot delete-thing --thing-name "CP_SIM_$(printf "%03d" $i)" 2>/dev/null
done

# Clear DynamoDB test entries
aws dynamodb scan \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --filter-expression "begins_with(chargePointId, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"CP_TEST_"}}' \
  --projection-expression "chargePointId" \
| jq -r '.Items[].chargePointId.S' \
| xargs -I {} aws dynamodb delete-item \
  --table-name AwsOcppGatewayStack-ChargePointTable \
  --key '{"chargePointId":{"S":"{}"}}'

echo "Test cleanup completed"
```

---

## Test Automation

### Continuous Integration Tests

For CI/CD pipelines, create automated test suites:

**Test Suite**: `ci_test_suite.py`

```python
#!/usr/bin/env python3
import pytest
import asyncio
import requests
import time
import os

class TestOCPPSystemCI:
    
    def setup_class(self):
        self.gateway_url = os.environ.get('WEBSOCKET_URL')
        self.remote_start_url = os.environ.get('REMOTE_START_URL')
        self.remote_stop_url = os.environ.get('REMOTE_STOP_URL')
        
        assert self.gateway_url, "WEBSOCKET_URL environment variable required"
        assert self.remote_start_url, "REMOTE_START_URL environment variable required"
        assert self.remote_stop_url, "REMOTE_STOP_URL environment variable required"
    
    def test_api_endpoints_respond(self):
        """Test that API endpoints are responsive"""
        
        # Test remote start endpoint
        response = requests.post(self.remote_start_url, json={
            "chargePointId": "CP_CI_TEST",
            "idTag": "ci-test"
        })
        assert response.status_code in [200, 400]  # 400 is OK for unregistered CP
        
        # Test remote stop endpoint
        response = requests.post(self.remote_stop_url, json={
            "chargePointId": "CP_CI_TEST",
            "transactionId": 123
        })
        assert response.status_code in [200, 400]  # 400 is OK for unregistered CP
    
    def test_websocket_gateway_accessible(self):
        """Test that WebSocket gateway is accessible"""
        import websockets
        
        async def test_connection():
            try:
                uri = f"{self.gateway_url}/CP_CI_TEST"
                async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as ws:
                    return True
            except Exception:
                return False
        
        result = asyncio.run(test_connection())
        # Connection should fail for unregistered CP, but gateway should be accessible
        assert isinstance(result, bool)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run CI Tests**:
```bash
export WEBSOCKET_URL="ws://your-gateway-url"
export REMOTE_START_URL="https://your-remote-start-url"
export REMOTE_STOP_URL="https://your-remote-stop-url"

python ci_test_suite.py
```

---

## Next Steps

- **[Troubleshooting](./troubleshooting.md)**: Detailed troubleshooting guide
- **[Monitoring](./monitoring.md)**: Set up comprehensive monitoring
- **[Load Testing](./load-testing.md)**: Advanced load testing scenarios
- **[API Reference](./api-reference.md)**: Complete API documentation 