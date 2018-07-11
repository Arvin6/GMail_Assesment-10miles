from gmail import GmailAPI
from model import Mail

gmail_handler = GmailAPI()

message_dict_list = gmail_handler.get_emails()

# Sync mails to DB
for message_dict in message_dict_list:
    try:
        # May throw exception if the mail exists
        Mail.insert(**message_dict).execute()
    except Exception as e:
        print (e)

