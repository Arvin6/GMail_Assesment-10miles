import json
import re
from datetime import datetime, timedelta

import peewee
from gmail import GmailAPI
from model import Mail, db


gmail_handler = GmailAPI()

def sync_mails_to_db():
    # Sync mails to DB
    message_dict_list = gmail_handler.get_emails()
    for row in db.batch_commit(message_dict_list, 100):
        try:
            Mail.create(**row)
        except peewee.IntegrityError as e:
            pass
        except Exception as e:
            print (e)

def get_clause_list(condition_list):

    def get_key(key):
        if key == "from":
            return Mail.sender
        elif key == "subject":
            return Mail.subject
        elif key == "date":
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

    def get_iso_delta(value):
        number = int(value[:-1])
        scale = value[-1]
        if scale == "h":
            return (datetime.utcnow() - timedelta(hours=number)).isoformat()
        elif scale == "m":
            return (datetime.utcnow() - timedelta(minutes=number)).isoformat()
        elif scale == "d":
            return (datetime.utcnow() - timedelta(days=number)).isoformat()
        raise Exception("Invalid scale")

    clause_list = []
    try:
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

                elif comparison == "lt" and condition_split[0] == "date":
                    value = get_iso_delta(value)
                    clause_list.append (key > value)
                elif comparison == "gt" and condition_split[0] == "date":
                    value = get_iso_delta(value)
                    clause_list.append (key < value)
                else:
                    raise Exception("Invalid format \"{key}:{operator}:{value}\""
                                            .format(key=key,value=value,operator=comparison))
        return clause_list
    except Exception as e:
        print (e)


if __name__ == "__main__":
    if input("Would you like to sync the mails? (y/n)") == "y":
        sync_mails_to_db()

    with open('rules.json', 'r') as rule_fp:
        rules = json.load(rule_fp)
    for rule in rules:
        condition = rule.get('condition')
        action = rule.get('action')
        if condition:
            operators = condition[1::2]
            condition_list = condition[0::2]
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
        result = Mail.select().where(expression)
        print (result.sql())
        for row in result:
            print (row.gid, row.sender)

