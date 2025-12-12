"""
AWS Connector - Fixed for Streamlit Secrets
Handles AWS credential management and session creation
"""

import boto3
import streamlit as st
from botocore.exceptions import ClientError, NoCredentialsError
import os

def get_aws_credentials():
    """
    Get AWS credentials from multiple sources in priority order:
    1. Streamlit secrets
    2. Environment variables
    3. AWS CLI configuration
    4. IAM role (if running on EC2)
    """
    
    # Try Streamlit secrets first
    try:
        if hasattr(st, 'secrets') and 'aws' in st.secrets:
            aws_config = st.secrets['aws']
            return {
                'aws_access_key_id': aws_config.get('access_key_id'),
                'aws_secret_access_key': aws_config.get('secret_access_key'),
                'region_name': aws_config.get('default_region', 'us-east-1')
            }
    except Exception as e:
        print(f"Could not read from Streamlit secrets: {e}")
    
    # Try session state (if saved via UI)
    try:
        if hasattr(st, 'session_state'):
            if 'aws_access_key' in st.session_state and 'aws_secret_key' in st.session_state:
                return {
                    'aws_access_key_id': st.session_state.aws_access_key,
                    'aws_secret_access_key': st.session_state.aws_secret_key,
                    'region_name': st.session_state.get('aws_region', 'us-east-1')
                }
    except Exception as e:
        print(f"Could not read from session state: {e}")
    
    # Try environment variables
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    if access_key and secret_key:
        return {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
            'region_name': region
        }
    
    # Let boto3 try default credential chain (AWS CLI, IAM role, etc.)
    return None

def get_aws_session(region=None):
    """
    Create and return AWS session
    
    Args:
        region: Optional region override
        
    Returns:
        boto3.Session object or None
    """
    
    try:
        credentials = get_aws_credentials()
        
        if credentials:
            # Use explicit credentials
            session = boto3.Session(
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key'],
                region_name=region or credentials.get('region_name', 'us-east-1')
            )
            
            # Test the session
            try:
                sts = session.client('sts')
                sts.get_caller_identity()
                return session
            except Exception as e:
                print(f"Session test failed: {e}")
                return None
        else:
            # Try default credential chain
            session = boto3.Session(region_name=region or 'us-east-1')
            
            # Test the session
            try:
                sts = session.client('sts')
                sts.get_caller_identity()
                return session
            except Exception as e:
                print(f"Default credential chain failed: {e}")
                return None
                
    except Exception as e:
        print(f"Error creating AWS session: {e}")
        return None

def test_aws_connection():
    """
    Test AWS connection and return status
    
    Returns:
        dict with status, account_id, region
    """
    
    try:
        session = get_aws_session()
        
        if not session:
            return {
                'connected': False,
                'error': 'No AWS credentials found'
            }
        
        # Get account information
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        return {
            'connected': True,
            'account_id': identity['Account'],
            'user_id': identity['UserId'],
            'arn': identity['Arn'],
            'region': session.region_name
        }
        
    except NoCredentialsError:
        return {
            'connected': False,
            'error': 'No credentials found'
        }
    except ClientError as e:
        return {
            'connected': False,
            'error': str(e)
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }

def get_available_regions():
    """
    Get list of available AWS regions
    
    Returns:
        list of region names
    """
    
    try:
        session = get_aws_session()
        if session:
            ec2 = session.client('ec2', region_name='us-east-1')
            regions = ec2.describe_regions()
            return [region['RegionName'] for region in regions['Regions']]
        else:
            # Return common regions if can't connect
            return [
                'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
            ]
    except Exception as e:
        print(f"Error getting regions: {e}")
        return [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
        ]

# Convenience functions for getting clients and resources

def get_client(service_name, region=None):
    """
    Get AWS client for a service
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'rds', 's3')
        region: Optional region override
        
    Returns:
        boto3 client or None
    """
    
    try:
        session = get_aws_session(region)
        if session:
            return session.client(service_name)
        return None
    except Exception as e:
        print(f"Error creating client for {service_name}: {e}")
        return None

def get_resource(service_name, region=None):
    """
    Get AWS resource for a service
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'rds', 's3')
        region: Optional region override
        
    Returns:
        boto3 resource or None
    """
    
    try:
        session = get_aws_session(region)
        if session:
            return session.resource(service_name)
        return None
    except Exception as e:
        print(f"Error creating resource for {service_name}: {e}")
        return None

# Main execution for testing
if __name__ == "__main__":
    print("Testing AWS Connection...")
    result = test_aws_connection()
    
    if result['connected']:
        print(f"✅ Connected!")
        print(f"   Account: {result['account_id']}")
        print(f"   Region: {result['region']}")
        print(f"   ARN: {result['arn']}")
    else:
        print(f"❌ Not connected: {result['error']}")
