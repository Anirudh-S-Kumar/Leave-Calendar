from __future__ import print_function

import os.path
import logging
import base64
import email
import html


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pprint import pprint
from ast import literal_eval

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SENDER_EMAIL = "anirudh.skumar.03@gmail.com"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GetMail")

gmail = None

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
    """Print contents of new emails"""
    # Call the Gmail API to only get emails from a specific sender
    results = service.users().messages().list(userId='me', q=f'from:{SENDER_EMAIL}').execute()
    messages = results.get('messages', [])

    if messages:
        # Get content of the email
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            skip = True
            for i in msg.get('payload').get('parts'):

                skip = not skip
                if skip:
                    continue
                
                ## get the label of the email
                label = msg.get('labelIds')
                print(label)

                text = (base64.urlsafe_b64decode(i.get('body').get('data')))
                text = (text.replace(b'\r\n', b' ')).decode('utf-8')
                print(text)
                print()
            print()
            
    else:
        logger.info('No messages found.')

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """

    try:
        # Call the Gmail API
        gmail = init()
        getMessages(gmail)
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()