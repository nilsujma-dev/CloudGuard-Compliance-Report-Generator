# dome9-assessment-api
This is to request the latest Assessment Results from Dome9 and to write them into Excel File.
Before running this script, the following parameters need to be set as system environments:

DOME9_USERNAME
DOME9_PASSWORD

In addition you need to specify the bundleID and CloudAccountID while running the script. 
You can also adjust the time window for which the script is required to run. 
If no time parameter is set, the script will use the system time and will go back 120mins in time to gather all assessment results. 

Example Execution: 

python3 script.py 123456 123456-1234-1234-1234-123456789
OR with time specification
python3 script.py 123456 123456-1234-1234-1234-123456789 '2023-06-09 04:00:00'
