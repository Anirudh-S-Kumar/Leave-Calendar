from __future__ import print_function

import os.path
import logging
import base64
import email
import html
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from pprint import pprint
from ast import literal_eval
from datetime import datetime, timedelta, date
from logging.handlers import TimedRotatingFileHandler

# logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    'logs/caledarCreation.log', when='W6', interval=4, backupCount=30)
handler.suffix = '%Y-%m-%d'
logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


# If modifying these scopes, delete the file token.json.
SCOPES: str = ['https://www.googleapis.com/auth/gmail.readonly',]
#               'https://www.googleapis.com/auth/gmail.labels', 'https://www.googleapis.com/auth/gmail.modify']
SENDER_EMAIL: str = "admin-leave@iiitd.ac.in"
REQD_LABEL: str = "leave-approvals"
REQD_TEXT: str = "has been approved by Dofa"
TIME: int = 1
REMOVE_TAGS = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

# generating query based on log file
# trying to get the last date of the last email processed
try:
    with open("last_run.txt", "r") as f:
        TIME = int(f.read())
except FileNotFoundError or ValueError:
    TIME = 1

QUERY: str = f'from:{SENDER_EMAIL} label:{REQD_LABEL} after:{TIME} "{REQD_TEXT}"'

gmail = None
labels = {}


def quote_text(text):
    """For a given string, return the text inside single quotes.
    For example, for the string "Hello 'World'", return "World".
    """
    for i in range(len(text)):
        if text[i] == "'":
            for j in range(i+1, len(text)):
                if text[j] == "'":
                    return text[i+1:j]
            return None


def init():
    """Initializez the client library."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        gmail = build('gmail', 'v1', credentials=creds)
    except HttpError as error:
        logger.error(f'An error occurred: {error}')

    logger.info("Service created")
    return gmail


def getMessages(service):
    """Returns ID of emails to be processed.
    """
    # Call the Gmail API to only get emails from a specific sender
    results = service.users().messages().list(userId='me', q=QUERY).execute()
    messages = results.get('messages', [])
    rval: list[str] = []
    if messages:
        for message in messages:
            msg = service.users().messages().get(
                userId='me', id=message['id']).execute()
            temp = (msg.get('payload').get('body').get('data'))
            text = (base64.urlsafe_b64decode(temp))

            text = text.replace(b'<br />', b"\n").decode('utf-8')
            text = (re.sub(REMOVE_TAGS, '', text))            
            rval.append(text)
            logger.info(f"Message with ID {message['id']} added to list")

        return rval
    else:
        logger.info('No messages found.')


def getEventDetails(service, msg_list):
    """Takes message IDs, processes the text and returns a list of events.
    """
    rval: list[dict] = []

    messages: list[str] = msg_list
    # Process the text
    messages = [i.split('\n') for i in messages]
    messages = [[j for j in i if j] for i in messages]
    # Get the event details
    for i in messages:
        event: dict = {}
        event['name'] = quote_text(i[2])
        event['category'] = quote_text(i[3])
        event['start'] = quote_text(i[4])
        event['end'] = quote_text(i[5])
        rval.append(event)

    logging.info("Event details processed")
    return rval


def createEvent(events):
    """Takes a list of events and creates them on the calendar.
    """
    calendar = GoogleCalendar(credentials_path='credentials.json')
    # for i in calendar.get_calendar_list():
    #     print(i.summary)
    #     print(i.calendar_id)

    for event in events:
        start_date = datetime.strptime(event['start'], '%Y/%m/%d').date()
        end_date = datetime.strptime(event['end'], '%Y/%m/%d').date()
        end_date = (end_date + timedelta(days=1))

        new_event = Event(
            summary=f"{event['name']} - {event['category']}",
            start=start_date,
            end=end_date,
        )

        calendar.add_event(new_event, calendar_id='c_a0b924988ea1829e240a2db34c29d3e8c1be75f4a202c74748e7719e8e4415bd@group.calendar.google.com')
        logger.info(
            f"Event {event['name']}, from {event['start']} to {event['end']}, added to calendar")


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    try:
        # Call the Gmail API
        gmail = init()
        messages: list[str] = getMessages(gmail)
        if (messages):
           events = getEventDetails(gmail, messages)
           createEvent(events)

    except HttpError as error:
        print(f'An error occurred: {error}')

    finally:
        logger.info(
            f"Last Run on {int(datetime.now().timestamp())} {datetime.now()}")
        with open('last_run.txt', 'w') as f:
            f.write(str(int(datetime.now().timestamp())))


if __name__ == '__main__':
    main()
