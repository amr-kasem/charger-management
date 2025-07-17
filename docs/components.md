# Component Overview

## Introduction

This document provides detailed technical information about each component in the OCPP Management System. Understanding these components is essential for development, troubleshooting, and extending the system.

## 1. OCPP Gateway Container

### Overview
The OCPP Gateway is the core component that handles WebSocket connections from charge points and translates OCPP messages to MQTT for AWS IoT Core integration.

### Technical Specifications

**Container Image**: `aws-ocpp-gateway-container`
- **Base Image**: Amazon Linux 2022
- **Runtime**: Python 3.10
- **Dependencies**: WebSockets, asyncio-mqtt, boto3
- **Health Check**: HTTP endpoint on port 8080

**Resource Configuration**:
```yaml
CPU: 256 vCPU units (0.25 vCPU)
Memory: 512 MB
File Descriptors: 65,536 (ulimit)
Port Mappings: 8080:8080
```

### Key Files

#### `gateway.py` - Core Gateway Logic
```python
class Gateway(asyncio_mqtt.Client):
    """
    Gateway wrapper around asyncio_mqtt.Client that handles:
    - IoT Core MQTT connection setup
    - WebSocket to MQTT message relay
    - Charge point validation
    - SSL/TLS certificate management
    """
```

**Key Methods**:
- `charge_point_exists()`: Validates charge point registration in DynamoDB
- `create_ssl_context()`: Sets up TLS certificates for IoT Core
- `relay(topic)`: Forwards MQTT messages to WebSocket
- `forward(topic)`: Forwards WebSocket messages to MQTT

#### `server.py` - WebSocket Server
```python
async def handler(websocket, path):
    """
    WebSocket connection handler that:
    - Validates OCPP protocol subprotocol
    - Extracts charge point ID from path
    - Creates Gateway instance for the connection
    - Manages bidirectional message flow
    """
```

**Protocol Support**:
- OCPP 1.6 (`ocpp1.6`)
- OCPP 2.0 (`ocpp2.0`)
- OCPP 2.0.1 (`ocpp2.0.1`)

### Environment Variables

```bash
AWS_REGION=<region>                      # AWS region for services
DYNAMODB_CHARGE_POINT_TABLE=<table>     # DynamoDB table name
IOT_ENDPOINT=<endpoint>                  # IoT Core endpoint URL
IOT_PORT=8883                           # MQTT over TLS port
OCPP_PROTOCOLS=ocpp1.6,ocpp2.0,ocpp2.0.1  # Supported protocols
OCPP_GATEWAY_PORT=8080                  # WebSocket server port
```

### Secret Management

The gateway retrieves TLS certificates from AWS Secrets Manager:
- `IOT_AMAZON_ROOT_CA`: Amazon Root CA certificate
- `IOT_GATEWAY_CERTIFICATE`: Gateway's IoT certificate
- `IOT_GATEWAY_PUBLIC_KEY`: Public key for the certificate
- `IOT_GATEWAY_PRIVATE_KEY`: Private key for the certificate

### Connection Flow

1. **Charge Point Connection**: CP initiates WebSocket to `ws://gateway/chargePointId`
2. **Protocol Negotiation**: Gateway validates OCPP subprotocol
3. **Charge Point Validation**: Checks DynamoDB for registered charge point
4. **MQTT Setup**: Establishes secure MQTT connection to IoT Core
5. **Message Relay**: Bidirectional message forwarding begins

## 2. Lambda Functions

### Message Processor Lambda

**Purpose**: Processes all incoming OCPP messages from charge points

**Configuration**:
```yaml
Runtime: python3.9
Architecture: arm64
Memory: 128 MB
Timeout: 30 seconds
Event Source: SQS (IncomingMessagesQueue)
```

**Key Components**:

#### `MessageProcessor` Class
```python
class MessageProcessor:
    def __init__(self):
        self.iot = boto3.client("iot-data")
        self._handlers = {
            Action.boot_notification: BootNotificationHandler(self.iot),
            Action.heartbeat: HeartbeatHandler(),
            Action.status_notification: StatusNotificationHandler(),
            Action.transaction_event: TransactionEventHandler(self.iot),
            Action.request_start_transaction: RequestStartTransactionHandler(self.iot),
            Action.request_stop_transaction: RequestStopTransactionHandler(self.iot),
        }
        self._call_result_handler = CallResultHandler(self.iot)
        self._default_handler = UnsupportedMessageHandler()
```

**Message Routing Logic**:
- CallResult messages → `CallResultHandler`
- Action-based messages → Specific handlers
- Unknown messages → `UnsupportedMessageHandler`

### Remote Transaction Lambdas

#### Remote Start Transaction
```python
def lambda_handler(event, context):
    """
    Processes remote start requests:
    1. Extracts charge point ID and parameters
    2. Creates OCPP RequestStartTransaction message
    3. Publishes to {chargePointId}/out topic
    """
```

**Input Format**:
```json
{
  "chargePointId": "CP001",
  "idTag": "user-123",
  "connectorId": 1,
  "transactionData": {} // Optional
}
```

**OCPP Message Generated**:
```json
[2, "uuid", "RequestStartTransaction", {
  "idToken": {"idToken": "user-123", "type": "ISO14443"},
  "evseId": 1,
  "remoteStartId": 123456789
}]
```

#### Remote Stop Transaction
```python
def lambda_handler(event, context):
    """
    Processes remote stop requests:
    1. Extracts transaction ID
    2. Creates OCPP RequestStopTransaction message
    3. Publishes to charge point
    """
```

**Input Format**:
```json
{
  "chargePointId": "CP001",
  "transactionId": 123456789
}
```

## 3. Message Handlers

### Handler Architecture

All handlers implement the base `Handler` interface:
```python
class Handler(ABC):
    @abstractmethod
    def handle(self, charge_point_id: str, message: Any) -> Dict[str, Any]:
        """Handle a specific OCPP message type"""
        pass
```

### Implemented Handlers

#### 1. BootNotificationHandler
**Purpose**: Processes charge point registration messages

**Functionality**:
- Updates IoT device shadow with charge point metadata
- Returns registration acceptance with heartbeat interval
- Stores hardware attributes (model, vendor, firmware, etc.)

**Response**:
```json
{
  "currentTime": "2023-12-01T10:00:00Z",
  "interval": 10,
  "status": "Accepted"
}
```

#### 2. HeartbeatHandler
**Purpose**: Responds to periodic heartbeat messages

**Functionality**:
- Provides current timestamp to charge point
- Maintains connection keepalive
- No state persistence required

#### 3. StatusNotificationHandler
**Purpose**: Processes charge point status updates

**Functionality**:
- Receives connector status changes
- Updates charge point availability
- Empty response (acknowledgment only)

#### 4. TransactionEventHandler
**Purpose**: Processes transaction lifecycle events

**Functionality**:
- Handles Started, Updated, Ended transaction events
- Updates device shadow with transaction state
- Stores transaction history

**Shadow Updates**:
- `activeTransaction`: Current transaction details
- `lastCompletedTransaction`: Most recent completed transaction
- `lastTransactionEvent`: Latest event details

#### 5. RequestStartTransactionHandler
**Purpose**: Handles remote start transaction requests

**Functionality**:
- Validates start request parameters
- Generates transaction ID
- Updates shadow with transaction info
- Returns Accepted/Rejected status

#### 6. RequestStopTransactionHandler
**Purpose**: Handles remote stop transaction requests

**Functionality**:
- Validates transaction exists
- Updates transaction status to "Stopped"
- Returns Accepted/Rejected status

#### 7. CallResultHandler
**Purpose**: Processes responses to remote commands

**Functionality**:
- Logs command response status
- Updates shadow with call result info
- No response required (response to a response)

#### 8. UnsupportedMessageHandler
**Purpose**: Handles unknown or unsupported message types

**Functionality**:
- Logs unsupported message
- Returns original message (no processing)

## 4. Data Storage Components

### DynamoDB Table Structure

**Table**: `ChargePointTable`
```json
{
  "TableName": "AwsOcppGatewayStack-ChargePointTable",
  "KeySchema": [
    {
      "AttributeName": "chargePointId",
      "KeyType": "HASH"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "chargePointId",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

**Record Example**:
```json
{
  "chargePointId": "CP001",
  "timestamp": 1701427200000,
  "registrationTime": "2023-12-01T10:00:00Z"
}
```

### IoT Device Shadow Structure

**Classic Shadow Document**:
```json
{
  "state": {
    "reported": {
      "chargingStation": {
        "model": "SmartCharger Pro",
        "vendorName": "ACME Charging",
        "firmwareVersion": "v2.1.0",
        "serialNumber": "SC001234",
        "modem": {
          "iccid": "891004234814455936F",
          "imsi": "310410123456789"
        }
      },
      "activeTransaction": {
        "transactionId": 123456789,
        "evseId": 1,
        "idToken": "user-123",
        "startTime": "2023-12-01T14:30:00Z",
        "status": "Started"
      },
      "lastTransactionEvent": {
        "eventType": "Started",
        "timestamp": "2023-12-01T14:30:00Z",
        "transactionId": 123456789
      },
      "lastCallResult": {
        "messageId": "uuid-123",
        "receivedAt": "2023-12-01T14:29:45Z",
        "payload": {"status": "Accepted"}
      }
    }
  }
}
```

## 5. Network Components

### VPC Configuration

**CIDR Block**: `10.0.0.0/16`

**Subnets**:
- **Public Subnets**: Host NAT Gateway and Load Balancer
- **Private Subnets**: Host ECS tasks and Lambda functions

**Routing**:
- Public subnets route to Internet Gateway
- Private subnets route to NAT Gateway for outbound access

### Network Load Balancer

**Configuration**:
- **Type**: Network Load Balancer (Layer 4)
- **Scheme**: Internet-facing
- **IP Address Type**: IPv4
- **Load Balancer Name**: `ocpp-gateway`

**Target Group**:
- **Protocol**: TCP
- **Port**: 8080
- **Health Check**: TCP health check on port 8080
- **Deregistration Delay**: 10 seconds

**Listeners**:
- **Default**: Port 80 (TCP) → Port 8080 (TCP)
- **TLS (Optional)**: Port 443 (TLS) → Port 8080 (TCP)

### Security Groups

**Gateway Security Group**:
```yaml
Inbound Rules:
  - Port: 8080
    Protocol: TCP
    Source: 10.0.0.0/16 (VPC CIDR)
    
Outbound Rules:
  - Port: All
    Protocol: All
    Destination: 0.0.0.0/0
```

## 6. Auto-Scaling Configuration

### ECS Service Auto-Scaling

**Scaling Policy**:
```yaml
MetricType: CPUUtilization
TargetValue: 60%
ScaleOutCooldown: 30 seconds
ScaleInCooldown: 30 seconds

CapacityLimits:
  MinCapacity: 1
  MaxCapacity: 20
```

**Scaling Behavior**:
- Scale out when CPU > 60% for 2 consecutive periods
- Scale in when CPU < 60% for 2 consecutive periods
- Each scaling action adds/removes 1 instance

### Lambda Concurrency

**Configuration**:
- **Reserved Concurrency**: None (uses account pool)
- **Provisioned Concurrency**: None (cold starts acceptable)
- **Maximum Concurrency**: Account limit (default: 1000)

## 7. Monitoring Components

### CloudWatch Logs

**Log Groups**:
- `/aws/ecs/AwsOcppGatewayStack-LogGroup`: Gateway container logs
- `/aws/lambda/AwsOcppGatewayStack-OCPPMessageProcessor`: Message processor logs
- `/aws/lambda/AwsOcppGatewayStack-RemoteStartTransaction`: Remote start logs
- `/aws/lambda/AwsOcppGatewayStack-RemoteStopTransaction`: Remote stop logs

**Retention**: 1 day (configurable)

### Custom Metrics

**Gateway Metrics**:
- Active connection count
- Message processing rate
- Protocol version distribution

**Lambda Metrics**:
- Invocation count and duration
- Error rate and types
- Cold start frequency

## 8. Security Components

### IAM Roles and Policies

**Gateway Task Role**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:region:account:table/ChargePointTable"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:region:account:secret:*"
    }
  ]
}
```

**Lambda Execution Roles**:
- IoT publish permissions
- CloudWatch Logs write access
- DynamoDB read/write access

### Certificate Management

**IoT Certificates**:
- **Creation**: Automated via CDK custom resource
- **Storage**: AWS Secrets Manager
- **Rotation**: Manual process (can be automated)
- **Validation**: X.509 certificate validation

---

## Next Steps

- **[Message Handlers](./message-handlers.md)**: Detailed handler implementation
- **[API Reference](./api-reference.md)**: REST API documentation
- **[Testing Guide](./testing.md)**: Component testing procedures
- **[Troubleshooting](./troubleshooting.md)**: Common issues and solutions 