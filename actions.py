from gmail import GmailAPI
from model import Mail

gmail_handler = GmailAPI()

def sync_mails_to_db():
    # Sync mails to DB
    message_dict_list = gmail_handler.get_emails()
    for message_dict in message_dict_list:
        try:
            # May throw exception if the mail exists
            Mail.insert(**message_dict).execute()
        except Exception as e:
            print (e)

