"""
Name: generate_app_CR_SCA_info.py

Author: Guru Pai/Nevin Kaplan

Date: Thu 05/24/2020 

Arguments:
1. -c - Generate CR information
2. -s - Generate SCA information
2. -t - Enable the time tracking functionality

NOTE:

Prerequisites:
See the README.md file for complete details.
"""
__version__ = 1.2

import sys
import math
import requests
import pandas as pd
import numpy as np
import argparse
import configparser
import logging
import requests
import pandas as pd
import numpy as np

from time import perf_counter, ctime
from numpy.core.multiarray import empty_like
from pandas.core.frame import DataFrame
from time import perf_counter, ctime
from requests import HTTPError, Timeout, ConnectionError, RequestException
from requests.api import options
from tqdm import tqdm

# Turn this off, if you do not need to track durations of each call
_track_time = True

# TODO: Only if _track_time is trus.
cols=['Application', 'URL', 'Start Time', 'End Time', 'Duration']
time_tracker_df = pd.DataFrame(columns=cols)

base_url, base64_token, excel_file, excel_file_prefix = '', '', '', ''
domain_id = 0

total_apps, app_limit = 0, 0
debug, run_cloud, run_oss, run_comp, run_timeline = False, False, False, False, False

proxies = {}
head = {'Authorization': '{}'.format(base64_token), 'Accept': 'application/json'}

def read_cfg():
    global base_url, proxy_url, proxies, base64_token, domain_id, excel_file, excel_file_prefix
    logger = logging.getLogger('read_cfg')
    logger.info('In read_cfg()')

    """
    Read setting from the settings.cfg file. 
    The file is expected to be in the current folder.
    """
    
    cfg = configparser.ConfigParser()
    file_found = cfg.read('settings.cfg')

    if not file_found:
        raise Exception('Configuation file settings.cfg, was not found. Aborting..')
    else:
        try:
            base_url = cfg['CAST_HL']['BASE_URL']
            proxy_url = cfg['CUSTOM']['PROXY_URL']
            base64_token = cfg['CUSTOM']['HL_BASE64_CREDS']
            domain_id = cfg['CUSTOM']['HL_DOMAIN_ID']
            excel_file = cfg['CUSTOM']['EXCEL_FILE']
            excel_file_prefix = cfg['CUSTOM']['FILE_PREFIX']
        except:
            raise Exception('An exception occurred while reading config file.. Aborting..')
        else:
            if base64_token == 'DFLTCreds' or domain_id == 'DFLT999':
                raise Exception('Base64 credential and/or HL domain id not correctly set. Update the settings in the config file and re-run. Aborting..')

    #Base64     : {base64_token}
            logger.debug(f"""
    Base URL   : {base_url}
    Proxy URL  : {proxy_url}
    Domain Id  : {domain_id}
    File Name  : {excel_file}
    File Prefix: {excel_file_prefix}
            """)

    logger.info('Leaving read_cfg()')
    return

def rest_call(url, header):
    logger = logging.getLogger('rest_call')
    logger.info('In rest_call()')

    global time_tracker_df

    start_dttm = ctime()
    start_tm = perf_counter()
    head = header
    head['Authorization'] = f'Basic {base64_token}'

    logger.debug(f'Processing URL: {url}')
    #logger.debug(head)
    logger.debug(proxies)

    try:
        resp = requests.get(url = url, headers = head, proxies = proxies, timeout = None)
        resp.raise_for_status()

        # Save the duration, if enabled.
        if (_track_time):
            end_tm = perf_counter()
            end_dttm = ctime()
            duration = end_tm - start_tm

            time_tracker_df = time_tracker_df.append({'Application': 'ALL', 'URL': url, 'Start Time': start_dttm \
                                                        , 'End Time': end_dttm, 'Duration': duration}, ignore_index=True)
    except ConnectionError as conn_err:
        logger.error(f'Connection exception: {conn_err}')
        raise
    except HTTPError as http_err:
        logger.error(f'HTTP exception: {http_err}')
        raise
    except Timeout as to_err:
        logger.error(f'Timeout exception: {to_err}')
        raise
    except RequestException as req_err:
        logger.error(f'Request exception: {req_err}')
        raise
    finally:
        logger.info('Leaving rest call()')

    # Return results, as there were no exceptions.
    if resp.status_code == requests.codes.ok:
        return len(resp.json()), resp.json()
    else: 
        # No results found.
        logging.info(f'No results foundi.')
        return 0, {}

def get_total_apps(domain_id):
    logger = logging.getLogger('get_total_apps')
    logger.info('In get_total_apps()')

    status = 0
    url = f'{base_url}/domains/{domain_id}/applications'

    try:
        (status, json) = rest_call(url, {'Accept': 'application/json'})
    except Exception as err:
        print(f'An exception occurred while retrieving total_apps. Cannot continue.. Error:{err}')
        logger.error(f'An exception occurred while retrieving total_apps. Cannot continue.. Error:{err}')
        raise
    else:
        logger.info(f'Found {len(json)} apps.')
        return len(json), json
    finally:
        logger.info('Leaving get_total_apps()')

def get_application_info(domain_id):
    logger = logging.getLogger('get_application_info')
    logger.info('In get_application_info()')

    app_info_df = pd.DataFrame()

    with tqdm(total = 7) as pbar:
        pbar.set_description("Processing Applications")

        (total_apps, apps) = get_total_apps(domain_id)

        if total_apps == 0:
            print('No apps found. Cannot continue..')
            logger.warning('No apps found. Cannot continue..')
            logger.info('Leaving get_application_info()')

            return app_info_df, total_apps

        pbar.update(1)
        application = pd.json_normalize(apps, meta=['id'])
        pbar.update(1)


        # If just the initial X apps were requested, keep just those many applications in the dataframe.
        if app_limit > 0:
            logger.info(f'Limiting to only {app_limit} apps, as requested!')
            # TODO: For some strange reason, head returns 2 fewer records.
            application = application.head(n = app_limit + 2) 

        for row in apps:
            if row.get('metrics') is None:
                row['metrics'] = []

            if row.get('domains') is None:
                row['domains'] = []

        metrics = pd.json_normalize(apps, 'metrics', meta=['id'], record_prefix='metrics.')
        domains = pd.json_normalize(apps, 'domains', meta=['id'], record_prefix='domain.')
        pbar.update(1)

        application = application.drop(columns=['domains','metrics'])
        drop_column(metrics,'metrics.vulnerabilities')
        drop_column(metrics,'metrics.customIndicators')
        drop_column(metrics,'metrics.technologies')

        pbar.update(1)

        app_info_df = domains.merge(application, left_on='id', right_on='id')
        app_info_df = application.merge(metrics, left_on='id', right_on='id')
        pbar.update(1)

        app_info_df.rename(columns={'domain.id':'Domain Id'}, inplace=True)
        app_info_df.rename(columns={'domain.name':'Domain Name'}, inplace=True)
        app_info_df.rename(columns={'id':'Application Id'}, inplace=True)
        app_info_df.rename(columns={'name':'Application Name'}, inplace=True)
        app_info_df.rename(columns={'contributors':'Application Contributors'}, inplace=True)
        app_info_df.rename(columns={'tags':'Applications Tags'}, inplace=True)
        app_info_df.rename(columns={'clientRef':'Reference Id'}, inplace=True)
        app_info_df.rename(columns={'metrics.snapshotLabel':'Snapshot Label'}, inplace=True)
        app_info_df.rename(columns={'metrics.snapshotDate':'Snapshot Date'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareAgility':'Software Agility'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareAgilityAdded':'Software Agility - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareElegance':'Software Elegance'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareEleganceAdded':'Software Elegance - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareResiliency':'Software Resiliency'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareResiliencyAdded':'Software Resiliency - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.maintenanceRecordedFTE':'Recorded FTE'}, inplace=True)
        app_info_df.rename(columns={'metrics.maintenanceRecommendedFTE':'Recommended FTE'}, inplace=True)
        app_info_df.rename(columns={'metrics.openSourceSafety':'Open Source Safety'}, inplace=True)
        app_info_df.rename(columns={'metrics.technicalDebt':'Technical Debt'}, inplace=True)
        app_info_df.rename(columns={'metrics.cloudReady':'Cloud Ready'}, inplace=True)
        app_info_df.rename(columns={'metrics.cloudReadyScan':'Cloud Ready Scan'}, inplace=True)
        app_info_df.rename(columns={'metrics.boosters':'Boosters'}, inplace=True)
        app_info_df.rename(columns={'metrics.roadblocks':'Roadblocks'}, inplace=True)
        app_info_df.rename(columns={'metrics.businessImpact':'Business Impact'}, inplace=True)
        app_info_df.rename(columns={'metrics.roarIndex':'Roar Index'}, inplace=True)
        app_info_df.rename(columns={'metrics.backFiredFP':'BFP'}, inplace=True)
        app_info_df.rename(columns={'metrics.backFiredFPAdded':'Backfired FP - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.cloudReadySurvey':'Cloud Ready Survey'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalLinesOfCode':'LOC'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalLinesOfCodeAdded':'Total LOC - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalLinesOfCodeModified':'Total LOC - Modified'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalFiles':'Total Files'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalFilesAdded':'Total Files - Added'}, inplace=True)
        app_info_df.rename(columns={'metrics.totalFilesModified':'Total Files - Modified'}, inplace=True)
        app_info_df.rename(columns={'metrics.technologies':'Technologies'}, inplace=True)
        app_info_df.rename(columns={'metrics.cloudReady':'CloudReady'}, inplace=True)
        app_info_df.rename(columns={'metrics.blockers':'Blockers'}, inplace=True)
        app_info_df.rename(columns={'metrics.vulnerabilities':'Vulnerabilities'}, inplace=True)
        app_info_df.rename(columns={'metrics.cloudEffort':'Cloud Effort'}, inplace=True)
        app_info_df.rename(columns={'metrics.softwareHealth':'Software Health'}, inplace=True)
        pbar.update(1)

        app_info_df['Snapshot Date'] = pd.to_datetime(app_info_df['Snapshot Date'], unit='ms')
        adjust_percent(app_info_df,'Software Health')
        adjust_percent(app_info_df,'Software Agility')
        adjust_percent(app_info_df,'Software Agility - Added')
        adjust_percent(app_info_df,'Software Elegance')
        adjust_percent(app_info_df,'Software Elegance - Added')
        adjust_percent(app_info_df,'Software Resiliency')
        adjust_percent(app_info_df,'Software Resiliency - Added')
        adjust_percent(app_info_df,'Open Source Safety')
        adjust_percent(app_info_df,'Cloud Ready')
        adjust_percent(app_info_df,'Cloud Ready Scan')
        adjust_percent(app_info_df,'Cloud Ready Survey')
        adjust_percent(app_info_df,'Boosters')
        adjust_percent(app_info_df,'Blockers')
        adjust_percent(app_info_df,'Cloud Effort')
        adjust_percent(app_info_df,'Business Impact')
        adjust_percent(app_info_df,'Roar Index')
        adjust_percent(app_info_df,'Open Source Safty')
        pbar.update(1)

        # Move the Software health column to position 7 (column #8)
        sw_health = app_info_df.pop('Software Health')
        app_info_df.insert(7, 'Software Health', sw_health)

        logger.info('Leaving get_application_info()')
        return app_info_df, total_apps

def get_cloudready_info(app_info_df):
    logger = logging.getLogger('get_cloudread_info')
    logger.info('In get_cloudread_info()')

    global time_tracker_df

    cloudready_info_df = pd.DataFrame()

    loc = app_info_df[app_info_df['LOC'] > 0]
    loc = loc[(loc['Roadblocks']>0) | (loc['Boosters']>0) ]
    
    total_apps = len(loc)

    with tqdm(total=total_apps) as pbar:
        pbar.set_description("Processing CloudReady information")

        for index, row in loc.iterrows():
            pbar.update(1)
            app_id = row['Application Id']
            app_name = row['Application Name']

            url = f'https://rpa.casthighlight.com/WS2/domains/{domain_id}/applications/{app_id}'
            (status, json) = rest_call(url, {'Accept': 'application/json'})

            try:
                data = json['metrics'][0]['cloudReadyDetail']
            except (KeyError):
                json['metrics'][0]['cloudReadyDetail'] = []

            app_cr_df = pd.json_normalize(json['metrics'][0], record_path=['cloudReadyDetail' \
                                    , 'cloudReadyDetails'], meta=['snapshotLabel', ['cloudReadyDetail','technology']])

            # Add application id and application name as 2 new columns in the df.
            app_cr_df.insert(0, 'Application Id', app_id)
            app_cr_df.insert(1, 'Application Name', app_name)

            if (cloudready_info_df.empty and (not app_cr_df.empty)):
                cloudready_info_df = app_cr_df
            else:
                cloudready_info_df = cloudready_info_df.append(app_cr_df)

        # take care of the column names
        cloudready_info_df.rename(columns={'contributionScore':'Contrib Score'}, inplace=True)
        cloudready_info_df.rename(columns={'roadblocks':'Roadblocks'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudEffort':'Effort'}, inplace=True)
        cloudready_info_df.rename(columns={'files':'Files'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudReadyDetail.technology':'Technology'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudRequirement.ruleType':'Rule Type'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudRequirement.criticality':'Criticality'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudRequirement.impacts':'Rule Impact'}, inplace=True)
        cloudready_info_df.rename(columns={'rulePlatform':'Rule Platform'}, inplace=True)
        #cloudready_info_df.rename(columns={'cloudRequirement.hrefDoc':'Doc Reference'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudRequirement.rulePlatform':'Rule Platform'}, inplace=True)
        cloudready_info_df.rename(columns={'cloudRequirement.display':'Rule'}, inplace=True)

        #formatting
        adjust_percent(cloudready_info_df,'Contrib Score')

        drop_column(cloudready_info_df,'cloudRequirement.parent')
        drop_column(cloudready_info_df,'triggered')

        cloudready_info_df = cloudready_info_df[['Application Id','Application Name', 'Technology', 'Rule Type', \
                                    'Contrib Score', 'Effort','Files', 'Roadblocks', 'Criticality', \
                                    'Rule Impact', 'Rule']]
                                    #'Rule Impact', 'Rule', 'Doc Reference']]

        logger.info('Leaving get_cloudread_info()')

        return cloudready_info_df

def adjust_percent(df, name):
    if df.get(name) is not None:
        df[name] = round(df[name] * 100, 2)

def drop_column(df, name):
    if df.get(name) is not None:
        del df[name]

def get_sca_info(app_id, app_name):
    """
    This call handles both CVE (components with CVEs) and component (all third party components) request, based on
    the arguments that were supplied during program invocation.
    """
    logger = logging.getLogger('get_sca_info')
    logger.info('In get_sca_info()')

    global time_tracker_df

    cve_df, third_df = pd.DataFrame(), pd.DataFrame()

    #with tqdm(total=total_apps) as pbar:
        #pbar.set_description("Processing SCA information")
        #for index, row in app_df.iterrows():
            #app_id = row['Appl Id']
            #app_name = row['Appl Name']
            #print(f'Processing:{index}/App Id: {app_id}/App Name:{app_name}')

    url = f'{base_url}/domains/{domain_id}/applications/{app_id}/thirdparty'

    if (_track_time):
        # Used for track elapsed duration, if enabled.
        start_dttm = ctime()
        start_tm = perf_counter()

    try:
        (status, json) = rest_call(url, {'Accept': 'application/json'})
    except Exception as err:
        print(f'An exception occurred while retrieving SCA information. Cannot continue.. Error:{err}')
        logger.error(f'An exception occurred while retirieving SCA info. Cannot continue. Error{err}')
        raise

    # Save the duration, if enabled.
    if (_track_time):
        end_tm = perf_counter()
        end_dttm = ctime()
        duration = end_tm - start_tm

        #print(f'Request completed in {duration} ms')
        time_tracker_df = time_tracker_df.append({'Application': app_name, 'URL': url, 'Start Time': start_dttm \
                                                , 'End Time': end_dttm, 'Duration': duration}, ignore_index=True)

    response_json = json
 
    # CVEs and vulnerabilities cannot be retrieved directly 'coz, if they don't exist, json_normalize fails with a 'KeyError'.
    # So, as a workaround, we insert blank entries for them, before invoking json_normalize().

    try:
        data = response_json['thirdParties']
    except (KeyError):
        response_json['thirdParties'] = []

    if (run_comp):
        logger.debug('Processing component info.')
        third_df = pd.json_normalize(response_json['thirdParties'])

        col = third_df.columns

        if (len(col) > 0):
            third_df = third_df[['origin', 'name', 'languages', 'version', 'release', 'lastVersion', 'lastRelease', 'nbVersionPreviousYear']]

            third_df.rename(columns={'name':'Third-Party Component'}, inplace=True)
            third_df.rename(columns={'origin':'Origin'}, inplace=True)
            third_df.rename(columns={'languages':'Technologies'}, inplace=True)
            third_df.rename(columns={'version':'Version'}, inplace=True)
            third_df.rename(columns={'release':'Release Date'}, inplace=True)
            third_df.rename(columns={'lastVersion':'Latest Version'}, inplace=True)
            third_df.rename(columns={'lastRelease':'Latest Release Date'}, inplace=True)
            third_df.rename(columns={'nbVersionPreviousYear':'Releases / 12 months'}, inplace=True)

            third_df['Release Date'] = pd.to_datetime(third_df['Release Date'], unit ='ms')
            third_df['Release Date'] = pd.to_datetime(third_df['Release Date']).dt.date
            third_df['Latest Release Date'] = pd.to_datetime(third_df['Latest Release Date'], unit ='ms')
            third_df['Latest Release Date'] = pd.to_datetime(third_df['Latest Release Date']).dt.date

            third_df.insert(0, 'Application Name', app_name)
            third_df.insert(7, 'Gap In Years', 99)
            third_df['diff_days'] = third_df['Latest Release Date'] - third_df['Release Date'] 
            third_df['Gap In Years'] = third_df['diff_days'] / np.timedelta64(1, 'Y')

            third_df.drop(columns=['diff_days'], inplace = True)

        #show progress made.
        #pbar2.update(1)

    # If CVEs were requested, process and return that data.

    if (run_oss):
        # This loop ensures that the call to the json_normalize function below works without an issue
        # as the REST API does not CVE info when there aren't any, causing the json_normalize funtion to fail.

        for i in response_json['thirdParties']:
            cve = i.get('cve')

            if cve is None:
                i['cve'] = {'vendor': '', 'product': '', 'version': '', 'vulnerabilities': [] }

        cve_df = pd.json_normalize(response_json['thirdParties'], record_path=['cve', 'vulnerabilities'], meta=['id', 'componentId', ['cve', 'vendor']])

        # TODO: Ignoring license information for now.
        # Retrieve license information.

        #licenses = pd.json_normalize(response_json['thirdParties'], 'licenses', meta=['id'], record_prefix='license_')

        # Add application id and application name as 2 new columns in the df.
        cve_df.insert(0, 'Application Id', app_id)
        cve_df.insert(1, 'Application Name', app_name)

        #show progress made.
        #pbar1.update(1)

    logger.info('Leaving get_sca_info()')
    return cve_df, third_df

def adjust_sca_cols(cve_info_df):

    cve_info_df.rename(columns={'name':'CVE'}, inplace=True)
    cve_info_df.rename(columns={'link':'CVE Link'}, inplace=True)
    cve_info_df.rename(columns={'cweId':'CWE Id'}, inplace=True)
    cve_info_df.rename(columns={'cweLabel':'CWE Label'}, inplace=True)
    cve_info_df.rename(columns={'criticity':'Criticality'}, inplace=True)
    cve_info_df.rename(columns={'cpe':'CPE'}, inplace=True)
    cve_info_df.rename(columns={'id':'Id'}, inplace=True)
    cve_info_df.rename(columns={'componentId':'Component Name'}, inplace=True)
    cve_info_df.rename(columns={'cve.vendor':'Component Vendor'}, inplace=True)
    cve_info_df.rename(columns={'description':'Description'}, inplace=True)

    return
"""
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
"""

def get_timeline_info(sca_info_df):
    """
    This function is not yet ready from prime time.
    """
    global time_tracker_df

    timeline_info_df = pd.DataFrame()
    comp_timeline_df = pd.DataFrame()
    # For storing component ids for timeline retrieval
    comp_id_df = pd.DataFrame(sca_info_df, columns = ['id'])

    # Drop all duplicate component ids
    comp_id_df.drop_duplicates()

    with tqdm(total = len(comp_id_df)) as pbar:
        pbar.set_description("Retrieveing timeline info")

        for index, comp in comp_id_df.iterrows():
            comp_id = comp['id']
            #print(f'Processing:{index}/Comp Id: {comp_id}')

            # Clear the dataframe.
            comp_timeline_df = comp_timeline_df.iloc[0:0]

            url = f'{base_url}/domains/{domain_id}/components/{comp_id}/timeline'
            print(f'Timeline URL:{url}')

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

            # Version information may not always exist.

            try:
                data = response_json['versions']
            except (KeyError):
                response_json['versions'] = []

            for i in response_json['versions']:
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

            if debug_WF and index > 5:
                break

#    print('\nDone.')

    return timeline_info_df

def create_excel(excel_file_name, app_info_df, cloudready_info_df, cve_info_df, comp_info_df):
    logger = logging.getLogger('create_excel')
    logger.info('In create_excel()')

    writer = pd.ExcelWriter(f'output\\{excel_file_name}', engine='xlsxwriter')
    workbook = writer.book

    # format_decimal = workbook.add_format( {'num_format':'(#,##0.00)','align':'right'} )
    # format_number = workbook.add_format( {'num_format':'(#,##0)','align':'right'} )

    apps = format_table(writer, app_info_df, 'Applications')
    
    logger.info('Creating Excel file.')
    logger.debug(f'DF lengths:CR:{len(cloudready_info_df)}/CVE:{len(cve_info_df)}/Component:{len(comp_info_df)}.')

    if (run_cloud and len(cloudready_info_df)):
        logger.debug('Writing CR info to Excel')
        format_table(writer, cloudready_info_df, 'CloudReady')

    if (run_oss and len(cve_info_df)):
        logger.debug('Writing CVE info to Excel')
        format_table(writer, cve_info_df, 'CVEs')
    
    if (run_comp and len(comp_info_df)):
        logger.debug('Writing Component info to Excel')
        format_table(writer, comp_info_df, 'Components')
    
    if (_track_time):
        format_table(writer, time_tracker_df, 'Time Tracker')

    writer.save()

    logger.info('Excel file created.')
    logger.info('Leaving create_excel()')

    return

def format_table(writer, data, sheet_name ):
    data.to_excel(writer, index=False, sheet_name=sheet_name, startrow=1,header=False)

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    rows = len(data)
    cols = len(data.columns)
    columns=[]

    for col_num, value in enumerate(data.columns.values):
        columns.append({'header': value})

    table_options = {
        'columns': columns,
        'header_row': True,
        'autofilter': True,
        'banded_rows': True
    }
    worksheet.add_table(0, 0, rows, cols,table_options)
    
    header_format = workbook.add_format({'text_wrap':True,
                                         'align': 'center'})

    for col_num, value in enumerate(data.columns.values):
        worksheet.write(0, col_num, value, header_format)
        col_width = min(max_word_size(value),100)+4
        worksheet.set_column(col_num, col_num, col_width)
    
    return worksheet

def max_word_size(mystring):
    size = 0
    for word in mystring.split():
        size = max(len(word),size)
    return size

def main():
    global total_apps

    logger = logging.getLogger(__name__)
    logger.info('In main()')

    app_info_df = pd.DataFrame()
    cloudready_info_df = pd.DataFrame()
    cve_info_df = pd.DataFrame()
    comp_info_df = pd.DataFrame()
    timeline_info_df = pd.DataFrame()

    (app_info_df, total_apps) = get_application_info(domain_id)

    print(f'Total applications: {total_apps}')

    if total_apps > 0:
        # Retrieve Cloud Ready info for each app
        if (run_cloud):
            cloudready_info_df = get_cloudready_info(app_info_df)

        if run_comp or run_oss:
            cve_df = pd.DataFrame()
            comp_df = pd.DataFrame()

            if run_oss:
                print("Processing CVE information..")
                #with tqdm(total = total_apps) as pbar1:
                    #pbar1.set_description("Processing CVE information")

            if run_comp:
                print("Processing component information..")
                #with tqdm(total = total_apps) as pbar2:
                #    pbar2.set_description("Processing component information")

            for index, row in app_info_df.iterrows():
                app_id = row['Application Id']
                app_name = row['Application Name']

                logger.info(f'Processing CVE/component info for app:{app_id}/{app_name}')

                cve_df = cve_df.iloc[0:0]
                comp_df = comp_df.iloc[0:0]

                cve_df, comp_df = get_sca_info(app_id, app_name)

                if run_oss:
                    adjust_sca_cols(cve_df)
                    cve_info_df = cve_info_df.append(cve_df)

                if run_comp:
                    comp_info_df = comp_info_df.append(comp_df)

                # Handle the batch size here, if specified. The default size is 5K.
                if ((index + 1) % batch_size == 0):
                    if run_oss:
                        # Reorder the columns based on their relevance.
                        cve_info_df = cve_info_df[['Application Id','Application Name', 'CWE Id', 'CWE Label', 'CVE', 'Criticality', \
                                                   'CVE Link', 'CPE', 'Id', 'Component Name', 'Component Vendor', 'Description']]

                    logger.info(f'Ready to create Excel file.')
                    new_excel_file = excel_file_prefix + excel_file.replace('.xlsx', f'_{index + 1}.xlsx')
                    # TODO:
                    # NOTE: At this time, the CR info and app info are not saved in batches. This will be addressed in the future.
                    create_excel(new_excel_file, app_info_df, cloudready_info_df, cve_info_df, comp_info_df)
                    # Clear the DF to prevent values from repeating in the next batch.
                    cve_info_df = cve_info_df.iloc[0:0]
                    comp_info_df = comp_info_df.iloc[0:0]

        # Generate the Excel report for the remaining data.

        if run_oss:
            # Reorder the columns based on their relevance.
            cve_info_df = cve_info_df[['Application Id','Application Name', 'CWE Id', 'CWE Label', 'CVE', 'Criticality', \
                                        'CVE Link', 'CPE', 'Id', 'Component Name', 'Component Vendor', 'Description']]

        logger.info(f'Ready to create Excel file.')
        new_excel_file = excel_file_prefix + excel_file
        create_excel(new_excel_file, app_info_df, cloudready_info_df, cve_info_df, comp_info_df)
        logger.info('Leaving main()')
    else:
        print('Did not find any applications.. Cannot proceed.')
        logger.error('Did not find any application.. Cannot proceed.')
        logger.info('Leaving main()')
        return False
    
    # TODO: Table formatting

    return True

if __name__ == "__main__":

    # TODO:
    # If the logs folder does not exist, create it.
    # If the output folder does not exist, create it.

    logger = logging.getLogger('generate_app_CR_SCA_info')
    logging.basicConfig(filename = '.\\logs\\hl_app_cr_sca_info.log', filemode = 'w', format='%(asctime)s - %(name)s:%(levelname)s: %(message)s', level = logging.DEBUG)

    start_dttm = ctime()
    start_tm = perf_counter()

    print(f'Process started at:{start_dttm}')
    logger.info(f'Process starting..')

    # Process the args.
    parser = argparse.ArgumentParser()

    logger.info(f'Processing arguments')
    parser.add_argument('-b', '--bat', type = int, dest = 'bat_size', default = 5000, help = 'Group information in batches of "" apps')
    parser.add_argument('-c', '--cr', dest='run_cloud', action='store_true', help='Retrieve Cloud Ready data')
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Enable debugging info display')
    parser.add_argument('-m', '--comp', dest='run_comp', action='store_true', help='Retrieve full component information (no CVEs)')
    parser.add_argument('-s', '--sca', dest='run_oss', action='store_true', help='Retrieve Open-source CVE data')
    parser.add_argument('-l', '--limit', type = int, dest='app_limit', default = 0, help='Limit the number of apps to retrieve')
    # TODO:
    #parser.add_argument('-t', '--time', dest='run_timeline', action='store_true', help='Enable component timeline information retrieval')

    args = parser.parse_args()

    batch_size = args.bat_size
    debug = args.debug
    run_cloud = args.run_cloud
    run_oss = args.run_oss
    run_comp = args.run_comp
    app_limit = args.app_limit
    #run_timeline = args.run_timeline

    logger.debug(f"""
    Arguments passed:
    Batch Size: {batch_size}
    Enable Debug: {debug}
    Retrieve CR Info: {run_cloud}
    Retrieve CVE Info: {run_oss}
    Retrieve Component Info: {run_comp}
    App limit: {app_limit}
    """)
    #Store Timeline Info: {run_timeline}

    if app_limit > 0:
        logger.info(f'Limiting extract to {app_limit} apps.')

    try:
        read_cfg()
    except Exception as ex:
        print(f'ERROR: {ex}')
        logger.error(f'{ex}')
    else:
        # Adjust proxy settings basaed on the URL
        if "https:" in proxy_url:
            proxies = {'https': proxy_url}
        else:
            proxies = {'http': proxy_url}

        # If no file prefix was provided, blank out the default prefix.
        if excel_file_prefix == 'DFLT':
            excel_file_prefix = ''
        else:
            excel_file_prefix += ' - '

        if main() == True:
            print('Successfully completed.')
            logger.info('Successfully completed.')
        else:
            print('An error occrred during processing.')
            logger.error('An error occrred during processing.')

    end_tm = perf_counter()
    end_dttm = ctime()
    duration = end_tm - start_tm

    print(f'Process ended at:{end_dttm}')
    logger.info(f'Process stopping.')

    logging.shutdown()
    sys.exit(0)