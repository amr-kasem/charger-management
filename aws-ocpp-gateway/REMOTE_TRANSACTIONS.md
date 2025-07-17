# OCPP 2.0.1 Remote Transaction Control

This document explains how to use the remote transaction control functionality in the OCPP 2.0.1 gateway.

## Overview

The OCPP 2.0.1 specification provides functionality for a central system to remotely start and stop charging transactions on charge points. This implementation includes:

1. Lambda functions for sending remote start and stop commands to charge points
2. Message handlers for processing responses from charge points
3. Testing utilities to demonstrate the functionality

## Remote Transaction Flow

### Remote Start Transaction

1. Central system sends a `RequestStartTransaction` command to the charge point
2. Charge point processes the request and responds with `RequestStartTransactionResponse` (a CallResult message)
3. If the response status is "Accepted", the charge point will initiate a transaction
4. The charge point sends a `TransactionEvent` with eventType "Started" to report the start of the transaction

### Remote Stop Transaction

1. Central system sends a `RequestStopTransaction` command to the charge point with a transaction ID
2. Charge point processes the request and responds with `RequestStopTransactionResponse` (a CallResult message)
3. If the response status is "Accepted", the charge point will stop the transaction
4. The charge point sends a `TransactionEvent` with eventType "Ended" to report the end of the transaction

## Message Types in OCPP 2.0.1

The OCPP protocol uses different message types:

1. **Call (2)**: Commands sent to charge points (like RequestStartTransaction)
2. **CallResult (3)**: Responses to commands (like RequestStartTransactionResponse)
3. **CallError (4)**: Error responses

This implementation handles all these message types, including proper processing of CallResult messages that are received in response to commands sent to charge points.

## Using the API

### Remote Start Transaction API

**Endpoint**: `[RemoteStartTransactionUrl]`

**Method**: POST

**Request Body**:
```json
{
  "chargePointId": "CP001",
  "connectorId": 1,
  "idTag": "RFID12345"
}
```

**Parameters**:
- `chargePointId` (required): ID of the target charge point
- `connectorId` (optional): ID of the connector/EVSE to start the transaction on (defaults to 1)
- `idTag` (optional): Authorization ID token (if omitted, a random ID will be generated)

**Response**:
```json
{
  "message": "RequestStartTransaction command sent successfully",
  "messageId": "8b5d3e1a-5d2c-4c1b-9c1e-8c1d2e3f4a5b",
  "chargePointId": "CP001"
}
```

### Remote Stop Transaction API

**Endpoint**: `[RemoteStopTransactionUrl]`

**Method**: POST

**Request Body**:
```json
{
  "chargePointId": "CP001",
  "transactionId": 1234567890
}
```

**Parameters**:
- `chargePointId` (required): ID of the target charge point
- `transactionId` (required): ID of the transaction to stop

**Response**:
```json
{
  "message": "RequestStopTransaction command sent successfully",
  "messageId": "a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6",
  "chargePointId": "CP001",
  "transactionId": 1234567890
}
```

## Testing with the Command Line Tool

The repository includes a command-line tool for testing remote transaction functionality:

```
python test_remote_transaction.py start --charge-point-id CP001 --id-tag TAG12345 --connector-id 1
```

```
python test_remote_transaction.py stop --charge-point-id CP001 --transaction-id 1234567890
```

## Implementation Details

### Message Handlers

The system implements these handlers:

1. `RequestStartTransactionHandler`: Handles responses to remote start commands
2. `RequestStopTransactionHandler`: Handles responses to remote stop commands 
3. `TransactionEventHandler`: Processes transaction events from charge points
4. `CallResultHandler`: Processes CallResult messages (responses to commands sent to charge points)

### CallResult Processing

CallResult messages are received when a charge point responds to a command:

1. When a `RequestStartTransaction` command is sent, the charge point responds with a CallResult containing the status
2. The CallResult is processed by the `CallResultHandler` which:
   - Logs the response status (Accepted/Rejected)
   - Updates the charge point's shadow with the response information
   - No further response is needed from the system

### AWS IoT Shadow Integration

Transaction data is stored in the charge point's AWS IoT device shadow to maintain state:

- Active transaction info is stored when a transaction starts
- Transaction status is updated when a transaction ends
- Transaction event details are logged for monitoring
- Command responses (CallResults) are stored in the shadow for tracking 