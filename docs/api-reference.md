# API Reference

## Overview

This document provides complete API reference for the OCPP Management System, including REST APIs for remote control, WebSocket APIs for charge point communication, and MQTT topics for internal messaging.

## Table of Contents

1. [REST APIs](#rest-apis)
2. [WebSocket API](#websocket-api)
3. [OCPP Message Formats](#ocpp-message-formats)
4. [MQTT Topics](#mqtt-topics)
5. [Error Codes](#error-codes)
6. [Authentication](#authentication)

## REST APIs

### Remote Start Transaction API

**Endpoint**: `POST /remote-start-transaction`

**Description**: Initiates a charging transaction on a specific charge point.

#### Request

**URL**: Function URL from CloudFormation output `RemoteStartTransactionUrl`

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
```

**Body**:
```json
{
  "chargePointId": "string",     // Required: Charge point identifier
  "idTag": "string",             // Optional: User identification token
  "connectorId": 1,              // Optional: Connector ID (default: 1)
  "transactionData": {}          // Optional: Additional transaction data
}
```

**Example Request**:
```bash
curl -X POST https://your-function-url.lambda-url.region.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{
    "chargePointId": "CP001",
    "idTag": "user-123",
    "connectorId": 1
  }'
```

#### Response

**Success Response** (200 OK):
```json
{
  "message": "RequestStartTransaction command sent successfully",
  "messageId": "uuid-123",
  "chargePointId": "CP001",
  "remoteStartId": 1234567890
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Missing required parameter: chargePointId"
}
```

**Error Response** (500 Internal Server Error):
```json
{
  "error": "Failed to publish message: error details"
}
```

#### OCPP Message Generated

The API generates the following OCPP 2.0.1 message:
```json
[
  2,                              // Call message type
  "uuid-123",                     // Unique message ID
  "RequestStartTransaction",      // Action
  {
    "idToken": {
      "idToken": "user-123",
      "type": "ISO14443"
    },
    "evseId": 1,
    "remoteStartId": 1234567890
  }
]
```

### Remote Stop Transaction API

**Endpoint**: `POST /remote-stop-transaction`

**Description**: Terminates an active charging transaction.

#### Request

**URL**: Function URL from CloudFormation output `RemoteStopTransactionUrl`

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
```

**Body**:
```json
{
  "chargePointId": "string",     // Required: Charge point identifier
  "transactionId": 123456789     // Required: Transaction ID to stop
}
```

**Example Request**:
```bash
curl -X POST https://your-function-url.lambda-url.region.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{
    "chargePointId": "CP001",
    "transactionId": 123456789
  }'
```

#### Response

**Success Response** (200 OK):
```json
{
  "message": "RequestStopTransaction command sent successfully",
  "messageId": "uuid-456",
  "chargePointId": "CP001",
  "transactionId": 123456789
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Missing required parameter: transactionId"
}
```

#### OCPP Message Generated

```json
[
  2,                              // Call message type
  "uuid-456",                     // Unique message ID
  "RequestStopTransaction",       // Action
  {
    "transactionId": 123456789
  }
]
```

## WebSocket API

### Connection Endpoint

**URL Pattern**: `ws://gateway-url/{chargePointId}`

**Protocol**: WebSocket with OCPP subprotocol negotiation

**Supported Subprotocols**:
- `ocpp1.6`
- `ocpp2.0`
- `ocpp2.0.1`

### Connection Flow

1. **Initial Connection**:
```javascript
const ws = new WebSocket('ws://gateway-url/CP001', ['ocpp2.0.1']);
```

2. **Protocol Negotiation**:
   - Client requests OCPP subprotocol
   - Server validates and accepts supported protocol
   - Connection established with negotiated protocol

3. **Authentication**:
   - Charge point ID validated against DynamoDB registry
   - Connection rejected if charge point not registered

### Message Format

All OCPP messages follow the standard format:
```json
[MessageType, MessageId, Action, Payload]
```

**Message Types**:
- `2`: Call (request)
- `3`: CallResult (response)
- `4`: CallError (error response)

## OCPP Message Formats

### Supported OCPP 2.0.1 Messages

#### BootNotification

**Direction**: Charge Point → Central System

**Purpose**: Register charge point and receive configuration

**Format**:
```json
[
  2,
  "message-id",
  "BootNotification",
  {
    "chargingStation": {
      "model": "string",
      "vendorName": "string",
      "firmwareVersion": "string",
      "serialNumber": "string",
      "modem": {
        "iccid": "string",
        "imsi": "string"
      }
    },
    "reason": "PowerUp|FirmwareUpdate|LocalReset|RemoteReset|ScheduledReset"
  }
]
```

**Response**:
```json
[
  3,
  "message-id",
  {
    "currentTime": "2023-12-01T10:00:00Z",
    "interval": 10,
    "status": "Accepted|Pending|Rejected"
  }
]
```

#### Heartbeat

**Direction**: Charge Point → Central System

**Purpose**: Maintain connection and get current time

**Format**:
```json
[2, "message-id", "Heartbeat", {}]
```

**Response**:
```json
[
  3,
  "message-id",
  {
    "currentTime": "2023-12-01T10:00:00Z"
  }
]
```

#### StatusNotification

**Direction**: Charge Point → Central System

**Purpose**: Report connector status changes

**Format**:
```json
[
  2,
  "message-id",
  "StatusNotification",
  {
    "timestamp": "2023-12-01T10:00:00Z",
    "connectorStatus": "Available|Occupied|Reserved|Unavailable|Faulted",
    "evseId": 1,
    "connectorId": 1
  }
]
```

**Response**:
```json
[3, "message-id", {}]
```

#### TransactionEvent

**Direction**: Charge Point → Central System

**Purpose**: Report transaction lifecycle events

**Format**:
```json
[
  2,
  "message-id",
  "TransactionEvent",
  {
    "eventType": "Started|Updated|Ended",
    "timestamp": "2023-12-01T10:00:00Z",
    "transactionInfo": {
      "transactionId": "123456789"
    },
    "evse": {
      "id": 1
    },
    "idToken": {
      "idToken": "user-123",
      "type": "ISO14443"
    }
  }
]
```

**Response**:
```json
[3, "message-id", {}]
```

#### RequestStartTransaction

**Direction**: Central System → Charge Point

**Purpose**: Request charge point to start a transaction

**Format**:
```json
[
  2,
  "message-id",
  "RequestStartTransaction",
  {
    "idToken": {
      "idToken": "user-123",
      "type": "ISO14443"
    },
    "evseId": 1,
    "remoteStartId": 1234567890
  }
]
```

**Response**:
```json
[
  3,
  "message-id",
  {
    "status": "Accepted|Rejected"
  }
]
```

#### RequestStopTransaction

**Direction**: Central System → Charge Point

**Purpose**: Request charge point to stop a transaction

**Format**:
```json
[
  2,
  "message-id",
  "RequestStopTransaction",
  {
    "transactionId": "123456789"
  }
]
```

**Response**:
```json
[
  3,
  "message-id",
  {
    "status": "Accepted|Rejected"
  }
]
```

### CallError Format

**Structure**:
```json
[
  4,
  "message-id",
  "ErrorCode",
  "Error Description",
  {}
]
```

**Common Error Codes**:
- `NotImplemented`: Action not supported
- `NotSupported`: Feature not supported
- `InternalError`: Internal system error
- `ProtocolError`: Protocol violation
- `SecurityError`: Security-related error
- `FormationViolation`: Message format violation
- `PropertyConstraintViolation`: Property constraint violation
- `OccurrenceConstraintViolation`: Occurrence constraint violation
- `TypeConstraintViolation`: Type constraint violation
- `GenericError`: Generic error

## MQTT Topics

### Topic Structure

All MQTT topics follow the pattern: `{chargePointId}/{direction}`

#### Inbound Topics (Charge Point → Cloud)

**Topic**: `{chargePointId}/in`

**Purpose**: Messages from charge points to the cloud system

**Message Format**: OCPP JSON message as string

**Example**:
- Topic: `CP001/in`
- Payload: `[2,"123","Heartbeat",{}]`

#### Outbound Topics (Cloud → Charge Point)

**Topic**: `{chargePointId}/out`

**Purpose**: Messages from cloud system to charge points

**Message Format**: OCPP JSON message as string

**Example**:
- Topic: `CP001/out`
- Payload: `[2,"456","RequestStartTransaction",{"idToken":{"idToken":"user-123","type":"ISO14443"},"evseId":1}]`

#### Device Shadow Topics

**Update Topic**: `$aws/things/{chargePointId}/shadow/update`

**Purpose**: Update charge point device shadow

**Message Format**: AWS IoT Device Shadow JSON

**Example**:
```json
{
  "state": {
    "reported": {
      "chargingStation": {
        "model": "SmartCharger Pro",
        "vendorName": "ACME"
      },
      "activeTransaction": {
        "transactionId": 123456789,
        "evseId": 1,
        "startTime": "2023-12-01T10:00:00Z"
      }
    }
  }
}
```

## Error Codes

### HTTP Error Codes

| Code | Description | Cause |
|------|-------------|-------|
| 400 | Bad Request | Missing required parameters, invalid JSON |
| 500 | Internal Server Error | Lambda function error, IoT publish failure |

### WebSocket Error Codes

| Code | Description | Cause |
|------|-------------|-------|
| 1000 | Normal Closure | Connection closed normally |
| 1008 | Policy Violation | Charge point not registered |
| 1011 | Internal Error | Server error during processing |

### OCPP Error Codes

Standard OCPP error codes as defined in OCPP 2.0.1 specification.

## Authentication

### IoT Core Authentication

**Method**: X.509 Certificate Authentication

**Certificate Management**:
- Certificates automatically generated during deployment
- Stored in AWS Secrets Manager
- Used by OCPP Gateway for IoT Core connection

### API Authentication

**Current**: No authentication (for testing)

**Production Recommendation**: 
```json
{
  "authType": "AWS_IAM",
  "cors": {
    "allowedOrigins": ["https://yourdomain.com"],
    "allowedMethods": ["POST"],
    "allowedHeaders": ["Authorization", "Content-Type"]
  }
}
```

**IAM Policy Example**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunctionUrl",
      "Resource": [
        "arn:aws:lambda:region:account:function:RemoteStartTransaction",
        "arn:aws:lambda:region:account:function:RemoteStopTransaction"
      ]
    }
  ]
}
```

## SDK Examples

### Python SDK Example

```python
import requests
import json

class OCPPClient:
    def __init__(self, remote_start_url, remote_stop_url):
        self.remote_start_url = remote_start_url
        self.remote_stop_url = remote_stop_url
    
    def start_transaction(self, charge_point_id, id_tag, connector_id=1):
        """Start a charging transaction"""
        payload = {
            "chargePointId": charge_point_id,
            "idTag": id_tag,
            "connectorId": connector_id
        }
        
        response = requests.post(self.remote_start_url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def stop_transaction(self, charge_point_id, transaction_id):
        """Stop a charging transaction"""
        payload = {
            "chargePointId": charge_point_id,
            "transactionId": transaction_id
        }
        
        response = requests.post(self.remote_stop_url, json=payload)
        response.raise_for_status()
        return response.json()

# Usage
client = OCPPClient(
    remote_start_url="https://your-start-url",
    remote_stop_url="https://your-stop-url"
)

# Start transaction
result = client.start_transaction("CP001", "user-123", 1)
print(f"Transaction started: {result}")

# Stop transaction
result = client.stop_transaction("CP001", 123456789)
print(f"Transaction stopped: {result}")
```

### JavaScript SDK Example

```javascript
class OCPPClient {
    constructor(remoteStartUrl, remoteStopUrl) {
        this.remoteStartUrl = remoteStartUrl;
        this.remoteStopUrl = remoteStopUrl;
    }
    
    async startTransaction(chargePointId, idTag, connectorId = 1) {
        const response = await fetch(this.remoteStartUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chargePointId,
                idTag,
                connectorId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async stopTransaction(chargePointId, transactionId) {
        const response = await fetch(this.remoteStopUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chargePointId,
                transactionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
}

// Usage
const client = new OCPPClient(
    'https://your-start-url',
    'https://your-stop-url'
);

// Start transaction
try {
    const result = await client.startTransaction('CP001', 'user-123', 1);
    console.log('Transaction started:', result);
} catch (error) {
    console.error('Error starting transaction:', error);
}
```

## Rate Limits

### API Rate Limits

**Lambda Function URLs**:
- No built-in rate limiting
- Limited by Lambda concurrency (1000 concurrent executions default)
- Consider implementing API Gateway for rate limiting in production

**Recommended Rate Limits**:
- Remote Start/Stop: 10 requests/second per charge point
- Burst: 100 requests

### WebSocket Limits

**Connection Limits**:
- 65,536 connections per gateway instance
- Auto-scaling supports up to 20 instances (1.3M connections)

**Message Rate Limits**:
- No enforced limits
- Recommended: ≤1 message/second per connection for heartbeats

## Versioning

### API Versioning

**Current Version**: v1 (implicit)

**Future Versioning Strategy**:
- URL path versioning: `/v2/remote-start-transaction`
- Header versioning: `API-Version: v2`

### OCPP Protocol Versioning

**Supported Versions**:
- OCPP 1.6 (legacy support)
- OCPP 2.0 (full support)
- OCPP 2.0.1 (full support, recommended)

**Version Selection**:
- Determined by WebSocket subprotocol negotiation
- Default: OCPP 2.0.1

---

## Next Steps

- **[Testing Guide](./testing.md)**: API testing procedures
- **[Components](./components.md)**: Implementation details
- **[Security](./security.md)**: Security best practices
- **[Troubleshooting](./troubleshooting.md)**: Common API issues 