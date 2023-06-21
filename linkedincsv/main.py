import flask
from flask import Flask, redirect, url_for, request
import requests
import pandas as pd
import csv
import zipfile
import io
app = Flask(__name__)
app.secret_key = '_hkj97m_1j!!c7*n'
letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
titles = set(["mba","cpa","phd", "md","jd", "pmp","cfa","cfp", "cma", "pe", "cissp", "phr", "cfe", "cirsc", "cisa", "eit", "cfp", "ca", "ea"])
@app.route('/test',methods = ['POST', 'GET'])
def main():
   if request.method == 'POST':
       data = request.form
       userID = data['user_id']
       fileURL = data['file']
       url = "https://buckfifty.com/version-test/fileupload/f1687367486649x712366247971640800/Connections.csv"
       urlcsv = "https://buckfifty.com/version-test/fileupload/f1687367317489x356895471459457660/Basic_LinkedInDataExport_06-19-2023.zip"
       newnames = getInfoZIP(fileURL)
       newdict = {}
       for x in data:
           newdict[x] = data[x]
       return newdict
   else:
       return "GET"

def getInfoZIP(url):
    req = requests.get(urlcsv, stream = True)
    z = zipfile.ZipFile(io.BytesIO(req.content))
    namelist = z.namelist()
    count = 0
    initconnection = True
    for filename in namelist:
        for line in z.open(filename).readlines():
            curline = line.decode('utf-8')
            if filename == 'messages.csv' or filename == 'Messages.csv':
                continue
                # temp = curline.split(',')
                # c = 0
                # prev = None
                # namefrom = None
                # nameto = None
                # for x in temp:
                #     if "https://www.linkedin.com/in/" in x:
                #         if c == 0:
                #             namefrom = prev
                #             c+=1
                #         elif c == 1:
                #             nameto = prev
                #     prev = x
                # if namefrom and nameto:
                #     print (namefrom)
                #     print (nameto)
                #     print ("...........")
            if filename == 'Recommendations_Given.csv' or filename == 'recommendations_given.csv' or filename == "Recommendations_Received.csv" or filename == "recommendations_received.csv":
                temp = curline.split(',')
                if len(temp) > 2:
                    firstname = temp[0]
                    lastname = temp[1]
                    if firstname != 'First Name' and lastname != 'Last Name':
                        normalized = normalizeName(firstname,lastname)
            if filename == 'Connections.csv' or filename == 'connections.csv':
                temp = curline.split(',')
                if len(temp) >= 2:
                    firstname = temp[0]
                    lastname = temp[1]
                    if firstname and lastname and firstname != 'First Name' and lastname != 'Last Name':
                        if not initconnection:
                            normalized = normalizeName(firstname,lastname)
                            count+=1
                        initconnection = False
    return "HELLO TESTING POST REQUESTS"
def getInfoCSV(url):
    req = requests.get(url)
    content = req.content
    new = str(content)
    new1 = new.split("\\n")
    count = 0
    nameres = []
    for x in new1:
        temp = x.split(',')
        if len(temp) >= 2:
            firstname = temp[0]
            lastname = temp[1]
            if firstname and lastname:
                normalized = normalizeName(firstname,lastname)
                nameres.append(normalized)
                count+=1
    return nameres
    
def normalizeName(firstname,lastname):
    #take in 2 strings
    #firstname = \xe2\x98\x85\xe2\x98\x85\xe2\x98\x85 Klaas 
    #lastname = Baks PhD \xe2\x98\x85\xe2\x98\x85\xe2\x98\x85
    firstname = firstname.split(' ')
    lastname = lastname.split(' ')
    first = None
    firstmax = 0
    last = None
    lastmax = 0
    #split on space, iterate through each element, calculate ratio of alphabetic characters to total length, 
    #keep track of the element with the biggest ratio
    #Klass and Baks
    #when looking through lastname, check that the characters (all lowercase) don't form a title (ie mba, phd). If it does, don't include
    for n in firstname:
        if n:
            n = n.lower()
            reg = 0
            for i in range (len(n)):
                if n[i] in letters:
                    reg+=1
            ratio = 1.0*reg/len(n)
            if ratio > firstmax and n not in titles:
                firstmax = ratio
                first = n
    for n in lastname:
        if n:
            n = n.lower()
            reg = 0
            for i in range (len(n)):
                if n[i] in letters:
                    reg+=1
            ratio = 1.0*reg/len(n)
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
if __name__ == '__main__':
   app.run('localhost', 8000)
