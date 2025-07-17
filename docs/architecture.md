# System Architecture

## Overview

The OCPP Management System implements a cloud-native, serverless architecture designed for scalability, reliability, and cost-effectiveness. The system bridges the gap between OCPP-compliant charge points and cloud-based management services using AWS infrastructure.

## High-Level Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐    MQTT      ┌─────────────────┐
│   Charge Points │ ◄────────────► │  OCPP Gateway   │ ◄─────────► │   AWS IoT Core  │
│   (OCPP 1.6,    │                │  (ECS Fargate)  │             │                 │
│    2.0, 2.0.1)  │                │                 │             │                 │
└─────────────────┘                └─────────────────┘             └─────────────────┘
                                            │                               │
                                            │                               │
                                            ▼                               ▼
                                   ┌─────────────────┐             ┌─────────────────┐
                                   │      VPC        │             │ Lambda Functions│
                                   │  Load Balancer  │             │ Message         │
                                   │  Auto Scaling   │             │ Processors      │
                                   └─────────────────┘             └─────────────────┘
                                                                           │
                                                                           ▼
                                                                  ┌─────────────────┐
                                                                  │   DynamoDB &    │
                                                                  │  Device Shadows │
                                                                  └─────────────────┘
```

## Core Components

### 1. OCPP Gateway (ECS Fargate)

**Purpose**: Acts as a WebSocket proxy between charge points and AWS IoT Core

**Key Features**:
- WebSocket server supporting OCPP protocols (1.6, 2.0, 2.0.1)
- Protocol translation between OCPP and MQTT
- Connection management and validation
- Auto-scaling based on CPU utilization

**Implementation Details**:
- **Container**: Amazon Linux 2022 with Python 3.10
- **Networking**: VPC with private and public subnets
- **Load Balancing**: Network Load Balancer (NLB) for TCP connections
- **Security**: TLS termination (optional with custom domain)
- **Scaling**: 1-20 instances based on CPU (60% target)

### 2. AWS IoT Core

**Purpose**: Secure, bi-directional communication hub for all charge point messages

**Key Features**:
- MQTT message broker
- Device shadows for state management
- Rules engine for message routing
- Certificate-based authentication

**Topic Structure**:
```
{chargePointId}/in   - Messages from charge points to cloud
{chargePointId}/out  - Messages from cloud to charge points
$aws/things/{chargePointId}/shadow/update - Device shadow updates
```

### 3. Lambda Functions

**Purpose**: Serverless message processing and business logic

**Functions Implemented**:

#### Message Processor Lambda
- **Trigger**: SQS queue from IoT Core rules
- **Purpose**: Process all incoming OCPP messages
- **Runtime**: Python 3.9 on ARM64
- **Memory**: 128 MB
- **Timeout**: 30 seconds

#### Remote Start Transaction Lambda
- **Trigger**: Function URL (HTTP API)
- **Purpose**: Send start transaction commands to charge points
- **Response**: Publishes to `{chargePointId}/out` topic

#### Remote Stop Transaction Lambda
- **Trigger**: Function URL (HTTP API)
- **Purpose**: Send stop transaction commands to charge points
- **Response**: Publishes to `{chargePointId}/out` topic

#### Delete Thing Lambda
- **Trigger**: SQS queue from IoT Core thing deletion events
- **Purpose**: Clean up DynamoDB entries when IoT Things are deleted

### 4. Data Storage

#### DynamoDB Table: `ChargePointTable`
- **Partition Key**: `chargePointId` (String)
- **Purpose**: Registry of registered charge points
- **Billing**: Pay-per-request
- **Encryption**: AWS managed keys

#### IoT Device Shadows
- **Purpose**: Store charge point state and configuration
- **Structure**: JSON documents with reported/desired states
- **Updates**: Real-time via MQTT

### 5. Message Queue System

#### SQS Queues
- **IncomingMessagesQueue**: Buffers messages from charge points
- **DeletedThings**: Handles charge point deregistration
- **Dead Letter Queues**: Error handling and retry logic

### 6. Network Infrastructure

#### VPC Configuration
```
CIDR: 10.0.0.0/16
├── Public Subnets (NAT Gateway, Load Balancer)
└── Private Subnets (ECS Tasks, Lambda Functions)
```

#### Security Groups
- **Gateway Security Group**: 
  - Inbound: Port 8080 from VPC CIDR
  - Outbound: All traffic (HTTPS, MQTT)

#### Load Balancer
- **Type**: Network Load Balancer (Layer 4)
- **Scheme**: Internet-facing
- **Listeners**: 
  - Port 80 (TCP) - Default configuration
  - Port 443 (TLS) - With custom domain

## Message Flow Architecture

### 1. Charge Point to Cloud Flow

```
1. Charge Point ──WebSocket──► OCPP Gateway
2. OCPP Gateway ──MQTT──► AWS IoT Core  
3. IoT Core ──Rules Engine──► SQS Queue
4. SQS ──Event Source──► Lambda Function
5. Lambda ──Processing──► Device Shadow Update
```

### 2. Cloud to Charge Point Flow

```
1. REST API ──HTTP──► Lambda Function
2. Lambda ──MQTT Publish──► IoT Core
3. IoT Core ──MQTT──► OCPP Gateway
4. OCPP Gateway ──WebSocket──► Charge Point
```

## Scalability Design

### Auto-Scaling Components

1. **ECS Service Auto-Scaling**
   - Metric: CPU Utilization
   - Target: 60%
   - Min Capacity: 1 instance
   - Max Capacity: 20 instances
   - Scale-out Cooldown: 30 seconds
   - Scale-in Cooldown: 30 seconds

2. **Lambda Concurrency**
   - Automatic scaling up to account limits
   - No reserved concurrency configured (uses account pool)

3. **DynamoDB**
   - On-demand billing mode
   - Automatic scaling based on traffic

### Performance Characteristics

- **WebSocket Connections**: 65,536 per gateway instance (ulimit)
- **Message Throughput**: ~1,000 messages/second per instance
- **Latency**: <100ms for message processing
- **Availability**: 99.9% (multi-AZ deployment)

## Security Architecture

### Network Security
- **VPC Isolation**: Private subnets for compute resources
- **Security Groups**: Restrictive ingress rules
- **TLS Encryption**: End-to-end encryption support

### Authentication & Authorization
- **IoT Core**: X.509 certificate-based authentication
- **IAM Roles**: Least privilege access for all components
- **API Security**: Function URLs without authentication (configure IAM for production)

### Certificate Management
- **IoT Certificates**: Automatically generated and stored in Secrets Manager
- **Root CA**: Amazon Root CA certificate
- **Certificate Rotation**: Manual process (can be automated)

## Monitoring & Observability

### CloudWatch Integration
- **Metrics**: Custom metrics for OCPP message processing
- **Logs**: Centralized logging from all components
- **Alarms**: Automated alerting for system health

### Key Metrics Tracked
- Gateway connection count
- Message processing rate
- Error rates and types
- Lambda duration and errors
- DynamoDB throttling events

## Deployment Architecture

### Infrastructure as Code
- **AWS CDK**: TypeScript-based infrastructure definition
- **Bootstrap**: Account and region preparation
- **Stack Deployment**: Single CloudFormation stack

### Environment Configuration
- **Development**: Single-AZ, minimal resources
- **Production**: Multi-AZ, high availability configuration
- **Cost Optimization**: Serverless-first approach

## Integration Points

### External Systems
- **Charge Point Vendors**: Standard OCPP WebSocket interface
- **Billing Systems**: Via Lambda functions and API Gateway
- **Monitoring Systems**: CloudWatch APIs and metrics
- **Management UIs**: Via AWS console and custom dashboards

### API Endpoints
- **WebSocket**: `ws://domain/chargePointId` or `wss://domain/chargePointId`
- **Remote Start**: `POST /remote-start-transaction`
- **Remote Stop**: `POST /remote-stop-transaction`

## Cost Optimization

### Serverless Design Benefits
- **Pay-per-use**: Lambda and DynamoDB on-demand pricing
- **No Idle Costs**: ECS auto-scaling to zero when possible
- **Managed Services**: Reduced operational overhead

### Estimated Monthly Costs (500 Charge Points)
- **Total**: ~$175/month
- **Breakdown**: See [Cost Optimization Guide](./cost-optimization.md)

---

## Next Steps

- **[Quick Start](./quick-start.md)**: Deploy the system
- **[Components](./components.md)**: Detailed component documentation
- **[Message Flow](./message-flow.md)**: Understand message processing
- **[Security](./security.md)**: Security best practices 