import sys
import math
import requests
import pandas as pd
import numpy as np
from time import perf_counter, ctime
from tqdm import tqdm

cols=['Application', 'URL', 'Start Time', 'End Time', 'Duration']
# TODO: Only if _track_time is trus.
time_tracker_df = pd.DataFrame(columns=cols)

# Turn this off, if you do not need to track durations of each call.
_track_time = True

excel_file = r'.\App_CR_And_SCA_Info.xlsx'
# Sandbox
token = 'Basic Zy5wYWkrQ0FTVFNhbmRib3hQU0BjYXN0c29mdHdhcmUuY29tOmNhc3RATllDMjA='
domain_id = 9642
# MMC
#token = 'Basic Zy5wYWkrTU1DQGNhc3Rzb2Z0d2FyZS5jb206Y0A1dEhpZ2hMXw=='
#domain_id = 9210
# Wells - NKA
#token = 'Basic bi5rYXBsYW4rV2VsbHNGYXJnb0BjYXN0c29mdHdhcmUuY29tOm1kU2kyMHR5QDAy'
#domain_id = 1271
# NTRS
#token = 'Basic Zy5wYWkrTlRSU0BjYXN0c29mdHdhcmUuY29tOmNANXRIaWdoTF8='
#domain_id = 9455

head = {'Authorization': '{}'.format(token), 'Accept': 'application/json'}

total_apps = 0

def get_app_info():
    global time_tracker_df

    print('Retrieving App Info..')

    url = f'https://rpa.casthighlight.com/WS2/domains/{domain_id}/applications'

    if (_track_time):
        # Used for track elapsed duration, if enabled.
        start_dttm = ctime()
        start_tm = perf_counter()

    # TODO: Errorhandling
    resp = requests.get(url=url, headers=head)

    # Save the duration, if enabled.
    if (_track_time):
        end_tm = perf_counter()
        end_dttm = ctime()
        duration = end_tm - start_tm

        #print(f'Request completed in {duration} ms')
        time_tracker_df = time_tracker_df.append({'Application': 'ALL', 'URL': url, 'Start Time': start_dttm \
                                                    , 'End Time': end_dttm, 'Duration': duration}, ignore_index=True)

    resp_json = resp.json()
    main_df = pd.json_normalize(resp.json())

    #flat_table.normalize(main_df, expand_dicts=False, expand_lists=True)

    #print(main_df.columns)
    #main_df['metrics'] = [ [] if x is np.NaN else x for x in main_df['metrics'] ]
    #resp.json['metrics'] = [ [] if x is np.NaN else x for x in resp_json['metrics'] ]

    for i in resp_json:
        cont=i.get('contributors')
        metrics=i.get('metrics')

        if metrics:
            # Good here.
            pass
            #print(cont)
        else:
            #print('found a blank metric')
            i['metrics']={}
            #metrics=i.get('metrics')
            #print(metrics)

        if cont:
            # Good here.
            pass
            #print(cont)
        else:
            #print('found a blank contrib')
            i['contributors']={}
            cont=i.get('contributors')
            #print(cont)

    domains = pd.json_normalize(resp_json, 'domains', meta=['id'], record_prefix='domain_')
    domains.rename(columns={'domain_id':'Domain Id'}, inplace=True)
    domains.rename(columns={'domain_name':'Domain Name'}, inplace=True)
    #print(domains.head())

    # TODO: Contributor info needed?
    #contributors = pd.json_normalize(resp_json, 'contributors', meta=['id'], record_prefix='contributors_')
    #print(contributors.head())

    #metrics = pd.json_normalize(resp_json, 'metrics', meta=['id'], record_prefix='metrics_')
    metrics = pd.json_normalize(resp_json, 'metrics', meta=['id'])
    #metrics = pd.json_normalize(main_df['metrics'], 'metrics', meta=['id'])

    # Rename column names to make them more readable 
    metrics.rename(columns={'snapshotDate':'Snapshot Date'}, inplace=True)
    metrics.rename(columns={'softwareAgility':'Software Agility'}, inplace=True)
    metrics.rename(columns={'softwareElegance':'Software Elegance'}, inplace=True)
    metrics.rename(columns={'softwareResiliency':'Software Resiliency'}, inplace=True)
    metrics.rename(columns={'openSourceSafety':'Open Source Safety'}, inplace=True)
    metrics.rename(columns={'backFiredFP':'Back Fired FP'}, inplace=True)
    metrics.rename(columns={'technicalDebt':'Technical Debt'}, inplace=True)
    metrics.rename(columns={'maintenanceRecordedFTE':'Maintenance Recorded FTE'}, inplace=True)
    metrics.rename(columns={'maintenanceRecommendedFTE':'Maintenance Recommended FTE'}, inplace=True)
    metrics.rename(columns={'cloudReady':'Cloud Ready'}, inplace=True)
    metrics.rename(columns={'cloudReadyScan':'Cloud Ready Scan'}, inplace=True)
    metrics.rename(columns={'boosters':'Boosters'}, inplace=True)
    metrics.rename(columns={'blockers':'Blockers'}, inplace=True)
    metrics.rename(columns={'roadblocks':'Road Blocks'}, inplace=True)
    # Issue at NTRS
    #metrics.rename(columns={'cloudEffort':'Cloud Effort'}, inplace=True)
    metrics.rename(columns={'totalLinesOfCode':'Total Lines Of Code'}, inplace=True)
    metrics.rename(columns={'totalFiles':'Total Files'}, inplace=True)
    metrics.rename(columns={'businessImpact':'Business Impact'}, inplace=True)
    metrics.rename(columns={'roarIndex':'Roar Index'}, inplace=True)

    # Drop the columns Technologies and Vulnerabilites, as we do not need it at this time.
    del metrics['technologies']
    del metrics['vulnerabilities']

    # Rounding off/data adjustments
     
    metrics['Snapshot Datetime'] = pd.to_datetime(metrics['Snapshot Date'], unit='ms')
    metrics['Software Agility'] = round(metrics['Software Agility'] * 100, 2)
    metrics['Software Elegance'] = round(metrics['Software Elegance'] * 100, 2)
    metrics['Software Resiliency'] = round(metrics['Software Resiliency'] * 100, 2)
    metrics['Open Source Safety'] = round(metrics['Open Source Safety'] * 100, 2)
    metrics['Cloud Ready'] = round(metrics['Cloud Ready'] * 100, 2)
    metrics['Cloud Ready Scan'] = round(metrics['Cloud Ready Scan'] * 100, 2)
    metrics['Boosters'] = round(metrics['Boosters'] * 100, 2)
    metrics['Blockers'] = round(metrics['Blockers'] * 100, 2)
    # Issue at NTRS
    #metrics['Cloud Effort'] = round(metrics['Cloud Effort'] * 100, 2)
    metrics['Business Impact'] = round(metrics['Business Impact'] * 100, 2)
    metrics['Roar Index'] = round(metrics['Roar Index'] * 100, 2)

    #print(metrics.head())

    #merged_df = pd.merge(main_df, domains, how='inner',on='id')
    #print(merged_df)
    #merged_df = merged_df.drop(columns=['domains','contributors'])
    merged_df = main_df
    merged_df = merged_df.drop(columns=['domains', 'contributors', 'metrics'])

    # TODO: clientRef needed?
    merged_df = merged_df.drop(columns=['clientRef'])

    merged_df = pd.merge(merged_df, domains, how='inner', on='id')
    # TODO: Contributor info needed?
    #merged_df = pd.merge(merged_df, contributors, how='inner', on='id')
    merged_df = pd.merge(merged_df, metrics, how='inner',on='id')
    #print(merged_df.columns)

    merged_df.rename(columns={'id':'Application Id'}, inplace=True)
    merged_df.rename(columns={'name':'Application Name'}, inplace=True)
    merged_df.rename(columns={'snapshotLabel':'Snapshot Label'}, inplace=True)

    merged_df = merged_df[['Application Id','Application Name', 'Domain Id', 'Domain Name', 'Snapshot Label', 'Snapshot Datetime', \
                           'Snapshot Date', 'Software Agility', 'Software Elegance', 'Software Resiliency', \
                           'Open Source Safety', 'Back Fired FP', 'Technical Debt', 'Maintenance Recorded FTE', \
                            'Maintenance Recommended FTE', 'Cloud Ready', 'Cloud Ready Scan', 'Boosters', \
                            'Blockers', 'Road Blocks','cloudEffort', 'Total Lines Of Code', 'Total Files',\
                            'Business Impact', 'Roar Index']]

    print('Done.')
    return merged_df

def get_cloudready_info(app_df):
    global time_tracker_df

    cr_df = pd.DataFrame()
    app_cr_df = pd.DataFrame()

    print("\nRetrieving CloudReady info..")

    with tqdm(total=total_apps) as pbar:
        for index, row in app_df.iterrows():
            app_id = row['Application Id']
            app_name = row['Application Name']

            #print(f'Processing app:{app_id}/{app_name}')
            # Clear the dataframe.
            app_cr_df.iloc[0:0]

            url = f'https://rpa.casthighlight.com/WS2/domains/{domain_id}/applications/{app_id}'

            resp = {}

            if (_track_time):
                # Used for track elapsed duration, if enabled.
                start_dttm = ctime()
                start_tm = perf_counter()

            # TODO: Errorhandling
            resp = requests.get(url=url, headers=head)

            # Save the duration, if enabled.
            if (_track_time):
                end_tm = perf_counter()
                end_dttm = ctime()
                duration = end_tm - start_tm

                #print(f'Request completed in {duration} ms')
                time_tracker_df = time_tracker_df.append({'Application': app_name, 'URL': url, 'Start Time': start_dttm \
                                                        , 'End Time': end_dttm, 'Duration': duration}, ignore_index=True)

            response_json = resp.json()

            # Not all apps will have 'cloudReadyDetail' info.
            # So, in cases where it is not found, create a blank entry, so that 
            # json_normalize won't barf.

            try:
                data = response_json['metrics'][0]['cloudReadyDetail']
            except (KeyError):
                response_json['metrics'][0]['cloudReadyDetail'] = []

            app_cr_df = pd.json_normalize(response_json['metrics'][0], record_path=['cloudReadyDetail' \
                                    , 'cloudReadyDetails'], meta=['snapshotLabel', ['cloudReadyDetail','technology']])

            # Add application id and application name as 2 new columns in the df.
            app_cr_df.insert(0, 'Application Id', app_id)
            app_cr_df.insert(1, 'Application Name', app_name)

            # Add rule category and rule name, both come from the display column.

            #temp = app_cr_df['cloudRequirement.display'].str.split(":", n = 1, expand = True)

            #app_cr_df['Rule Category'] = temp[0]
            #app_cr_df['Rule'] = temp[1]

            # Drop the column as we no monger need it.
            #app_cr_df.drop(columns=['cloudRequirement.display'], inplace = True)

            # Append the data for the current application to the main dataframe, before processing
            # the CVE info for the next application.

            if (cr_df.empty and (not app_cr_df.empty)):
                cr_df = app_cr_df
            else:
                cr_df = cr_df.append(app_cr_df)

            #show progress made.
            pbar.update(1)

    # Update the progress bar (final)
    print('\nDone.')

    return cr_df

def get_sca_info(app_df):
    global time_tracker_df

    complete_sca_df = pd.DataFrame()
    cve_df = pd.DataFrame()

    print("\nRetrieving SCA info..")

    with tqdm(total=total_apps) as pbar:
        for index, row in app_df.iterrows():
            app_id = row['Application Id']
            app_name = row['Application Name']
            #print(f'Processing:{index}/App Id: {app_id}/App Name:{app_name}')

            # Clear the dataframe.
            cve_df.iloc[0:0]

            url = f'https://rpa.casthighlight.com/WS2/domains/{domain_id}/applications/{app_id}/thirdparty'

            resp = {}

            if (_track_time):
                # Used for track elapsed duration, if enabled.
                start_dttm = ctime()
                start_tm = perf_counter()

            # TODO: Errorhandling
            resp = requests.get(url=url, headers=head)

            # Save the duration, if enabled.
            if (_track_time):
                end_tm = perf_counter()
                end_dttm = ctime()
                duration = end_tm - start_tm

                #print(f'Request completed in {duration} ms')
                time_tracker_df = time_tracker_df.append({'Application': app_name, 'URL': url, 'Start Time': start_dttm \
                                                        , 'End Time': end_dttm, 'Duration': duration}, ignore_index=True)

            response_json = resp.json()

            # CVEs and vulnerabilities cannot be retrieved directly 'coz, if they don't exist, json_normalize fails with a 'KeyError'.
            # So, as a workaround, we insert blank entries for them, before invoking json_normalize().

            # TODO: Don't need two loop, maybe.

            try:
                data = response_json['thirdParties']
            except (KeyError):
                response_json['thirdParties'] = []

            for i in response_json['thirdParties']:
                cve = i.get('cve')

                if cve is None:
                    i['cve'] = {'vendor': '', 'product': '', 'version': '', 'vulnerabilities': [] }

            # Now we should be able to normalize without an issue.
            #cves = pd.json_normalize(response_json['thirdParties'], 'cve', record_prefix='cve_')
            #cves.head(90)

            #tpty_df = pd.json_normalize(response_json['thirdParties'])
            #tpty_df.head(20)

            # GOOD - DO NOT MODIFY
            # vul_df = pd.json_normalize(response_json['thirdParties'], record_path=['cve','vulnerabilities'], meta=['id', ['cve', 'vendor']], record_prefix='vulnerabilty_')
            ##############
            cve_df = pd.json_normalize(response_json['thirdParties'], record_path=['cve', 'vulnerabilities'], meta=['id', 'componentId', ['cve', 'vendor']])

            # TODO: Ignoring license information for now.
            # Retrieve license information.

            #licenses = pd.json_normalize(response_json['thirdParties'], 'licenses', meta=['id'], record_prefix='license_')

            # Add application id and application name as 2 new columns in the df.
            cve_df.insert(0, 'Application Id', app_id)
            cve_df.insert(1, 'Application Name', app_name)

            # Append the data for the current application to the main dataframe, before processing
            # the CVE info for the next application.

            if (complete_sca_df.empty and (not cve_df.empty)):
                complete_sca_df =  cve_df
            else:
                complete_sca_df = complete_sca_df.append(cve_df)

            #show progress made.
            pbar.update(1)

    print('\nDone.')

    return complete_sca_df

def adjust_sca_cols(sca_info_df):

    sca_info_df.rename(columns={'name':'CVE'}, inplace=True)
    sca_info_df.rename(columns={'link':'CVE Link'}, inplace=True)
    sca_info_df.rename(columns={'cweId':'CWE Id'}, inplace=True)
    sca_info_df.rename(columns={'cweLabel':'CWE Label'}, inplace=True)
    sca_info_df.rename(columns={'criticity':'Criticality'}, inplace=True)
    sca_info_df.rename(columns={'cpe':'CPE'}, inplace=True)
    sca_info_df.rename(columns={'id':'Id'}, inplace=True)
    sca_info_df.rename(columns={'componentId':'Component Name'}, inplace=True)
    sca_info_df.rename(columns={'cve.vendor':'Component Vendor'}, inplace=True)
    sca_info_df.rename(columns={'description':'Description'}, inplace=True)

    return

def adjust_cr_cols(cr_df):

    cr_df.rename(columns={'cloudReadyDetail.technology':'Technology'}, inplace=True)
    cr_df.rename(columns={'cloudRequirement.ruleType':'Rule Type'}, inplace=True)
    cr_df.rename(columns={'contributionScore':'Contribution Score'}, inplace=True)
    cr_df.rename(columns={'cloudEffort':'Effort'}, inplace=True)
    cr_df.rename(columns={'roadblocks':'Roadblocks'}, inplace=True)
    cr_df.rename(columns={'cloudRequirement.criticality':'Criticality'}, inplace=True)
    cr_df.rename(columns={'cloudRequirement.impacts':'Rule Impact'}, inplace=True)
    cr_df.rename(columns={'cloudRequirement.hrefDoc':'Doc Reference'}, inplace=True)

    temp = cr_df['cloudRequirement.display'].str.split(' : ', n = 1, expand = True)

    cr_df['Rule Category'] = temp[0]
    cr_df['Rule'] = temp[1]

    # Drop the column as we no monger need it.
    cr_df.drop(columns=['cloudRequirement.display'], inplace = True)

    return

def main():

    global total_apps

    app_info_df = pd.DataFrame()
    sca_info_df = pd.DataFrame()

    app_info_df = get_app_info()

    total_apps = len(app_info_df)

    print(f'Processing {total_apps} applications..')

    # TODO: Print stats - time taken, number of apps processed, etc.
    # Get Cloud Ready info for each app
    cloudready_info_df = get_cloudready_info(app_info_df)
    adjust_cr_cols(cloudready_info_df)

    # Reorder the columns based on their relevance.
    cloudready_info_df = cloudready_info_df[['Application Id','Application Name', 'Technology', 'Rule Type', \
                               'Contribution Score', 'Effort', 'Roadblocks', 'Criticality', 'Rule Impact',   \
                               'Rule Category', 'Rule', 'Doc Reference']]

    # Get SCA Info for each app
    sca_info_df = get_sca_info(app_info_df)
    adjust_sca_cols(sca_info_df)

    # Reorder the columns based on their relevance.
    sca_info_df = sca_info_df[['Application Id','Application Name', 'CWE Id', 'CWE Label',       \
                               'CVE', 'Criticality', 'CVE Link', 'CPE', 'Id', 'Component Name',  \
                               'Component Vendor', 'Description']]

    # TODO
    with pd.ExcelWriter(excel_file) as writer:
        app_info_df.to_excel(writer, index=False, sheet_name='Applications')
        cloudready_info_df.to_excel(writer, index=False, sheet_name='Cloud')
        sca_info_df.to_excel(writer, index=False, sheet_name='SCA')
        if (_track_time):
            time_tracker_df.to_excel(writer, index=False, sheet_name='Time Tracker')
    
    # TODO: Table formatting
    # see: https://xlsxwriter.readthedocs.io/working_with_pandas.html

if __name__ == "__main__":
    # TODO: Take arguments to get all data or specific ones.

    start_dttm = ctime()
    start_tm = perf_counter()

    print(f'Process started at:{start_dttm}')
    main()

    end_tm = perf_counter()
    end_dttm = ctime()
    duration = end_tm - start_tm
    print('Successfully completed.')
    print(f'Process ended at:{end_dttm}')

    sys.exit(0)
