import pandas as pd
import requests
import json
import base64
from datetime import datetime
import os
import sys
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook

# Check that the necessary command line arguments were provided
if len(sys.argv) < 3:
    print("Usage: script.py bundle_id cloudAccountIds [from_time as 'YYYY-MM-DD HH:MM:SS']")
    sys.exit(1)

url = "https://api.dome9.com/v2/AssessmentHistoryV2/bundleResults"

bundle_id = sys.argv[1]
cloud_account_ids = sys.argv[2]
cloud_account_url = f"https://api.dome9.com/v2/AzureCloudAccount/{cloud_account_ids}"

# If from_time is provided, use it; otherwise, use the current time
if len(sys.argv) > 3:
    from_time_input = datetime.strptime(sys.argv[3], '%Y-%m-%d %H:%M:%S')
    from_time = from_time_input.strftime('%Y-%m-%dT%H:%M:%S.000Z')
else:
    from_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

epsilon_in_minutes = 120

username = os.getenv('DOME9_USERNAME')
password = os.getenv('DOME9_PASSWORD')

# Check that the necessary environment variables were set
if username is None or password is None:
    print("The DOME9_USERNAME and DOME9_PASSWORD environment variables must be set.")
    sys.exit(1)

credentials = f"{username}:{password}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

headers = {
    "accept": "application/json",
    "authorization": f"Basic {encoded_credentials}"
}

params = {
    "bundleId": bundle_id,
    "cloudAccountIds": cloud_account_ids,
    "fromTime": from_time,
    "epsilonInMinutes": epsilon_in_minutes
}

# Print the parameters used
print(f"Running script with the following parameters:\nBundle ID: {bundle_id}\nCloud Account IDs: {cloud_account_ids}\nFrom Time: {from_time}")

# Fetch assessment history
response = requests.get(url, headers=headers, params=params)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()

    # Fetch cloud account info
    cloud_response = requests.get(cloud_account_url, headers=headers)
    if cloud_response.status_code == 200:
        cloud_account_data = cloud_response.json()
        cloud_account_name = cloud_account_data.get('name', '')
        organizational_unit_name = cloud_account_data.get('organizationalUnitName', '')
    else:
        print(f"Cloud account request failed with status code: {cloud_response.status_code}")
        print(f"Response content: {cloud_response.text}")
        cloud_account_name = ''
        organizational_unit_name = ''

    # Flatten the tests into a single list
    all_tests = [test for test_group in data for test in test_group['tests']]

    # Convert the all_tests data into a Pandas DataFrame
    df = pd.json_normalize(all_tests)

    # Expand the nested data in the 'entityResults' column
    entityResults_df = pd.json_normalize(df['entityResults'].explode().dropna())
    df = df.drop(columns='entityResults')

    # Merge the dataframes
    df = pd.merge(df, entityResults_df, left_index=True, right_index=True, suffixes=('_original', '_entity'))

    # Extract part after the last '|' for 'Entity Name'
    df['testObj.dome9Id'] = df['testObj.dome9Id'].str.rsplit(pat='|', n=1).str[-1]

    # Create a new DataFrame and add columns from the original DataFrame
    new_df = pd.DataFrame()
    new_df['Organizational Unit Path'] = [organizational_unit_name]*len(df)
    new_df['Cloud Account ID'] = [cloud_account_ids]*len(df)
    new_df['Cloud Account Name'] = [cloud_account_name]*len(df)
    new_df['Bundle Name'] = [bundle_id]*len(df)
    new_df['Severity'] = df['rule.severity']
    new_df['Compliance Section'] = df['rule.complianceTag']
    new_df['Entity Type'] = df['testObj.entityType']
    new_df['Entity Name'] = df['testObj.dome9Id']
    new_df['Entity  ID'] = df['testObj.id']
    new_df['Rule Name'] = df['rule.name']
    new_df['Rule ID'] = df['rule.ruleId']
    new_df['Region'] = ''
    new_df['Network'] = df['testObj.dome9Id']
    new_df['Source'] = 'Compliance Engine'
    new_df['Created Time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_df['Description'] = df['rule.description']
    new_df['Remediation'] = df['rule.remediation']
    new_df['Cloud Account'] = ''
    new_df['Test Result'] = df['testPassed']
    new_df['Post Exclusion Result'] = ''

    # Write the DataFrame to an Excel file
    new_df.to_excel("all_tests.xlsx", index=False)

    print(f"Assessment results saved to 'all_tests.xlsx' successfully.")
else:
    print(f"Request failed with status code: {response.status_code}")
    print(f"Response content: {response.text}")

