from datetime import datetime, timedelta
import json
import re
import time

import peewee
from gmail import GmailAPI
from model import Mail, Sync, db


# Initialize google handle
try:
    gmail_handler = GmailAPI()
except Exception as e:
    print (e)
    exit()


# Get last sync time
try:
    sync_results =  Sync.select().order_by(Sync.syncedon.desc()).get()
    last_sync_time = sync_results.syncedon
except Exception as e:
    last_sync_time = None


def sync_mails_to_db(last_sync_time):
    # Sync mails to DB
    if last_sync_time:
        human_readable_time_stamp = (datetime.fromtimestamp(last_sync_time)
                                                .strftime('%Y-%m-%d %H:%M:%S'))

        print ("Database is last updated on {}".format(human_readable_time_stamp))

    message_dict_list = gmail_handler.get_emails(last_sync_time=last_sync_time)
    for row in db.batch_commit(message_dict_list, 100):
        try:
            Mail.create(**row)
        except peewee.IntegrityError as e:
            pass
        except Exception as e:
            print (e)


def mark_mails_as_read(message_ids):
    print ("{} mails will be marked as read".format(len(message_ids)))
    labels = ['UNREAD']
    gmail_handler.remove_labels(message_ids=message_ids, labels=labels)

def mark_mails_as_spam(message_ids):
    labels = ["SPAM"]
    gmail_handler.add_labels(message_ids, labels)

def mark_mails_as_important(message_ids):
    labels = ['IMPORTANT']
    gmail_handler.add_labels(message_ids, labels)

def add_labels_to_mail(message_ids, labels):
    if not isinstance(labels, list):
        labels = [labels]
    labels = [label.upper() for label in labels]
    try:
        gmail_handler.add_labels(message_ids, labels)
    except Exception as e:
        print (e)


def get_key(key):
    if key == "from":
        return Mail.sender
    elif key == "subject":
        return Mail.subject
    elif key == "received":
        return Mail.date
    elif key == "message":
        return Mail.message
    return None

def validate_fields(key=None, comparison=None, value=None):
    valid_key = get_key(key)
    if value and valid_key and comparison:
        return valid_key, comparison, value
    raise Exception("Invalid format \"{key}:{operator}:{value}\""
                                .format(key=key,value=value,operator=comparison))

def get_iso_for_delta(value):
    number = int(value[:-1])
    scale = value[-1]
    if scale == "h":
        return (datetime.utcnow() - timedelta(hours=number)).isoformat()
    elif scale == "m":
        return (datetime.utcnow() - timedelta(minutes=number)).isoformat()
    elif scale == "d":
        return (datetime.utcnow() - timedelta(days=number)).isoformat()
    raise Exception("Invalid scale")


def get_clause_list(condition_list):
    clause_list = []
    for condition in condition_list:
        condition_split = condition.split(":")
        key, comparison, value = validate_fields(*condition_split)
        if value:
            if comparison == "equals":
                clause_list.append (key == value)
            elif comparison == "contains":
                clause_list.append (key ** value)
            elif comparison == "not":
                clause_list.append (key != value)

            elif comparison == "lt" and condition_split[0] == "received":
                value = get_iso_for_delta(value)
                clause_list.append (key > value)
            elif comparison == "gt" and condition_split[0] == "received":
                value = get_iso_for_delta(value)
                clause_list.append (key < value)
            elif comparison == "on" and condition_split[0] == "received":
                value = get_iso_for_delta(value)
                clause_list.append (key < value)
            else:
                raise Exception("Invalid operator \"{operator}\""
                                        .format(operator=comparison))
    return clause_list


if __name__ == "__main__":
    if input("Would you like to sync your Gmail inbox? (y/n)") == "y":
        sync_mails_to_db(last_sync_time)

    sync_time = int(time.time())
    try:
        Sync.create(syncedon=sync_time)
    except Exception as e:
        print (e)

    with open('rules.json', 'r') as rule_fp:
        rules = json.load(rule_fp)
    
    for rule in rules:
        condition = rule.get('condition')
        action = rule.get('action')

        if not action or not condition:
            """
            Checking if action or condition exists for the rule
            """
            print ("{} is not a valid rule".format(rule))
            continue

        operators = [operator.upper() for operator in condition[1::2]]
        condition_list = condition[0::2]

        try:
            for operator in operators:
                if operator not in ["AND", "OR", "NOT"]:
                    raise Exception("{} is not a valid operator".format(operator))

            clause_list = get_clause_list(condition_list)
            
            expression = clause_list.pop(0)
            
            while clause_list:
                clause = clause_list.pop(0)
                operator = operators.pop(0)
            
                if operator=="AND":
                    expression = (expression & clause)
            
                elif operator=="OR":
                    expression = (expression | clause)
            
                elif operator=="NOT":
                    expression |= ~(clause)
            
            result = Mail.select(Mail.gid).where(expression)
            # print (result.sql())
            message_ids = [row.gid for row in result]
            if message_ids:
                if action.get('mark_as_read'):
                    mark_mails_as_read(message_ids)
                
                if action.get('mark_as_important'):
                    mark_mails_as_important(message_ids)
                
                if action.get('mark_as_spam'):
                    mark_mails_as_spam(message_ids)

                labels = action.get('labels')
                if labels:
                    add_labels_to_mail(message_ids, labels)
        except Exception as e:
            print (e)
    