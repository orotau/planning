from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from datetime import datetime, date
import calendar
import pprint
from itertools import compress, cycle, islice


# Setup the Calendar API (Boiler Plate)
SCOPES = 'https://www.googleapis.com/auth/calendar' # read / write
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('calendar', 'v3', http=creds.authorize(Http()))

def get_calendars():
    page_token = None
    calendars =[]
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token, showHidden=True).execute()
        for calendar_list_entry in calendar_list['items']:
            calendars.append(calendar_list_entry)
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return calendars


if __name__ == '__main__':

    import sys
    import argparse
    import ast
    import pprint

    # create the top-level parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # create the parser for the get_calendars
    get_calendars_parser = subparsers.add_parser('get_calendars')
    get_calendars_parser.set_defaults(function = get_calendars)

    '''
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
    '''

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


