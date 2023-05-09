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
    res = getall()
    return res





class gmailAPI:
    def __init__(self):
        self.contactdict = {}
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] # If modifying these scopes, delete the file token.json.
        self.datedict = {"Jan":1,"Feb":2, "Mar":3,"Apr":4, "May": 5, "Jun": 6, "Jul": 7, "Aug":8, "Sep":9,"Oct":10, "Nov":11, "Dec":12}
        self.badwords = set(["feedback", "hello", "news", "newsletters", "no-reply", "noreply", "notifications", "notification", "team", "support", "billing", "info", "help", "newsletter", "blog", "updates"])
        self.letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    def getMessage(self,service,user_id,message_id):
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
                    if cur.split('@')[0] in self.badwords:
                        badwordflag = False
                    else:
                        while cur and cur[0] not in self.letters:
                            cur = cur[1:]
                        while cur and cur[-1] not in self.letters:
                            cur = cur[:-1]
                        if curperson:
                            curperson = curperson[:-1]
                            self.contactdict[cur] = curperson
                            fromPeople.append(curperson)
                        else:
                            if cur in self.contactdict:
                                fromPeople.append(self.contactdict[cur])
                    curperson = ""
                else:
                    curperson+=cur+' '
            toPerson = deque(stringForm['To'].split(' '))
            toPeople = []
            curperson = ""
            while toPerson:
                cur = toPerson.popleft()
                if '@' in cur:
                    while cur and cur[0] not in self.letters:
                        cur = cur[1:]
                    while cur and cur[-1] not in self.letters:
                        cur = cur[:-1]
                    if curperson:
                        curperson = curperson[:-1]
                        self.contactdict[cur] = curperson
                        toPeople.append(curperson)
                    else:
                        if cur in self.contactdict:
                            toPeople.append(self.contactdict[cur])
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
                date_time = datetime.datetime(int(new[3]),self.datedict[new[2]],int(new[1]),int(secs[0]),int(secs[1]),int(secs[2]))
                regDate = datetime.date(int(new[3]),self.datedict[new[2]],int(new[1])) #year, month, day
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

    def searchMessages(self, service,user_id):
        try:
            mydict = {}
            searchIDinbox = service.users().messages().list(userId = user_id, q = "label:inbox").execute() #get all emails in inbox
            searchIDsent = service.users().messages().list(userId = user_id, q = 'from: david@favorably.app').execute() #get emails that I sent
            def doThing(searchID, flag): #if flag = True, we're in inbox, look through from
                number_results = searchID['resultSizeEstimate']
                if number_results > 0:
                    message_ids = searchID['messages']
                    for ids in message_ids:
                        msg_id = ids['id']
                        fromPeople,toPeople,lastcontactUnix,hasGoogleMeet,regDate = self.getMessage(service,user_id,msg_id)
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



    def get_service(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=8000)
            # Save the credentials for the next run
            # with open('token.json', 'w') as token:
            #     token.write(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)
        return service

    def getall(self):
        service = self.get_service()
        mydict = self.searchMessages(service,"me")
        return mydict

if __name__ == '__main__':
    #app.run(debug = True, port=8000)
    new = gmailAPI()
    res = new.getall()
    print (res)
    #service = get_service()
    #print (service.users().messages().list(userId = 'me').execute())s