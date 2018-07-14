from apiclient.discovery import build
from apiclient import errors
from httplib2 import Http
from oauth2client import file, client, tools
import dateutil.parser as parser

# Setup the Gmail API
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
store = file.Storage('credentials/credentials.json')
userId = "me"

class GmailAPI:
    def __init__(self):
        self.labels = {}
        self.get_credentials()
        self.get_all_labels()


    def get_credentials(self):
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials/client_secret.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('gmail', 'v1', http=creds.authorize(Http()))


    def get_message_id_list(self, query=None, labels=None):
        message_id_list = []
        result = (self.service.users().messages()
                    .list(userId=userId, labelIds=labels, q=query, maxResults=500)).execute()
        if result.get('messages'):
            message_id_list.extend(result['messages'])

        # Limiting the number of pages due to quota limitations
        pages = 3
        
        while "nextPageToken" in result and (pages>0):
            request = (self.service.users().messages()
                            .list(userId=userId, labelIds=labels, q=query, maxResults=100, pageToken=result["nextPageToken"]))
            result = request.execute()
            message_id_list.extend(result['messages'])
            pages -= 1
        
        print ("{} mails are being synced to Database".format(len(message_id_list)))
        message_id_list = map(lambda x: x['id'], message_id_list)
        return message_id_list


    def get_all_labels(self):
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:            
            self.labels[label['name']] = label['id']


    def get_or_create_label(self, label):
        label_id = self.labels.get(label)
        if not label_id:
            created_label = self.create_label(label)
            print ("Created a new label {}".format(created_label['name']))
            label_id = created_label['id']
        return label_id


    def create_label(self, name):
        label_color = {
            "textColor": "#ffffff",
            "backgroundColor": "#44b984"
        }
        label_dict = {
            "name": name.upper(),
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow",
            "color": label_color
        }
        label = self.service.users().labels().create(
            userId=userId,
            body=label_dict).execute()
        return label

    def add_labels(self, message_ids, labels):
        label_id_list = []
        for label in labels:
            label_id = self.get_or_create_label(label)
            label_id_list.append(label_id)

        batch = self.service.users().messages().batchModify(
            userId=userId,
            body={
                "ids":message_ids,
                "addLabelIds": label_id_list,
                "removeLabelIds": []
            }
        ).execute()
        
        print ("{} mails added to the {} label".format(len(message_ids), labels))
    

    def remove_labels(self, message_ids, labels):
        batch = self.service.users().messages().batchModify(
            userId=userId,
            body={
                "ids":message_ids,
                "addLabelIds": [],
                "removeLabelIds": labels
            }
        )
        result = batch.execute()


    def get_message_dict_list(self, message_id_list):
        batch_request = self.service.new_batch_http_request()
        mail_dicts = []

        def append_mail_dicts(request_id, response_dict, error):
            if error:
                print (error)
                return
            payload = response_dict['payload']
            headers = payload['headers']
            
            message_dict = {
                'gid': response_dict['id'],
                "message": response_dict['snippet']
            }
            for item in headers:
                if item['name'] == "Subject":
                    message_dict['subject'] = item['value']
                if item['name'] == "Date":
                    message_dict['date'] = parser.parse(item['value']).isoformat()
                if item['name'] == "From":
                    message_dict['sender'] = item['value']
            mail_dicts.append(message_dict)
        
        for m_id in message_id_list:
            batch_request.add(self.service.users().messages()
                            .get(userId=userId, id=m_id, format="metadata",
                                 metadataHeaders=["From", "Subject", "Date"]),
                append_mail_dicts
            )
        batch_request.execute()
        return mail_dicts

    def get_emails(self, last_sync_time=None):
        last_sync_time_query = ("after:{}".format(last_sync_time)) if last_sync_time else  None
        message_id_list = self.get_message_id_list(query=last_sync_time_query)
        message_dict_list = self.get_message_dict_list(message_id_list)
        return message_dict_list
