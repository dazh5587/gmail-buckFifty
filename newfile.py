import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import email
import base64
from flask import Flask,request
import json
from collections import deque
import datetime
import time

app = Flask(__name__)

@app.route("/result", methods = ["POST","GET"])

def result():
    output = request.get_json(force = True)
    if len(output.keys()) < 2:
        return {"Status": "Bad response"}
    if 'num1' and 'num2' in output:
        num1 = int(output['num1'])
        num2 = int(output['num2'])
    else:
        num1 = 1
        num2 = 10
    cal = {}
    cal['addition'] = num1+num2
    cal['subtraction'] = num1-num2
    cal['multiplication'] = num1*num2
    cal['division'] = num1/num2
    return (cal)
    
@app.route("/getEmails", methods = ["GET"])

def emails():
    return "HI"
    # res = getall()
    # return res




# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def getMessage(service,user_id,message_id):
    try:
        datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
        badwords = set(["feedback", "hello", "news", "newsletters", "no-reply", "noreply", "notifications", "notification", "team", "support", "billing", "info", "help", "newsletter", "blog", "updates"])
        messageList = service.users().messages().get(userId = user_id, id = message_id, format = 'raw').execute()
        rawForm = base64.urlsafe_b64decode(messageList['raw'].encode('ASCII'))
        stringForm = email.message_from_bytes(rawForm)
        fromPerson = deque(stringForm['From'].split(' '))
        name = ""
        while fromPerson and '@' not in fromPerson[0]:
            name+=fromPerson[0]+ ' '
            fromPerson.popleft()
        name = name[:-1]
        emailAddress_from = fromPerson[-1][1:-1]
        new = emailAddress_from.split('@')
        if new[0] not in badwords:
            toPerson = stringForm['To']
            emailSubject = stringForm['Subject']
            date = stringForm['Date']
            new = date.split(' ')
            secs = new[4].split(':')
            date_time = datetime.datetime(int(new[3]),datedict[new[2]],int(new[1]),int(secs[0]),int(secs[1]),int(secs[2]))
            unixTime = (time.mktime(date_time.timetuple()))
            # contentTypes = stringForm.get_content_maintype()
            # if contentTypes == 'multipart':
            #     messageBody = stringForm.get_payload()[0].get_payload()
            # else:
            #     messageBody = stringForm.get_payload()
            return (name, unixTime)
        else:
            return (None,None)
        #messageList is dictionary with keys
            # threadId
            # labelIds
            # snippet
            # sizeEstimate
            # raw
            # historyId
            # internalDate
    except HttpError as error:
        print ("Error Occured: %s") %error

def searchMessages(service,user_id):
    try:
        mydict = {}
        myset = set()
        searchID = service.users().messages().list(userId = user_id).execute()
        number_results = searchID['resultSizeEstimate']
        if number_results > 0:
            message_ids = searchID['messages']
            for ids in message_ids:
                msg_id = ids['id']
                name,lastcontact = getMessage(service,user_id,msg_id)
                if name:
                    if name not in mydict:
                        mydict[name] = [lastcontact,1]
                    else:
                        mydict[name] = [max(mydict[name][0],lastcontact),mydict[name][1]+1]
        else:
            print ("Empty inbox")

        return mydict

    except HttpError as error:
        print ("Error Occured: %s") %error



def get_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    return service
def getall():
    service = get_service()
    mydict = searchMessages(service,"me")
    return mydict

if __name__ == '__main__':
    app.run(debug = True, port=8000)
    # res = getall()
    # print (res)
    # datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
    # string = "Wed, 19 Apr 2023 09:37:24 -0600"
    # new = string.split(' ')
    # secs = new[4].split(':')
    # date_time = datetime.datetime(int(new[3]),datedict[new[2]],int(new[1]),int(secs[0]),int(secs[1]),int(secs[2]))
    # print (date_time)
    #service = get_service()
    #print (service.users().messages().list(userId = 'me').execute())
    # searchMessages(service,"me")
    ## print (emailCounts.keys())
    # date_time = datetime.datetime(2023, 6, 3, 12, 0, 50)
    # inUnix = (time.mktime(date_time.timetuple()))
    # print (date_time, inUnix)
