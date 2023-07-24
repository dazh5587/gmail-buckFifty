import flask
from flask import Flask, redirect, url_for, request
import requests
import zipfile
import io
import pandas as pd
import ssl

app = Flask(__name__)
app.secret_key = '_hkj97m_1j!!c7*n'
letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
ssl._create_default_https_context = ssl._create_unverified_context
titles = set(["mba","cpa","phd", "md","jd", "asa", "cera", "pmp","cfa","cfp", "cma", "pe", "cissp", "phr", "cfe", "cirsc", "cisa", "eit", "cfp", "ca", "ea", "cgma"])
@app.route('/')
def test():
    url = "https://46bf5c50fffa688e7a15392847fa5453.cdn.bubble.io/f1689885782467x655530771889034640/messages.csv"
    storage_options = {'User-Agent': 'Mozilla/5.0'}
    df = pd.read_csv(url, on_bad_lines='skip', storage_options=storage_options)
    from_people = df["FROM"]
    to_people = df["TO"]
    #mydict = getMessage(url)
    return "GOOD!!"

@app.route('/test',methods = ['POST', 'GET'])
def main():
    if request.method == 'POST':
        data = request.form
        userID = data['user_id']
        fileURL = data['file']
        version = data['version'] #if yes, its staging, if no its live
        if version == "yes":
            bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/linkedin-import-in-progress/"
            bearer_token = '725b8d6584b071a02e1316945bf7743b'
            headers = {'Authorization': f'Bearer {bearer_token}'}
            for_post = {'user': userID, "status": "yes"}
            new = requests.post(bubble_url, json = for_post, headers = headers)
        else:
            bubble_url = "https://buckfifty.com/api/1.1/wf/linkedin-import-in-progress/"
            bearer_token = '725b8d6584b071a02e1316945bf7743b'
            headers = {'Authorization': f'Bearer {bearer_token}'}
            for_post = {'user': userID, "status": "yes"}
            new = requests.post(bubble_url, json = for_post, headers = headers)
        mydict = {}
        if "messages" in fileURL or "Messages" in fileURL:
            mydict = getMessage(fileURL)
        elif "Recommendations" in fileURL or "recommendations" in fileURL:
            mydict = getRecs(fileURL)
        if version == "yes": #testing
            bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/create-or-update-connection/"
            bearer_token = "725b8d6584b071a02e1316945bf7743b"
        else:
            bubble_url = "https://buckfifty.com/api/1.1/wf/create-or-update-connection/"
            bearer_token = "725b8d6584b071a02e1316945bf7743b"
        headers = {'Authorization': f'Bearer {bearer_token}'}
        odict = {True:'yes', False:'no'}
        for x in mydict:
            for_post = {"Full Name": x, "LI_messages_to": mydict[x][1],"LI_messages_from": mydict[x][0],"LI_recommendations": mydict[x][2],'Created By (custom)': userID, "Source": "LinkedIn", "Potential Key Relationship": True}
            if mydict[x][0] > 0 and mydict[x][1] == 0:
                continue
            else:
                new = requests.post(bubble_url, json = for_post, headers = headers)
        if version == "yes":
            bubble_url = "https://buckfifty.com/version-test/api/1.1/wf/linkedin-import-in-progress/"
            bearer_token = '725b8d6584b071a02e1316945bf7743b'
            headers = {'Authorization': f'Bearer {bearer_token}'}
            for_post = {'user': userID, "status": "no"}
            new = requests.post(bubble_url, json = for_post, headers = headers)
        else:
            bubble_url = "https://buckfifty.com/api/1.1/wf/linkedin-import-in-progress/"
            bearer_token = '725b8d6584b071a02e1316945bf7743b'
            headers = {'Authorization': f'Bearer {bearer_token}'}
            for_post = {'user': userID, "status": "no"}
            new = requests.post(bubble_url, json = for_post, headers = headers)
        return mydict
    else:
       return "GET"
def getMessage(url):
    storage_options = {'User-Agent': 'Mozilla/5.0'}
    df = pd.read_csv(url, on_bad_lines='skip', storage_options=storage_options)
    from_people = df["FROM"]
    to_people = df["TO"]
    mydict = {}
    for i in range (len(from_people)):
        cur = normalizeName2(from_people[i])
        if cur not in mydict:
            mydict[cur] = [1,0,0,True]
        else:
            mydict[cur][0]+=1
    for i in range (len(to_people)):
        cur = normalizeName2(to_people[i])
        if cur not in mydict:
            mydict[cur] = [0,1,0,True]
        else:
            mydict[cur][1]+=1
    return mydict

def getRecs(url):
    storage_options = {'User-Agent': 'Mozilla/5.0'}
    df = pd.read_csv(url, on_bad_lines='skip', storage_options=storage_options)
    mydict = {}
    for index,row in df.iterrows():
        name = row["First Name"]+row["Last Name"]
        cur = normalizeName2(name)
        if cur not in mydict:
            mydict[cur] = [0,0,1,True]
        else:
            mydict[cur][2]+=1
    return mydict

def normalizeName2(name):
    #take in 2 strings
    #firstname = \xe2\x98\x85\xe2\x98\x85\xe2\x98\x85 Klaas 
    #lastname = Baks PhD \xe2\x98\x85\xe2\x98\x85\xe2\x98\x85
    new = name.split(' ')
    first = None
    firstmax = 0
    last = None
    lastmax = 0
    #split on space, iterate through each element, calculate ratio of alphabetic characters to total length, 
    #keep track of the element with the biggest ratio
    #Klass and Baks
    #when looking through lastname, check that the characters (all lowercase) don't form a title (ie mba, phd). If it does, don't include
    for n in new:
        if n:
            n = n.lower()
            while n and n[-1] == ',':
                n = n[:-1]
            reg = 0
            for i in range (len(n)):
                if n[i] in letters:
                    reg+=1
            ratio = 1.0*reg/len(n)
            if ratio > firstmax and n not in titles:
                firstmax = ratio
                first = n
            if ratio >= lastmax and n not in titles:
                lastmax = ratio
                last = n
    newfirst = ""
    index = 0
    #go through the first name and last name with the best ratios, get rid of emojis and extra quotation marks 
    while index < len(first):
        if index+1 < len(first) and first[index:index+2] == "\\x": #if there is a \x, that means emoji pattern and continue
            index+=4
        elif index+1 < len(first) and first[index:index+2] == "\\'": #if there is a \' pattern, means theres a name like "o'malley" and keep
            newfirst+="'"
            index+=2
        elif first[index] in letters:
            newfirst+=first[index]
            index+=1
        else:
            index+=1
    newlast = ""
    index = 0
    while index < len(last):
        if index+1 < len(last) and last[index:index+2] == "\\x":
            index+=4
        elif index+1 < len(last) and last[index:index+2] == "\\'":
            newlast+="'"
            index+=2
        elif last[index] in letters:
            newlast+=last[index]
            index+=1
        else:
            index+=1
    newfirst = newfirst.capitalize()
    newlast = newlast.capitalize()
    return newfirst + ' '+ newlast
# def getInfoZIP(url):
#     req = requests.get(url, stream = True)
#     z = zipfile.ZipFile(io.BytesIO(req.content))
#     namelist = z.namelist()
#     count = 0
#     initconnection = True
#     namedict = {} #name: messages from, messages to, recommendations, Potential KR
#     for filename in namelist:
#         for line in z.open(filename).readlines():
#             curline = line.decode('utf-8')
#             if filename == 'messages.csv' or filename == 'Messages.csv':
#                 temp = curline.split(',')
#                 c = 0
#                 prev = None
#                 namefrom = None
#                 nameto = None
#                 for x in temp:
#                     x = x.lower()
#                     if "https://www.linkedin.com/in/" in x:
#                         if c == 0:
#                             namefrom = prev
#                             c+=1
#                         elif c == 1:
#                             nameto = prev
#                     while x and x[0] not in letters:
#                         x = x[1:]
#                     while x and x[-1] not in letters:
#                         x = x[:-1]
#                     if x not in titles:
#                         prev = x
#                 if namefrom and nameto:
#                     namefrom = namefrom.title()
#                     nameto = nameto.title()
#                     if namefrom not in namedict:
#                         namedict[namefrom] = [1,0,0, True]
#                     else:
#                         namedict[namefrom][0]+=1
#                         namedict[namefrom][3] = True
#                     if nameto not in namedict:
#                         namedict[nameto] = [0,1,0,True]
#                     else:
#                         namedict[nameto][1]+=1
#                         namedict[nameto][3] = True
#             if filename == 'Recommendations_Given.csv' or filename == 'recommendations_given.csv' or filename == "Recommendations_Received.csv" or filename == "recommendations_received.csv":
#                 temp = curline.split(',')
#                 if len(temp) > 2:
#                     firstname = temp[0]
#                     lastname = temp[1]
#                     if firstname != 'First Name' and lastname != 'Last Name':
#                         normalized = normalizeName(firstname,lastname)
#                         if normalized not in namedict:
#                             namedict[normalized] = [0,0,1,True]
#                         else:
#                             namedict[normalized][2]+=1
#                             namedict[normalized][3] = True
#             if filename == 'Connections.csv' or filename == 'connections.csv':
#                 continue
#                 # temp = curline.split(',')
#                 # if len(temp) >= 2:
#                 #     firstname = temp[0]
#                 #     lastname = temp[1]
#                 #     if firstname and lastname and firstname != 'First Name' and lastname != 'Last Name':
#                 #         if not initconnection:
#                 #             normalized = normalizeName(firstname,lastname)
#                 #             if normalized not in namedict:
#                 #                 namedict[normalized] = [0,0,0,False]
#                 #             count+=1
#                 #         initconnection = False
#     return namedict
# def getInfoCSVConnections(url):
#     req = requests.get(url)
#     content = req.content
#     new = str(content)
#     new1 = new.split("\\n")
#     count = 0
#     namedict = {}
#     for x in new1:
#         temp = x.split(',')
#         if len(temp) >= 2:
#             firstname = temp[0]
#             lastname = temp[1]
#             if firstname and lastname:
#                 normalized = normalizeName(firstname,lastname)
#                 if normalized not in namedict:
#                     namedict[normalized] = [0,0,0,False]
#                 count+=1
#     return namedict

# def getInfoCSVRecs(url):
#     req = requests.get(url)
#     content = req.content
#     new = str(content)
#     new1 = new.split("\\n")
#     count = 0
#     namedict = {}
#     for x in new1:
#         temp = x.split(',')
#         if len(temp) >= 2:
#             firstname = temp[0]
#             lastname = temp[1]
#             if firstname and lastname:
#                 normalized = normalizeName(firstname,lastname)
#                 if normalized not in namedict:
#                     namedict[normalized] = [0,0,0,False]
#                 count+=1
#     return namedict

# def getInfoCSVMessages(url):
#     req = requests.get(url)
#     content = req.content
#     new = str(content)
#     new1 = new.split("\\n")
#     namedict = {}
#     for y in new1:
#         c = 0
#         prev = None
#         namefrom = None
#         nameto = None
#         temp = y.split(',')
#         for x in temp:
#             x = x.lower()
#             if "https://www.linkedin.com/in/" in x:
#                 if c == 0:
#                     namefrom = prev
#                     c+=1
#                 elif c == 1:
#                     nameto = prev
#             while x and x[0] not in letters:
#                 x = x[1:]
#             while x and x[-1] not in letters:
#                 x = x[:-1]
#             if x not in titles:
#                 prev = x
#         if namefrom and nameto:
#             namefrom = namefrom.title()
#             nameto = nameto.title()
#             if namefrom not in namedict:
#                 namedict[namefrom] = [1,0,0, True]
#             else:
#                 namedict[namefrom][0]+=1
#                 namedict[namefrom][3] = True
#             if nameto not in namedict:
#                 namedict[nameto] = [0,1,0,True]
#             else:
#                 namedict[nameto][1]+=1
#                 namedict[nameto][3] = True
#     return namedict

if __name__ == '__main__':
   app.run('localhost', 8000)
