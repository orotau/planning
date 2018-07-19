from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from datetime import datetime, date
import calendar
import pprint
import numpy as np
import y2018 # can't name a module 2018
import utils
from dateutil.rrule import rrule, DAILY
from itertools import compress, cycle, islice
import iso8601 #http://pyiso8601.readthedocs.io/en/latest/
import day_chunks

PERIOD_TEXT = "Period"

# Setup the Calendar API (Boiler Plate)
SCOPES = 'https://www.googleapis.com/auth/calendar' # read / write
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('calendar', 'v3', http=creds.authorize(Http()))

def create_new_calendar(term):
    '''
    creates a new blank calendar with the name
    Term 1 - 2018 (03 Mar-08:23)
    So that it (the name) will fit on the computer screen
    The date time is the creation date of the calendar
    returns name, id

    Despite documentation color seems to be set randomly (as at April 2018)
    '''

    year = 2018

    current_datetime = datetime.now()
    current_datetime_as_string = datetime.strftime(current_datetime, "%d %b-%H:%M")
    calendar_name = "Term "  + str(term) + " - " + str(year) + " (" + current_datetime_as_string + ")"

    calendar = {
        'summary': calendar_name,
        'timeZone': 'Pacific/Auckland',
    }

    created_calendar = service.calendars().insert(body=calendar).execute()

    return created_calendar["id"], created_calendar["summary"]

def get_teaching_dates_for_term(term):

    start_teaching_date = [x.dayte for x in y2018.teaching_dates if x.term == term][0] # as string
    start_teaching_date = datetime.strptime(start_teaching_date, '%A %d %B %Y')

    end_teaching_date = [x.dayte for x in y2018.teaching_dates if x.term == term][-1] # as string
    end_teaching_date = datetime.strptime(end_teaching_date, '%A %d %B %Y')

    all_dates = list(rrule(DAILY, dtstart=start_teaching_date, until=end_teaching_date))

    # as string
    non_teaching_dates = [x.dayte for x in y2018.non_teaching_dates if x.term == term]

    # as datetime object
    non_teaching_dates = [datetime.strptime(x, '%A %d %B %Y') for x in non_teaching_dates]

    teaching_dates_filter = np.is_busday(all_dates, holidays=non_teaching_dates)
    teaching_dates = list(compress(all_dates, teaching_dates_filter))
    teaching_dates = [x.date() for x in teaching_dates] # convert to dates from datetimes
    return teaching_dates

def get_teaching_dates_and_day_number(term):
    '''
    get teaching dates and day number for term
    '''
    teaching_dates_and_day_number = []
    teaching_dates = get_teaching_dates_for_term(term)

    start_day_number = [x.day_number for x in y2018.teaching_dates if x.term == term][0]
    day_numbers = cycle([1, 2, 3, 4, 5, 6]) 
    adjusted_day_numbers = islice(day_numbers, start_day_number - 1, None)
    for teaching_date in teaching_dates:
        day_number_to_use = next(adjusted_day_numbers)
        teaching_dates_and_day_number.append((teaching_date, day_number_to_use))
    return teaching_dates_and_day_number

def create_periods_for_term(term, new_calendar_id):
    teaching_dates_and_day_number = get_teaching_dates_and_day_number(term)
    for teaching_date, day_number in teaching_dates_and_day_number:
        weekday = teaching_date.weekday() # 0 = Monday
        day_of_week = calendar.day_name[weekday]

        for period in [1,2,3,4,5]:
            line_number = utils.get_line_for_period(day_number, period)
            summary_text = "Period " + str(period) + " " + chr(8211) + " " + "Line " + str(line_number)
            colorId = utils.get_color_for_line(line_number)
            start_time = [x.start for x in day_chunks.day_chunks if x.day == day_of_week and x.title.endswith(str(period))][0]
            end_time = [x.end for x in day_chunks.day_chunks if x.day == day_of_week and x.title.endswith(str(period))][0]
            print(start_time, end_time)

            date_to_use = datetime.strftime(teaching_date, '%Y-%m-%d')
            start_datetime = date_to_use + "T" + start_time
            end_datetime = date_to_use + "T" + end_time

            utils.create_event(summary_text, colorId, start_datetime, end_datetime, new_calendar_id, service)
    return True

def create_other_day_chunks_for_term(term, new_calendar_id):
    teaching_dates_and_day_number = get_teaching_dates_and_day_number(term)
    for teaching_date, day_number in teaching_dates_and_day_number:
        weekday = teaching_date.weekday() # 0 = Monday
        day_of_week = calendar.day_name[weekday]
        other_day_chunks = [x for x in day_chunks.day_chunks if x.day == day_of_week and "Period" not in x.title]
        for other_day_chunk in other_day_chunks:
            summary_text = other_day_chunk.title
            colorId = 8 # graphite
            start_time = other_day_chunk.start
            end_time = other_day_chunk.end
            print(start_time, end_time)

            date_to_use = datetime.strftime(teaching_date, '%Y-%m-%d')
            start_datetime = date_to_use + "T" + start_time
            end_datetime = date_to_use + "T" + end_time

            utils.create_event(summary_text, colorId, start_datetime, end_datetime, new_calendar_id, service)
    return True


def create_day_all_day_events_for_term(term, new_calendar_id):
    teaching_dates_and_day_number = get_teaching_dates_and_day_number(term)
    for teaching_date, day_number in teaching_dates_and_day_number:
        summary_text = "Day " + str(day_number)
        colorId = 1 # Lavender
        date_to_use = datetime.strftime(teaching_date, '%Y-%m-%d')
        utils.create_all_day_event(summary_text, colorId, date_to_use, new_calendar_id, service)


def create_other_all_day_events_for_term(term, new_calendar_id):

    non_teaching_dates_for_term = [x for x in y2018.non_teaching_dates if x.term == term]
    for non_teaching_date_for_term in non_teaching_dates_for_term:
        summary_text = non_teaching_date_for_term.title
        colorId = 1 # Lavender
        date_as_datetime = datetime.strptime(non_teaching_date_for_term.dayte, '%A %d %B %Y')
        date_to_use = datetime.strftime(date_as_datetime, '%Y-%m-%d')
        utils.create_all_day_event(summary_text, colorId, date_to_use, new_calendar_id, service)


def create_term_calendar(term):
    new_calendar = create_new_calendar(term)
    new_calendar_id = new_calendar[0]
    create_periods_for_term(term, new_calendar_id)
    create_other_day_chunks_for_term(term, new_calendar_id)
    create_day_all_day_events_for_term(term, new_calendar_id)
    create_other_all_day_events_for_term(term, new_calendar_id)

if __name__ == '__main__':

    import sys
    import argparse
    import ast
    import pprint

    # create the top-level parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # create the parser for the get_teaching_dates_for_term
    get_teaching_dates_for_term_parser = subparsers.add_parser('get_teaching_dates_for_term')
    get_teaching_dates_for_term_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    get_teaching_dates_for_term_parser.set_defaults(function = get_teaching_dates_for_term)

    # create the parser for the get_teaching_dates_and_day_number
    get_teaching_dates_and_day_number_parser = subparsers.add_parser('get_teaching_dates_and_day_number')
    get_teaching_dates_and_day_number_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    get_teaching_dates_and_day_number_parser.set_defaults(function = get_teaching_dates_and_day_number)

    # create the parser for the function create_new_calendar
    create_new_calendar_parser = subparsers.add_parser('create_new_calendar')
    create_new_calendar_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    create_new_calendar_parser.set_defaults(function = create_new_calendar)

    # create the parser for the create_periods_for_term
    create_periods_for_term_parser = subparsers.add_parser('create_periods_for_term')
    create_periods_for_term_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    create_periods_for_term_parser.add_argument('new_calendar_id')
    create_periods_for_term_parser.set_defaults(function = create_periods_for_term)

    # create the parser for the create_term_calendar
    create_term_calendar_parser = subparsers.add_parser('create_term_calendar')
    create_term_calendar_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    create_term_calendar_parser.set_defaults(function = create_term_calendar)


    # parse the arguments
    arguments = parser.parse_args()
    arguments = vars(arguments) #convert from Namespace to dict

    #attempt to extract and then remove the function entry
    try:
        function_to_call = arguments['function'] 
    except KeyError:
        print ("You need a function name. Please type -h to get help")
        sys.exit()
    else:
        #remove the function entry as we are only passing arguments
        del arguments['function']
    
    if arguments:
        #remove any entries that have a value of 'None'
        #We are *assuming* that these are optional
        #We are doing this because we want the function definition to define
        #the defaults (NOT the function call)
        arguments = { k : v for k,v in arguments.items() if v is not None }

        #alter any string 'True' or 'False' to bools
        arguments = { k : ast.literal_eval(v) if v in ['True','False'] else v 
                                              for k,v in arguments.items() }       

    result = function_to_call(**arguments) #note **arguments works fine for empty dict {}
   
    pprint.pprint(result)


