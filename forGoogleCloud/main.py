import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import email
import base64
import flask
from flask import Flask
import json
from collections import deque
import datetime
import time
import tempfile

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_SERVICE_NAME = 'gmail'
API_VERSION = 'v1'

app = Flask(__name__)
app.secret_key = '_hkj97m_1j!!c7*n'
contactdict = {}
datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
badwords = set(["feedback", "hello", "news", "newsletters", "no-reply", "noreply", "notifications", "notification", "team", "support", "billing", "info", "help", "newsletter", "blog", "updates"])
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

@app.route('/')
def index():
  emails = get_request()
  return emails

@app.route('/getEmails')
def get_request():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = Credentials(**flask.session['credentials'])
    service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    flask.session['credentials'] = credentials_to_dict(credentials)
    mydict = searchMessages(service,"me")
    return mydict

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file('credentials.json',scopes=['https://www.googleapis.com/auth/gmail.readonly'])
    cur_url = flask.url_for('oauth2callback', _external=True)
    # if "http:" in cur_url and "https:" not in cur_url:
    #     cur_url = "https:" + cur_url[5:]
    flow.redirect_uri = cur_url
    flow.auth_uri = "https://accounts.google.com/o/oauth2/auth"
    flow.token_uri = "https://oauth2.googleapis.com/token"
    authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true')
    flask.session['state'] = state
    return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']
    # print (state, "BEFORE")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    cur_url = flask.url_for('oauth2callback', _external=True)
    # if "http:" in cur_url and "https:" not in cur_url:
    #     cur_url = "https:" + cur_url[5:]
    flow.redirect_uri = cur_url
    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    # if "http:" in authorization_response and "https:" not in authorization_response:
    #     authorization_response = "https:" + authorization_response[5:]
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)
    new_url = flask.url_for('get_request')
    # if "http:" in new_url and "https:" not in new_url:
    #     new_url = "https:" + new_url[5:]
    # print (new_url, "FINAL")
    return flask.redirect(new_url)

@app.route('/clear')
def clear():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared')

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

def getMessage(service,user_id,message_id):
    try:
        messageList = service.users().messages().get(userId = user_id, id = message_id, format = 'raw').execute()
        rawForm = base64.urlsafe_b64decode(messageList['raw'].encode('ASCII'))
        stringForm = email.message_from_bytes(rawForm)
        fromPerson = deque(stringForm['From'].split(' '))
        fromPeople = []
        badwordflag = True
        curperson = ""
        while fromPerson:
            cur = fromPerson.popleft()
            if '@' in cur:
                if cur.split('@')[0] in badwords:
                    badwordflag = False
                else:
                    while cur and cur[0] not in letters:
                        cur = cur[1:]
                    while cur and cur[-1] not in letters:
                        cur = cur[:-1]
                    if curperson:
                        curperson = curperson[:-1]
                        contactdict[cur] = curperson
                        fromPeople.append(curperson)
                    else:
                        if cur in contactdict:
                            fromPeople.append(contactdict[cur])
                curperson = ""
            else:
                curperson+=cur+' '
        toPerson = deque(stringForm['To'].split(' '))
        toPeople = []
        curperson = ""
        while toPerson:
            cur = toPerson.popleft()
            if '@' in cur:
                while cur and cur[0] not in letters:
                    cur = cur[1:]
                while cur and cur[-1] not in letters:
                    cur = cur[:-1]
                if curperson:
                    curperson = curperson[:-1]
                    contactdict[cur] = curperson
                    toPeople.append(curperson)
                else:
                    if cur in contactdict:
                        toPeople.append(contactdict[cur])
                curperson = ""
            else:
                curperson+=cur+' '
        # if fromPeople and fromPeople[0] == "fran dong":
        #     print ("HERE",messageList['snippet'])
        #print ("FROM: ", fromPeople)
        # print ("TO: ", toPeople)
        # print ("ORIGINAL: ", stringForm['To'])
        hasGoogleMeet = False
        if badwordflag:
            emailSubject = stringForm['Subject']
            #print (fromPerson, toPerson, emailSubject, "HERE")
            date = stringForm['Date']
            new = date.split(' ')
            secs = new[4].split(':')
            date_time = datetime.datetime(int(new[3]),datedict[new[2]],int(new[1]),int(secs[0]),int(secs[1]),int(secs[2]))
            regDate = datetime.date(int(new[3]),datedict[new[2]],int(new[1])) #year, month, day
            unixTime = (time.mktime(date_time.timetuple()))
            if "Invitation" in emailSubject or "Updated Invitation" in emailSubject:
                hasGoogleMeet = True
            # contentTypes = stringForm.get_content_maintype()
            # if contentTypes == 'multipart':
            #     messageBody = stringForm.get_payload()[0].get_payload()
            # else:
            #     messageBody = stringForm.get_payload()
            return (fromPeople, toPeople, unixTime, hasGoogleMeet, regDate)
        else:
            return (None, None, None, None, None)
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

def searchMessages(service, user_id):
    try:
        mydict = {}
        searchIDinbox = service.users().messages().list(userId = user_id, q = "label:inbox").execute() #get all emails in inbox
        searchIDsent = service.users().messages().list(userId = user_id, q = "in:sent").execute() #get emails that I sent
        def doThing(searchID, flag): #if flag = True, we're in inbox, look through from
            number_results = searchID['resultSizeEstimate']
            if number_results > 0:
                message_ids = searchID['messages']
                for ids in message_ids:
                    msg_id = ids['id']
                    fromPeople,toPeople,lastcontactUnix,hasGoogleMeet,regDate = getMessage(service,user_id,msg_id)
                    #print (fromPeople, toPeople, "HERE", flag)
                    if flag: #going through inbox (so fromPeople)
                        if fromPeople:
                            for name in fromPeople:
                                today = datetime.date.today()
                                dif = (today-regDate).days
                                onemonth = False
                                sixmonth = False
                                oneyear = False
                                twoyear = False
                                if dif <= 31:
                                    onemonth,sixmonth,oneyear,twoyear = True,True,True,True
                                elif dif <= 186:
                                    sixmonth,oneyear,twoyear = True,True,True
                                elif dif <= 365:
                                    oneyear,twoyear = True,True
                                elif dif <= 730:
                                    twoyear = True
                                if name not in mydict:
                                    #[last contact, last month, last 6 months, last year, last 2 years, totalreceived, totalsent, meetings]
                                    mydict[name] = [lastcontactUnix,0,0,0,0,0,0,0]
                                    if onemonth:
                                        mydict[name][1]+=1
                                    if sixmonth:
                                        mydict[name][2]+=1
                                    if oneyear:
                                        mydict[name][3]+=1
                                    if twoyear:
                                        mydict[name][4]+=1
                                    mydict[name][5]+=1
                                    if hasGoogleMeet:
                                        mydict[name][7]+=1

                                else:
                                    mydict[name][0] = max(mydict[name][0],lastcontactUnix)
                                    if onemonth:
                                        mydict[name][1]+=1
                                    if sixmonth:
                                        mydict[name][2]+=1
                                    if oneyear:
                                        mydict[name][3]+=1
                                    if twoyear:
                                        mydict[name][4]+=1
                                    mydict[name][5]+=1
                                    if hasGoogleMeet:
                                        mydict[name][7]+=1
                    else: #if not flag, going through sent, so toPeople
                        if toPeople:
                            for name in toPeople:
                                today = datetime.date.today()
                                dif = (today-regDate).days
                                onemonth = False
                                sixmonth = False
                                oneyear = False
                                twoyear = False
                                if dif <= 31:
                                    onemonth,sixmonth,oneyear,twoyear = True,True,True,True
                                elif dif <= 186:
                                    sixmonth,oneyear,twoyear = True,True,True
                                elif dif <= 365:
                                    oneyear,twoyear = True,True
                                elif dif <= 730:
                                    twoyear = True
                                if name not in mydict:
                                    #[last contact, last month, last 6 months, last year, last 2 years, totalreceived, totalsent, meetings]
                                    mydict[name] = [lastcontactUnix,0,0,0,0,0,0,0]
                                    if onemonth:
                                        mydict[name][1]+=1
                                    if sixmonth:
                                        mydict[name][2]+=1
                                    if oneyear:
                                        mydict[name][3]+=1
                                    if twoyear:
                                        mydict[name][4]+=1
                                    mydict[name][6]+=1
                                    if hasGoogleMeet:
                                        mydict[name][7]+=1

                                else:
                                    mydict[name][0] = max(mydict[name][0],lastcontactUnix)
                                    if onemonth:
                                        mydict[name][1]+=1
                                    if sixmonth:
                                        mydict[name][2]+=1
                                    if oneyear:
                                        mydict[name][3]+=1
                                    if twoyear:
                                        mydict[name][4]+=1
                                    mydict[name][6]+=1
                                    if hasGoogleMeet:
                                        mydict[name][1]+=1

        
            else:
                print ("Empty inbox")
        doThing(searchIDinbox, True)
        doThing(searchIDsent, False)
        return mydict

    except HttpError as error:
        print ("Error Occured: %s") %error
if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 8000, debug=True)


    
