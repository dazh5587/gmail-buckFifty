import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import language_v1
import email
import base64
import flask
from flask import Flask
import json
from collections import deque
import datetime
import time
import tempfile
import requests
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_SERVICE_NAME = 'gmail'
API_VERSION = 'v1'

app = Flask(__name__)
app.secret_key = '_hkj97m_1j!!c7*n'
contactdict = {}
datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
days = set(['Mon,', "Tue,", "Wed,", "Thu,", "Fri,", "Sat,", "Sun,"])
badwords = set(["feedback", "hello", "news", "newsletters", "no-reply", "noreply", "notifications", "notification", "team", "support", "billing", "info", "help", "newsletter", "blog", "updates"])
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
ffflag = True
@app.route('/<userID>')
def authorize(userID):
    flow = Flow.from_client_secrets_file('credentials.json',scopes=['https://www.googleapis.com/auth/gmail.readonly'])
    cur_url = flask.url_for('oauth2callback', _external=True)
    # if "http:" in cur_url and "https:" not in cur_url:
    #     cur_url = "https:" + cur_url[5:]
    flow.redirect_uri = cur_url
    flow.auth_uri = "https://accounts.google.com/o/oauth2/auth"
    flow.token_uri = "https://oauth2.googleapis.com/token"
    authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true')
    flask.session['state'] = state
    flask.session['userID'] = userID
    return flask.redirect(authorization_url)

@app.route('/getEmails')
def get_request():
    if 'credentials' not in flask.session:
        newurl = flask.url_for('authorize')
        return flask.redirect(newurl)
    credentials = Credentials(**flask.session['credentials'])
    service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    flask.session['credentials'] = credentials_to_dict(credentials)
    mydict = searchMessages(service,"me")
    newdict = {}
    for name in contactdict:
        newdict[name] = [float('inf'),0,0,0,0,0,0,0]
        for email in contactdict[name]:
            if email in mydict:
                arr = mydict[email]
                newdict[name][0] = min(newdict[name][0],arr[0])
                for i in range (1, len(arr)):
                    newdict[name][i]+=arr[i]
    res = {}
    for x in newdict:
        if newdict[x][6] > 0:
            res[x] = newdict[x]
    userID = flask.session['userID']
    # newdict = {}
    # for x in res:
    #     nlpdict = {}
    #     newlist_id = res[x][8]
    #     for message_id in newlist_id:
    #         nlp = doClassify(service,"me",message_id)
    #         if nlp:
    #             for y in nlp:
    #                 if y not in nlpdict:
    #                     nlpdict[y] = [nlp[y],1]
    #                 else:
    #                     nlpdict[y][0]+=nlp[y]
    #                     nlpdict[y][1]+=1
    #     print (x, nlpdict)
    bubble_url = "https://buckfifty.com/version-test/api/1.1/obj/connection"
    for x in res:
        for_post = {"Full Name": x, "last_contact": res[x][0],"email_1_month": res[x][1], 'email_6_months': res[x][2], 'email_1_year': res[x][3], 'email_2_years': res[x][4], 
         'email_received': res[x][5], 'email_sent': res[x][6], 'meetings': res[x][7], 'Created By (custom)': userID, "Source": "Gmail"}
        new = requests.post(bubble_url, json = for_post)
    return "Successfully imported contacts, you may safely close this window"

@app.route('/test/<userID>')
def test(userID):
    # text = text = " fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex fuck sex"

    # new = classify(text)
    
    return ("The userID is " + str(userID))
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
    return flask.redirect(new_url)

@app.route('/clear')
def clear():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    if 'userID' in flask.session:
        del flask.session['userID']
    return ('Credentials have been cleared')

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

def classify(text, verbose=True):
    language_client = language_v1.LanguageServiceClient()

    document = language_v1.Document(
        content=text, type_=language_v1.Document.Type.PLAIN_TEXT
    )
    response = language_client.classify_text(request={"document": document})
    categories = response.categories
    result = {}
    for category in categories:
        result[category.name] = category.confidence
    return result

def doClassify(service, user_id, message_id):
    messageList = service.users().messages().get(userId = user_id, id = message_id, format = 'raw').execute()
    rawForm = base64.urlsafe_b64decode(messageList['raw'].encode('ASCII'))
    stringForm = email.message_from_bytes(rawForm)
    text = None
    canClassify = False
    nlp = None
    for part in stringForm.walk():
        stringForm.get_payload()
        if part.get_content_type() == 'text/plain':
            text = part.get_payload()
    if text:
        new = text.splitlines()
        messageText = ""
        for x in new:
            if x:
                messageText+=x+ ' '
        messageText = messageText[:-1]
        test = messageText.split(" ")
        if len(test) >= 20:
            canClassify = True
    if canClassify:
        nlp = classify(messageText)
    return nlp

def getMessage(service,user_id,message_id):
    try:
        messageList = service.users().messages().get(userId = user_id, id = message_id, format = 'raw').execute()
        rawForm = base64.urlsafe_b64decode(messageList['raw'].encode('ASCII'))
        stringForm = email.message_from_bytes(rawForm)
        fromEmails = []
        if stringForm['From']:
            fromPerson = deque(stringForm['From'].split(' '))
            badwordflag = True
            curperson = ""
            while fromPerson:
                cur = fromPerson.popleft()
                if '@' in cur:
                    temp = cur.split('@')[0]
                    if temp in badwords or 'support' in temp or 'help' in temp:
                        badwordflag = False
                    else:
                        while cur and cur[0] not in letters:
                            cur = cur[1:]
                        while cur and cur[-1] not in letters:
                            cur = cur[:-1]
                        if curperson:
                            while curperson and curperson[0] not in letters:
                                curperson = curperson[1:]
                            while curperson and curperson[-1] not in letters:
                                curperson = curperson[:-1]
                            if curperson:
                                if curperson not in contactdict:
                                    contactdict[curperson] = set([cur])
                                else:
                                    contactdict[curperson].add(cur)
                            fromEmails.append(cur)
                    curperson = ""
                else:
                    curperson+=cur+' '
        toEmails = []
        if stringForm['To']:
            toPerson = deque(stringForm['To'].split(' '))
            curperson = ""
            while toPerson:
                cur = toPerson.popleft()
                if '@' in cur:
                    while cur and cur[0] not in letters:
                        cur = cur[1:]
                    while cur and cur[-1] not in letters:
                        cur = cur[:-1]
                    if curperson:
                        while curperson and curperson[0] not in letters:
                            curperson = curperson[1:]
                        while curperson and curperson[-1] not in letters:
                            curperson = curperson[:-1]
                        if curperson:
                            if curperson not in contactdict:
                                contactdict[curperson] = set([cur])
                            else:
                                contactdict[curperson].add(cur)
                        toEmails.append(cur)
                    curperson = ""
                else:
                    curperson+=cur+' '
        hasGoogleMeet = False
        if badwordflag:
            emailSubject = stringForm['Subject']
            bcc = stringForm['Bcc']
            curperson = ""
            if bcc:
                bcc = deque(bcc.split(' '))
                while bcc:
                    cur = bcc.popleft()
                    if '@' in cur:
                        while cur and cur[0] not in letters:
                            cur = cur[1:]
                        while cur and cur[-1] not in letters:
                            cur = cur[:-1]
                        if curperson:
                            curperson = curperson[:-1]
                            if curperson not in contactdict:
                                contactdict[curperson] = set([cur])
                            else:
                                contactdict[curperson].add(cur)
                            toEmails.append(cur)
                        curperson = ""
                    else:
                        curperson+=cur+' '
            cc = stringForm['Cc']
            curperson = ""
            if cc:
                cc = deque(cc.split(' '))
                while cc:
                    cur = cc.popleft()
                    if '@' in cur:
                        while cur and cur[0] not in letters:
                            cur = cur[1:]
                        while cur and cur[-1] not in letters:
                            cur = cur[:-1]
                        if curperson:
                            while curperson and curperson[0] not in letters:
                                curperson = curperson[1:]
                            while curperson and curperson[-1] not in letters:
                                curperson = curperson[:-1]
                            if curperson:
                                if curperson not in contactdict:
                                    contactdict[curperson] = set([cur])
                                else:
                                    contactdict[curperson].add(cur)
                            toEmails.append(cur)
                        curperson = ""
                    else:
                        curperson+=cur+' '
            #print (fromPerson, toPerson, emailSubject, "HERE")
            date = stringForm['Date']
            #print (date, "ORIG")
            new = date.split(' ')
            # print (new, "HRERE")
            dayofWeek = None
            year = None
            month = None
            day = None
            secs = None
            for x in new:
                if x in days:
                    dayofWeek = x[:-1]
                elif x in datedict:
                    month = datedict[x]
                elif len(x) == 4 and (x[0] == '2' or x[1] == '1'):
                    year = int(x)
                elif len(x) == 2 or len(x) == 1:
                    day = int(x)
                elif ':' in x:
                    secs = x
                    secs = secs.split(':')
            date_time = datetime.datetime(year,month,day,int(secs[0]),int(secs[1]),int(secs[2]))
            regDate = datetime.date(year,month,day)
            # if new[0] in days:
            #     secs = new[4].split(':')
            #     date_time = datetime.datetime(int(new[3]),datedict[new[2]],int(new[1]),int(secs[0]),int(secs[1]),int(secs[2]))
            #     regDate = datetime.date(int(new[3]),datedict[new[2]],int(new[1])) #year, month, day
            # else:
            #     secs = new[3].split(':')
            #     date_time = datetime.datetime(int(new[2]),datedict[new[1]], int(new[0]), int(secs[0]),int(secs[1]),int(secs[2]))
            #     regDate = datetime.date(int(new[2]),datedict[new[1]],int(new[0])) #year, month, day
            unixTime = (time.mktime(date_time.timetuple()))
            if emailSubject:
                if "Invitation" in emailSubject or "Updated Invitation" in emailSubject:
                    hasGoogleMeet = True

            return (fromEmails, toEmails, unixTime, hasGoogleMeet, regDate)
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
        searchIDinbox = service.users().messages().list(userId = user_id, q = "label:inbox", maxResults = 200).execute() #get all emails in inbox
        searchIDsent = service.users().messages().list(userId = user_id, q = "in:sent", maxResults = 200).execute() #get emails that I sent
        def doThing(searchID, flag): #if flag = True, we're in inbox, look through from
            number_results = searchID['resultSizeEstimate']
            if number_results > 0:
                message_ids = searchID['messages']
                for ids in message_ids:
                    msg_id = ids['id']
                    fromEmails,toEmails,lastcontactUnix,hasGoogleMeet,regDate = getMessage(service,user_id,msg_id)
                    if flag: #going through inbox (so fromEmails)
                        if fromEmails:
                            for email in fromEmails:
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
                                if email not in mydict:
                                    #[last contact, last month, last 6 months, last year, last 2 years, totalreceived, totalsent, meetings, all messageIDs]
                                    #mydict[email] = [lastcontactUnix,0,0,0,0,0,0,0,[msg_id]]
                                    mydict[email] = [lastcontactUnix,0,0,0,0,0,0,0]
                                    if onemonth:
                                        mydict[email][1]+=1
                                    if sixmonth:
                                        mydict[email][2]+=1
                                    if oneyear:
                                        mydict[email][3]+=1
                                    if twoyear:
                                        mydict[email][4]+=1
                                    mydict[email][5]+=1
                                    if hasGoogleMeet:
                                        mydict[email][7]+=1

                                else:
                                    mydict[email][0] = max(mydict[email][0],lastcontactUnix)
                                    if onemonth:
                                        mydict[email][1]+=1
                                    if sixmonth:
                                        mydict[email][2]+=1
                                    if oneyear:
                                        mydict[email][3]+=1
                                    if twoyear:
                                        mydict[email][4]+=1
                                    mydict[email][5]+=1
                                    if hasGoogleMeet:
                                        mydict[email][7]+=1
                                    #mydict[email][8].append(msg_id)
                    else: #if not flag, going through sent, so toEmail
                        if toEmails:
                            for email in toEmails:
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
                                if email not in mydict:
                                    #[last contact, last month, last 6 months, last year, last 2 years, totalreceived, totalsent, meetings]
                                    #mydict[email] = [lastcontactUnix,0,0,0,0,0,0,0, [msg_id]]
                                    mydict[email] = [lastcontactUnix,0,0,0,0,0,0,0]
                                    if onemonth:
                                        mydict[email][1]+=1
                                    if sixmonth:
                                        mydict[email][2]+=1
                                    if oneyear:
                                        mydict[email][3]+=1
                                    if twoyear:
                                        mydict[email][4]+=1
                                    mydict[email][6]+=1
                                    if hasGoogleMeet:
                                        mydict[email][7]+=1

                                else:
                                    mydict[email][0] = max(mydict[email][0],lastcontactUnix)
                                    if onemonth:
                                        mydict[email][1]+=1
                                    if sixmonth:
                                        mydict[email][2]+=1
                                    if oneyear:
                                        mydict[email][3]+=1
                                    if twoyear:
                                        mydict[email][4]+=1
                                    mydict[email][6]+=1
                                    if hasGoogleMeet:
                                        mydict[email][1]+=1
                                    #mydict[email][8].append(msg_id)

        
            else:
                print ("Empty inbox")
        doThing(searchIDinbox, True)
        doThing(searchIDsent, False)
        return mydict

    except HttpError as error:
        print ("Error Occured: %s") %error

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 8000)
