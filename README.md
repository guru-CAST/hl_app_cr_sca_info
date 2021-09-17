# hl_app_cr_sca_info
Python script to extract CAST Highlight (HL) information using HL REST API calls and generate the output as an MS-Excel file.

## Command-line arguments
The script accepts the following option arguments:
* -d Enable debug
* -c Extract CloudReady information
* -s Extract the CVE information from the SCA findings
* -m Extract the third-party component information from the SCA findings
* -b <batch_size> Split the output in smaller batches (number of apps). Default size: 5K
* -l <limit> Limit the output to X number of intial application - useful for running quick tests.

If arguments are not supplied, the script only generates application-level information. 

## Configuration Settings
Use the settings.cfg file to specify the additional settings, such as, the HL domain number and Base64 HL credentials.
## Logging
The script produces a log file for each run and it is written to the logs folder. Note that at this time, an existing log file will be overwritten.
## Output files
Results of the extract are saved to file/files named, <prefix> - HL_app_cr_sca_info_*.xlsx. Multiple files are created when the batch size is specified or when the number of applications exceed the default 5K limit. The files are saved in a folder named output. Existing files in the folder will be overwritten.
