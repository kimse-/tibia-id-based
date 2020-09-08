import requests
import json
import time
import pymongo
import datetime
import threading

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb1 = myclient["fluid-data"]
mydb2 = myclient["static-data"]
mydb3 = myclient["master-data"]
mycolNEW = mydb1["online-list-new"]
mycolOLD = mydb1["online-list-old"]
mycolSCAN = mydb3["char-scan-queue"]
mycolACT = mydb3["activity-log"]
mycolDEA = mydb3["deathlist"]
mycolFRAG = mydb3["death-fraggers"]
mycolALL = mydb3["all-characters"]
mycolCHANGE = mydb3["change-log"]
mycollACCS = mydb3["accounts"]

def setInterval(func,time):
    e = threading.Event()
    while not e.wait(time):
        func()

#
# this compares the data available in online-list-old with the data available in all-characters
# specifically level, vocation or world changes
# it also updates the last_login time but that's less important
# if there is a change, it gets logged accordingly and then the all-characters record is updated
# 
#

def CharChangeChecker():
    for x in mycolOLD.find():
        if mycolALL.count_documents({ "charID": x['charID'] }) > 0:
            y = mycolALL.find_one({ "charID": x['charID'] })
            # here I check if the world has changed
            # I also print this so I get an easy 'at a glance' view of any world changes related to the worlds I play
            if x['world'] != y['world']:
                print(x['name'] + " - " + str(x['level']) + x['vocation'] + " - FROM: " + y['world'] + " TO: " + x['world'])
                dbinsert1 = { "charID": x['charID'], "value": "worldchange", "old_value": y['world'], "new_value": x['world'], "date": datetime.datetime.now()}
                mycolCHANGE.insert_one(dbinsert1)
                myquery = { "charID": x['charID'] }
                newvalues = { "$set": { "world": x['world'] } }
                mycolALL.update_one(myquery, newvalues)
            # here I check if the vocation has changed
            if x['vocation'] != y['vocation']:
                dbinsert1 = { "charID": x['charID'], "value": "vocationchange", "old_value": y['vocation'], "new_value": x['vocation'], "date": datetime.datetime.now()}
                mycolCHANGE.insert_one(dbinsert1)
                myquery = { "charID": x['charID'] }
                newvalues = { "$set": { "vocation": x['vocation'] } }
                mycolALL.update_one(myquery, newvalues)
            # here I check if the level has changed
            if x['level'] != y['level']:
                dbinsert1 = { "charID": x['charID'], "value": "levelchange", "old_value": y['level'], "new_value": x['level'], "date": datetime.datetime.now()}
                mycolCHANGE.insert_one(dbinsert1)
                myquery = { "charID": x['charID'] }
                newvalues = { "$set": { "level": x['level'] } }
                mycolALL.update_one(myquery, newvalues)
            # here I check if the last_login has changed
            if x['login_time'] != y['last_login']:
                myquery = { "charID": x['charID'] }
                newvalues = { "$set": { "last_login": x['login_time'] } }
                mycolALL.update_one(myquery, newvalues)                
        else:
            pass


# the reason why I have "two" triggers for the function
# is that sometimes I dont want to wait the 15 seconds the setInterval needs before it launches the function :PP

CharChangeChecker()
setInterval(CharChangeChecker, 15)
