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
        self.get_labels()

    def get_credentials(self):
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials/client_secret.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('gmail', 'v1', http=creds.authorize(Http()))

    def get_message_id_list(self, query=None, labels=None):
        message_id_list = []
        result = (self.service.users().messages()
                    .list(userId=userId, labelIds=labels, q=query).execute())
        message_id_list.extend(result['messages'])
        # Commenting this since syncing 1000's of mail at a time will take more time
        # while 'nextPageToken' in result:
        #     result = (self.service.users().messages()
        #             .list(userId=userId, labelIds=labels, q=query, pageToken=result['nextPageToken']).execute())
        #     message_id_list.extend(result['messages'])                  
        message_id_list = map(lambda x: x['id'], message_id_list)
        return message_id_list

    def get_labels(self):
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:            
            self.labels[label['name']] = label['id']

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
        try:
            label = self.service.users().labels().create(
                userId=userId,
                body=label_dict
            ).execute()
            return label
        except errors.HttpError as e:
            print (e)
            return False

    def add_labels(self, message_ids, labels):
        label_id_list = []
        for label in labels:
            label_id = self.labels.get(label)
            if not label_id:
                created_label = self.create_label(label)
                if created_label:
                    print ("Created a new label {}".format(created_label['name']))
                    label_id = created_label['id']
                else:
                    raise Exception("Unable to create label - {}".format(label))
            label_id_list.append(label_id)

        batch = self.service.users().messages().batchModify(
            userId=userId,
            body={
                "ids":message_ids,
                "addLabelIds": label_id_list,
                "removeLabelIds": []
            }
        )
        result = batch.execute()
        print (result)
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
        print (result)
        

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

    def get_emails(self):
        message_id_list = self.get_message_id_list()
        message_dict_list = self.get_message_dict_list(message_id_list)
        return message_dict_list
