from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import sqlite3

# Detup DB
connection = sqlite3.connect('MailSync.db')
cursor = connection.cursor()

# Setup the Gmail API
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
store = file.Storage('credentials/credentials.json')
userId = "me"

class Gmail:
    def __init__(self):
        self.get_credentials()

    def get_credentials(self):
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials/client_secret.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('gmail', 'v1', http=creds.authorize(Http()))

    def get_mail_list(self, query=None, labels=None):
        message_id_list = []
        result = (self.service.users().messages()
                .list(userId=userId, labelIds=labels, q=query).execute())
        message_id_list.extend(result['messages'])

        while 'nextPageToken' in result:
            result = (self.service.users().messages()
                    .list(userId=userId, labelIds=labels, q=query, pageToken=result['nextPageToken']).execute())
            message_id_list.extend(result['messages'])                    
        message_id_list = map(lambda x: x['id'], message_id_list)
        return message_id_list

    def get_mails(self, message_id_list):
        batch_request = self.service.new_batch_http_request()
        mail_dicts = []

        def append_mail_dicts(request_id, response_dict, error):
            if error:
                print (error)
                return
            message_dict = {
                'id': response_dict['id'],
                'body': response_dict['snippet']
            }
            payload = response_dict['payload']
            headers = payload['headers']
            for item in headers:
                if item['name'] == "Subject":
                    message_dict['subject'] = item['value']
                if item['name'] == "Date":
                    message_dict['date'] = item['value']
                if item['name'] == "From":
                    message_dict['sender'] = item['value']
            mail_dicts.append(message_dict)
        
        for m_id in message_id_list:
            batch_request.add(self.service.users().messages().get(userId=userId, id=m_id, format="metadata", metadataHeaders="Subject, Date, From"),
                append_mail_dicts
            )
        batch_request.execute()
        print (mail_dicts[0])
        return mail_dicts

gmail_handler = Gmail()
message_id_list = gmail_handler.get_mail_list()
gmail_handler.get_mails(message_id_list)
