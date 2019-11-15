# -*- coding: utf-8 -*-
"""Reads original NSE data, stored for a whole week as a csv, and extracts
each day's, then stores it into separate csv files.

History:
    Created on 8 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

from datetime import datetime
import pandas as pd
import os
import calendar


def extract_file_info(data_file):
    """Extract key date info from the csv file name.

    Args:
        data_file (str): Location of raw NSE week csv file.

    Return:
        file_info (dict): experiment date related info, including
            * file_path (str): path to the data file
            * start_str (str): starting name of output fiile
            * year (str): experiment year
            * month (str): month that experiment was run
            * day_range (list str): days over which the experiment ran
            * week (str): week in which experiment took place
    """
    month_conversion = {'january': '01',
                        'february': '02',
                        'march': '03',
                        'april': '04',
                        'may': '05',
                        'june': '06',
                        'july': '07',
                        'august': '08',
                        'september': '09',
                        'october': '10',
                        'november': '11',
                        'december': '12'}

    file_start = data_file.rfind('/')  # everything before is the path
    file_path = data_file[:file_start] + '/'
    file_name_info = data_file[file_start + 1:-4].split('_')  # ignore .csv ext

    start_str = file_name_info[0] + '_' + file_name_info[1]
    week_str = file_name_info[2]
    month_str = file_name_info[3]
    date_range_str = file_name_info[4]
    year_str = file_name_info[5]

    week = week_str[4:]
    month = month_conversion[month_str]

    date_start = int(date_range_str[:date_range_str.find('to')])
    date_end = int(date_range_str[date_range_str.find('to') + 2:])
    date_range_int = range(date_start, date_end + 1)
    date_range = [str(x).rjust(2, '0') for x in date_range_int]  # pad zeros

    file_info = {'file_path': file_path,
                 'start_str': start_str,
                 'year': year_str,
                 'month': month,
                 'day_range': date_range,
                 'week': week}

    return file_info


def generate_file_names(data_file, out_file_start=None, out_file_path=None):
    """Generate file names to store each day's records.
    Arg:
        data_file (str): Location of raw NSE week csv file.

    Kwarg:
        out_file_start (str): Output file name format of start of each day's
            csv file
        out_file_path (str): Location for the output csv file.

    Returns:
        doi (dict): Dictionary of days of interest and their output files.
    """

    file_info = extract_file_info(data_file)

    if out_file_start is None:
        out_file_start = file_info['start_str']

    if out_file_path is None:
        out_file_path = file_info['file_path']

    file_name_start = out_file_path + out_file_start

    analyses_days = []
    for d in file_info['day_range']:
        analyses_days.append('{0}-{1}-{2}'.format(file_info['year'],
                                                  file_info['month'],
                                                  d))
    doi = {}
    for d in analyses_days:
        date = datetime.strptime(d, '%Y-%m-%d')
        dow = calendar.day_name[date.weekday()][:3]
        doi[d] = '{0}_week{1}_{2}_{3}.csv'.format(file_name_start,
                                                  file_info['week'],
                                                  d.replace('-', '_'),
                                                  dow)

    return doi


def extract_records(data_file, dio, overwrite=False):

    """Stores records from data file into separate files for each day.

    Arg:
        doi (dict): Date and file locations where data will be written.

    Kwarg:
        overwrite (bool): Overwrite existing files with the same file name.
    """

    with open(data_file) as f:
        i = 1
        headings = f.readline()
        analysis_days = doi.keys()

        for d in analyses_days:
            if os.path.isfile(doi[d]) and not over_write:
                f.close()
                raise OSError('File `{0}` already exists and over write set to `{1}`'.format(doi[d], over_write))

            f_out = open(doi[d], 'w')
            f_out.write(headings)
            f_out.close()


if __name__ == "__main__":
    test_name = '../data/nse_original_data_by_week/nse_data_week3_may_16to22_2016.csv'
    out_file_path_test = '../data/nse_orginal_data_by_day/'
    f_names = generate_file_names(test_name, out_file_path=out_file_path_test)
    print(f_names)
    extract_records(test_name, f_names)