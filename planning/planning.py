from __future__ import print_function

from apiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools
import pprint
import collections
import more_itertools
from datetime import datetime
import iso8601 #http://pyiso8601.readthedocs.io/en/latest/

MATHS = "Maths"
TOPIC = "Topic"

doc_title = collections.namedtuple("doc_title", "year term week subject")


SCOPES = (
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar.readonly',
)

# storage.json gets created when you run authorise.py
store = file.Storage('storage.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
DRIVE = discovery.build('drive', 'v3', http=creds.authorize(Http()))
CALENDAR = discovery.build('calendar', 'v3', http=creds.authorize(Http()))

TOPIC_FOLDER_ID = "1_IHOrfJsm9bNOrEkzIKsXQcBf5utVUfp" # term 3 2018


def get_calendar_id(term, year):
    calendars = []
    page_token = None
    while True:
        google_calendars = CALENDAR.calendarList().list(pageToken=page_token).execute()
        # returns a dict with four keys, very unlikely that we will need to go back again to the server
        # because we won't have that many calendars, but just in case.

        calendars.extend(google_calendars['items']) # create a list of dicts, 1 dict for each calendar

        page_token = google_calendars.get('nextPageToken')
        if not page_token:
            break

    for calendar in calendars:
        calendar_title = calendar['summary']
        # the assumption is that the 6th character will be the term .... 'Term X'
        # and the last 4 characters will be the year.
        if calendar_title[5] == str(term) and calendar_title.endswith(str(year)):
            return calendar['id']

    # no calendar has been found
    return None

def get_events_for_calendar(calendar_id):
    events = []
    page_token = None
    while True:
        google_events = CALENDAR.events().list(calendarId=calendar_id, pageToken=page_token).execute()

        events.extend(google_events['items'])
        page_token = google_events.get('nextPageToken')
        if not page_token:
            break

    return events

def get_documents_data(term, year, subject, calendar_events):
    '''
    We will return a dictionary with key = the named tuple ("doc_title", "year term week subject")
    and data = a list of the the tuples (event_date, event summary)
    if there is no lesson on a dayte then both period and lesson_number will be set to 0
    '''
    documents_data = {}
    subject_keys = []

    all_day_events = [x for x in calendar_events if 'date' in x['start'] and 'date' in x['end'] and x['start']['date'] == x['end']['date']]
    # sort them in ascending order (to allow the week to be found)
    all_day_events = sorted(all_day_events, key=lambda k: k['start']['date'])

    line4_events = [x for x in calendar_events if x['summary'] and x['summary'].endswith("Line 4")]
    line5_events = [x for x in calendar_events if x['summary'] and x['summary'].endswith("Line 5")]

    # we are assuming Maths is Line 4 and Topic is Line 5
    if subject == MATHS:
        events_to_use = line4_events
    if subject == TOPIC:
        events_to_use = line5_events

    #We are assuming that the term starts on a Monday here (Not ok for term 1)
    assert datetime.strptime(all_day_events[0]['start']['date'], '%Y-%m-%d').weekday() == 0 #Monday

    for counter, weeks_all_day_events in enumerate(more_itertools.chunked(all_day_events, 5)):
        # each week
        subject_keys.append(doc_title(year, "Term " + str(term), "Week " + '{:02}'.format(counter + 1), subject))
        periods_for_week = []
        for all_day_event in weeks_all_day_events:
            # each day of the week
            for event in events_to_use:
                event_date = iso8601.parse_date(event['start']['dateTime']).date()
                all_day_event_date = datetime.strptime(all_day_event['start']['date'], '%Y-%m-%d').date()
                if event_date == all_day_event_date:                    
                    periods_for_week.append((event_date, event['summary']))
        documents_data[subject_keys[counter]] = periods_for_week
    return(documents_data)
        

def get_files():
    files = DRIVE.files().list().execute().get('files', [])
    pprint.pprint(files)
    '''
    for f in files:
        pprint.pprint(f['name'], f['mimeType'])
    '''

def create_planning_skeletons(term, year):
    calendar_id = get_calendar_id(term, year)
    calendar_events = get_events_for_calendar(calendar_id)
    documents_data_maths = get_documents_data(term, year, MATHS, calendar_events)
    documents_data_topic = get_documents_data(term, year, TOPIC, calendar_events)
    for k, v in documents_data_maths.items():
        print(k, v)
    return(documents_data_maths)

    

if __name__ == '__main__':

    import sys
    import argparse
    import ast
    import pprint

    # create the top-level parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # create the parser for get_calendar_id
    get_calendar_id_parser = subparsers.add_parser('get_calendar_id')
    get_calendar_id_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    get_calendar_id_parser.add_argument('year', type=int)
    get_calendar_id_parser.set_defaults(function = get_calendar_id)

    # create the parser for get_events_for_calendar
    get_events_for_calendar_parser = subparsers.add_parser('get_events_for_calendar')
    get_events_for_calendar_parser.add_argument('id')
    get_events_for_calendar_parser.set_defaults(function = get_events_for_calendar)

    # create the parser for create_planning_skeletons
    create_planning_skeletons_parser = subparsers.add_parser('create_planning_skeletons')
    create_planning_skeletons_parser.add_argument('term', type=int, choices = [1, 2, 3, 4])
    create_planning_skeletons_parser.add_argument('year', type=int)
    create_planning_skeletons_parser.set_defaults(function = create_planning_skeletons)

    # create the parser for the get_files
    get_files_parser = subparsers.add_parser('get_files')
    get_files_parser.set_defaults(function = get_files)

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
    print(len(result))

