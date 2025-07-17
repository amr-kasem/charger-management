#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import uuid

# Replace these with your actual function URLs from the AWS CloudFormation output
# You can get these from the AWS Console (Lambda -> Functions -> Your Function -> Configuration -> Function URL)
REMOTE_START_URL = "https://txxjjtyumtbrc2ofsv3kyhcx5u0osekq.lambda-url.eu-north-1.on.aws/"
REMOTE_STOP_URL = "https://d4szrf4iw3czy56gbkvr7f25t40qjwoz.lambda-url.eu-north-1.on.aws/"

def remote_start_transaction(charge_point_id, id_tag=None, connector_id=1):
    """
    Send a remote start transaction command to a charge point.
    
    Args:
        charge_point_id (str): ID of the charge point
        id_tag (str, optional): ID tag for authorization. Defaults to a random UUID.
        connector_id (int, optional): Connector ID (evseId in OCPP 2.0.1). Defaults to 1.
        
    Returns:
        dict: Response from the API
    """
    if id_tag is None:
        id_tag = str(uuid.uuid4())
        
    payload = {
        "chargePointId": charge_point_id,
        "connectorId": connector_id,  # Will be interpreted as evseId in the Lambda
        "idTag": id_tag  # Will be converted to idToken structure in the Lambda
    }
        
    try:
        print(f"Sending remote start transaction request to {charge_point_id}:")
        print(json.dumps(payload, indent=2))
        
        response = requests.post(
            REMOTE_START_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending remote start transaction: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def remote_stop_transaction(charge_point_id, transaction_id):
    """
    Send a remote stop transaction command to a charge point.
    
    Args:
        charge_point_id (str): ID of the charge point
        transaction_id (int): Transaction ID to stop
        
    Returns:
        dict: Response from the API
    """
    payload = {
        "chargePointId": charge_point_id,
        "transactionId": transaction_id
    }
    
    try:
        print(f"Sending remote stop transaction request to {charge_point_id}:")
        print(json.dumps(payload, indent=2))
        
        response = requests.post(
            REMOTE_STOP_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending remote stop transaction: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Send OCPP 2.0.1 remote start/stop commands')
    parser.add_argument('command', choices=['start', 'stop'], help='Command to execute')
    parser.add_argument('--charge-point-id', '-c', required=True, help='Charge point ID')
    parser.add_argument('--id-tag', '-i', help='ID token for authorization (only for start)')
    parser.add_argument('--connector-id', '-n', type=int, default=1, help='EVSE ID (only for start)')
    parser.add_argument('--transaction-id', '-t', type=int, help='Transaction ID (required for stop)')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        result = remote_start_transaction(args.charge_point_id, args.id_tag, args.connector_id)
        if result:
            print(f"\nRequestStartTransaction sent successfully:")
            print(json.dumps(result, indent=2))
    
    elif args.command == 'stop':
        if not args.transaction_id:
            print("Error: transaction-id is required for stop command")
            parser.print_help()
            sys.exit(1)
            
        result = remote_stop_transaction(args.charge_point_id, args.transaction_id)
        if result:
            print(f"\nRequestStopTransaction sent successfully:")
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 