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
import requests

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/calendar.readonly']
app = Flask(__name__)
app.secret_key = '_hkj97m_1j!!c7*n'
contactdict = {}
datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
days = set(['Mon,', "Tue,", "Wed,", "Thu,", "Fri,", "Sat,", "Sun,"])
badwords = set(["feedback", "hello", "news", "newsletters", "no-reply", "noreply", "notifications", "notification", "team", "support", "billing", "info", "help", "newsletter", "blog", "updates"])
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
ffflag = True

@app.route('/<userID>&<option>&<version>')
def authorize(userID, option, version):
    flask.session['userID'] = userID
    flask.session['option'] = option
    flask.session['version'] = version
    flow = Flow.from_client_secrets_file('credentials.json',scopes=['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/calendar.readonly'])
    cur_url = flask.url_for('oauth2callback', _external=True)
    flow.redirect_uri = cur_url
    flow.auth_uri = "https://accounts.google.com/o/oauth2/auth"
    flow.token_uri = "https://oauth2.googleapis.com/token"
    authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true')
    flask.session['state'] = state
    return flask.redirect(authorization_url)

@app.route('/getInfo')
def get_request():
    print ("1. LOGS ARE HERE BUDDY VERSION 3.0")
    if 'credentials' not in flask.session:
        print ("HELLO FUCKER")
        #newurl = flask.url_for('authorize')
        newurl = flask.url_for('authorize', userID=flask.session['userID'],option=flask.session['option'],version=flask.session['version'])
        return flask.redirect(newurl)
    credentials = Credentials(**flask.session['credentials'])
    flask.session['credentials'] = credentials_to_dict(credentials)
    if flask.session['version'] == 'test':
        bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/gmail-sync-in-progress/"
        bearer_token = '725b8d6584b071a02e1316945bf7743b'
        headers = {'Authorization': f'Bearer {bearer_token}'}
        for_post = {'user': flask.session['userID'], "status": "yes"}
        new = requests.post(bubble_url, json = for_post, headers = headers)
    if flask.session['version'] == 'live':
        bubble_url = "https://buckfifty.com/api/1.1/wf/gmail-sync-in-progress/"
        bearer_token = '725b8d6584b071a02e1316945bf7743b'
        headers = {'Authorization': f'Bearer {bearer_token}'}
        for_post = {'user': flask.session['userID'], "status": "yes"}
        new = requests.post(bubble_url, json = for_post, headers = headers)
    service = build('gmail', 'v1', credentials=credentials)
    mydict = searchMessages(service,"me")
    print ("4. In get_request successfully")
    if flask.session['version'] == 'test': #calendar data as well for testing right now
        service = build('calendar', 'v3', credentials=credentials)
        calendar_dict = get_calendar_info(service)
        for x in calendar_dict:
            if x not in mydict:
                mydict[x] = [calendar_dict[x][0],0,0,0,0,0,0,calendar_dict[x][1]]
            else:
                mydict[x][0] = max(mydict[x][0],calendar_dict[x][1])
                mydict[x][-1] = calendar_dict[x][1]
    newdict = {}
    for name in contactdict:
        while name and name[0] not in letters:
            name = name[1:]
        while name and name[-1] not in letters:
            name = name[:-1]
        orig = name
        name = name.lower()
        name = name.title()
        if name not in newdict:
            newdict[name] = [0,0,0,0,0,0,0,0]
        for email in contactdict[orig]:
            if email in mydict:
                arr = mydict[email]
                newdict[name][0] = max(newdict[name][0],arr[0])
                for i in range (1, len(arr)):
                    newdict[name][i]+=arr[i]
    
    res = {}
    for x in newdict:
        if newdict[x][6] > 0 and "Support" not in x:
            if ',' in x:
                name = x.split(',')
                name[1] = name[1][1:]
                name = name[1]+' '+name[0]
            else:
                name = x
            res[name] = newdict[x]
    userID = flask.session['userID']
    # # newdict = {}
    # # for x in res:
    # #     nlpdict = {}
    # #     newlist_id = res[x][8]
    # #     for message_id in newlist_id:
    # #         nlp = doClassify(service,"me",message_id)
    # #         if nlp:
    # #             for y in nlp:
    # #                 if y not in nlpdict:
    # #                     nlpdict[y] = [nlp[y],1]
    # #                 else:
    # #                     nlpdict[y][0]+=nlp[y]
    # #                     nlpdict[y][1]+=1
    # #     print (x, nlpdict)

    if flask.session['version'] == 'test':
        bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/create-or-update-connection/"
        bearer_token = '725b8d6584b071a02e1316945bf7743b'
    else:
        bubble_url = "https://buckfifty.com/api/1.1/wf/create-or-update-connection/"
        bearer_token = "725b8d6584b071a02e1316945bf7743b"
    headers = {'Authorization': f'Bearer {bearer_token}'}
    for x in res:
        if 'utf' not in x and "Utf" not in x and "?" not in x:
            for_post = {"Full Name": x, "last_contact": res[x][0]*1000,"email_1_month": res[x][1], 'email_6_months': res[x][2], 'email_1_year': res[x][3], 'email_2_years': res[x][4], 
            'email_received': res[x][5], 'email_sent': res[x][6], 'meetings': res[x][7], 'Created By (custom)': flask.session['userID'], "Source": "Gmail", "Potential Key Relationship": "yes"}
            new = requests.post(bubble_url, json = for_post, headers = headers)

    if flask.session['version'] == 'test':
        bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/gmail-sync-in-progress/"
        bearer_token = '725b8d6584b071a02e1316945bf7743b'
        headers = {'Authorization': f'Bearer {bearer_token}'}
        for_post = {'user': flask.session['userID'], "status": "no"}
        new = requests.post(bubble_url, json = for_post, headers = headers)
    if flask.session['version'] == 'live':
        bubble_url = "https://buckfifty.com/api/1.1/wf/gmail-sync-in-progress/"
        bearer_token = '725b8d6584b071a02e1316945bf7743b'
        headers = {'Authorization': f'Bearer {bearer_token}'}
        for_post = {'user': flask.session['userID'], "status": "no"}
        new = requests.post(bubble_url, json = for_post, headers = headers)
    print (res)
    print ("---DONE----")
    if 'credentials' in flask.session:
        del flask.session['credentials']
    if 'userID' in flask.session:
        del flask.session['userID']
    if 'option' in flask.session:
        del flask.session['option']
    if 'version' in flask.session:
        del flask.session['version']
    return "Successfully imported contacts, you may safely close this window"

    # if flask.session['option'] == 'c': #get calendar data
    #     service = build('calendar', 'v3', credentials=credentials)
    #     mydict = get_calendar_info(service)
    #     if 'credentials' in flask.session:
    #         del flask.session['credentials']
    #     return mydict

@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']
    # print (state, "BEFORE")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    cur_url = flask.url_for('oauth2callback', _external=True)
    flow.redirect_uri = cur_url
    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)
    new_url = flask.url_for('get_request')
    return flask.redirect(new_url)

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

def get_calendar_info(service):
    events_result = service.events().list(calendarId='primary', maxResults = 250).execute()
    events = events_result.get('items', [])
    # print (len(events))
    mydict = {} #email address: [last_contact, count of meetings with email]
    for event in events:
        unixtime = 0
        if 'start' in event:
            if 'dateTime' in event['start']:
                lastcontact = event['start']['dateTime']
                dt = datetime.datetime.fromisoformat(lastcontact)
                unixtime = time.mktime(dt.timetuple())
                # unixtime*=1000
        if 'attendees' in event:
            for x in event['attendees']:
                email = x['email']
                if 'self' not in x:
                    if email not in mydict:
                        mydict[email] = [unixtime,1]
                    else:
                        mydict[email][0] = max(mydict[email][0],unixtime)
                        mydict[email][1]+=1
    return mydict
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

def getMessage(service,user_id,message_id,flag):
    try:
        messageList = service.users().messages().get(userId = user_id, id = message_id, format = 'raw').execute()
        rawForm = base64.urlsafe_b64decode(messageList['raw'].encode('ASCII'))
        stringForm = email.message_from_bytes(rawForm)
        fromEmails = []
        # if flag == False:
            # print ("IN SENT EMAILS")
            # print ("FROM: ", stringForm['From'])
            # print ("TO: ", stringForm['To'])
            # print ("Date: ", stringForm['Date'])
            # print (".................")
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
            # emailSubject = stringForm['Subject']
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
            cc = stringForm['Cc']
            curperson = ""
            if cc:
            #     print ("*******")
            #     print ("WE HAVE REGULAR CC ")
            #     print ("*******")
                cc = deque(cc.split(' '))
                # print ("!!!!!")
                # print ("cc: ", cc)
                # print ("!!!!!")
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
            date = stringForm['Date']
            new = date.split(' ')
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
            date_time = None
            regDate = None
            unixTime = 0
            if year and month and day:
                date_time = datetime.datetime(year,month,day)
                regDate = datetime.date(year,month,day)
                unixTime = (time.mktime(date_time.timetuple()))
            return (fromEmails, toEmails, unixTime, hasGoogleMeet, regDate)
        else:
            return (None, None, None, None, None)
    except:
        return (None, None, None, None, None)

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
                    try:
                        fromEmails,toEmails,lastcontactUnix,hasGoogleMeet,regDate = getMessage(service,user_id,msg_id,flag)
                    except:
                        fromEmails,toEmails,lastcontactUnix,hasGoogleMeet,regDate = None,None,None,None,None
                    # print ('--3--')
                    # print (fromEmails,toEmails,lastcontactUnix,hasGoogleMeet,regDate)
                    if flag and lastcontactUnix and regDate: #going through inbox (so fromEmails)
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
                    elif not flag and lastcontactUnix and regDate: #if not flag, going through sent, so toEmail
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
                                        mydict[email][7]+=1
            else:
                print ("Empty inbox")
        doThing(searchIDinbox, True)
        print ("DID INBOX")
        doThing(searchIDsent, False)
        print ("DID SENT")
        return mydict
    except:
        return {}

# if __name__ == '__main__':
#     os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
#     app.run('localhost', 8000)