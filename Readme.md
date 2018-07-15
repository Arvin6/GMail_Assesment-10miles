This project uses the GMail API to sync and enforce rules on your mails in the inbox.

# Captured information from mails:
1) Message Id [gid] (this is not queryable, and is used for identification of mails in Gmail API)
2) Sender [From]
3) Received time and date [received]
4) A snippet of Message body [message]
5) Subject [subject]

# Actions supported:
1) Mark mails as read
2) Mark mails as spam
3) Mark mails as important
4) Add labels to mails
5) Sync your latest mails 

# Filter conditions supported:
1) Based on the received date/time in days, hours and minutes. 
    a) Lesser than a date/time in d| h | m. [lt]
    b) Greater than a date/time in d | h | m. [gt]
2) Checking equality in any of the captured keys. [equals]
3) Checking contains in any of the captured keys. [contains] (The user is responsible to add wildcards appropriately in conditions)
4) Checking for negation of a condition. [not]

# Piping conditions:
The conditions can be piped using these operators:
1) AND
2) OR
3) NOT

# Example condtion:
```json
{
"condition" : ["from:contains:%tenmiles%", "AND", "message:contains:%interview%"],
"action" : {
  "mark_as_imiportant" : true
  }
}
```

# Rules format:
1) "condition" and "action" are required fields.
2) contains filter is case insensitive.
3) lesser (lt) than and greater than (gt) go with received key only.
4) Piping conditions must exist appropriately in the chain.

# Runing the application
1) ```pip install -r requirements.txt```
2) Navigate to Application folder.
3) ```python action.py```
4) Fill in the rules in rules.json file.
5) Enter (y/n) for the prompt to sync mails (Enter "y" for the first run). This is required to populate the DB initially(2000 mails).

# Other info
1) Added a client_secret (from a testing account) for testing purposes. However this is an awful practice and this will be removed in 3 days.
