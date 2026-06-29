#!/usr/bin/env python3
"""Request SMS spending limit increase via AWS Support API."""
import boto3

def request_sms_limit_increase(target_limit_usd=10):
    """Create a support case to increase SMS spending limit."""
    support = boto3.client('support', region_name='us-east-1')
    
    case_body = f"""Hello AWS Support,

I am using Amazon SNS SMS for incident notifications in my PITER AiOps application.
I have reached my monthly SMS spending limit and would like to request an increase.

Current limit: $1.00 USD (default)
Requested limit: ${target_limit_usd}.00 USD

Use case: Production incident notifications for NOC/DevOps team alerting.

Thank you for your assistance.
"""
    
    try:
        response = support.create_case(
            subject=f'Request SMS Spending Limit Increase to ${target_limit_usd}',
            serviceCode='sns',
            severityCode='normal',
            categoryCode='other',
            communicationBody=case_body,
            language='en',
            issueType='technical'
        )
        case_id = response['caseId']
        print(f"✓ Support case created: {case_id}")
        print("  Check status in AWS Console → Support Center")
        print("  Typical response time: 12-24 hours")
        return case_id
    except Exception as e:
        print(f"✗ Failed to create support case: {e}")
        print("\nAlternative: Use AWS Console method (see instructions below)")
        return None

def check_current_limit():
    """Check current SMS spend via SNS."""
    sns = boto3.client('sns', region_name='us-east-1')
    try:
        attrs = sns.get_sms_attributes()['attributes']
        limit = attrs.get('MonthlySpendLimit', 'Not set')
        print(f"Current SMS monthly spend limit: ${limit}")
    except Exception as e:
        print(f"Could not retrieve SMS attributes: {e}")

if __name__ == '__main__':
    print("AWS SMS Spending Limit Increase Request\n")
    check_current_limit()
    print()
    
    # Check if Support API is available (requires Business/Enterprise support plan)
    try:
        support = boto3.client('support', region_name='us-east-1')
        support.describe_services()
        print("AWS Support API is available - creating case...\n")
        request_sms_limit_increase(target_limit_usd=10)
    except Exception as e:
        if 'SubscriptionRequiredException' in str(e):
            print("⚠ AWS Support API requires Business or Enterprise support plan")
            print("\nUse Console method instead (free):\n")
            print("1. Go to: https://console.aws.amazon.com/support/home#/case/create")
            print("2. Select: Service limit increase")
            print("3. Limit type: SNS Text Messaging (SMS)")
            print("4. Request: Increase monthly spending quota to $10")
            print("5. Use case: Production incident notifications")
            print("\nTypical approval time: 12-24 hours")
        else:
            print(f"Error: {e}")
