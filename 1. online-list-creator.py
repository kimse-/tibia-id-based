import pymongo
import requests
import json
import time
import sys
from pathlib import Path
import tibiapy
import aiohttp
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


# python version of JavaScript setInterval()
def setInterval(func,time):
    e = threading.Event()
    while not e.wait(time):
        func()

#list of world names
worlds = ['Estela', 'Kenora', 'Peloria', 'Premia', 'Vunira']

#API call for the world online lists
def force_get_world(world):
    try:
        response = requests.get("https://api.tibiadata.com/v2/world/" + world + ".json")
        world = json.loads(response.content)
        return world
    except:
        force_get_world(world)


#
# the purpose of this entire script is to  mentioned 
# fetch the online list of characters for each world
# and log the activity (login/logout) times of each character
# and if the characters isn't tracked, then add it to the char scan queue so it gets added by 2. char-queue-scanner.py
#

def OnlineListChecker():
    tid = datetime.datetime.now()
    print(str(tid) + ' - OnlineListChecker - Triggering update...')
    # a lot of try/except to avoid the scripts seizing if the API stops responding etc. This needs to run 24/7
    try:
        for world in worlds:
            #force_get_world(world)
            jsonObj = force_get_world(world)
            worldData = jsonObj['world']
            players = worldData['players_online']
            lastUpdate = jsonObj['information']['last_updated']

            # store the most recent API call in online-list-new collection
            for x in players:
                dbinsert1 = { "name": x['name'], "vocation": x['vocation'], "level": x['level'], "world": world, "status": "online", "login_time": lastUpdate }
                mycolNEW.insert_one(dbinsert1)
                # update eventual level and vocation changes     !!!!!!!!!!!!!!!!---A COMMENT/REMINDER FOR ME---> could be optimized to skip needing 2.char-queue-scanner
                if mycolOLD.count_documents({ "name": x['name'] }) == 1:
                    findChar = { "name": x['name'] }
                    updateValues = { "$set": { "vocation": x['vocation'], "level": x['level'] } }
                    mycolOLD.update_one(findChar, updateValues)

            # compare online-list-new and online-list-old to spot who has logged out "for each character that has logged out..."
            findWorld = { "world": world }
            eachWorld = mycolOLD.find(findWorld)
            for x in eachWorld:
                if mycolNEW.count_documents({ "name": x['name'] }) < 1:
                    # if there is no charID in all-characters for the name, delete the entry
                    if x['charID'] == "":
                        dbdel = { "name": x['name'] }
                        mycolOLD.delete_one(dbdel)
                    # if there is a charID, then create an entry in activity-log and then delete the entry
                    else:
                        dbinsert1 = { "charID": x['charID'], "world": x['world'], "login_time": x['login_time'], "logout_time": lastUpdate }
                        mycolACT.insert_one(dbinsert1)
                        dbdel = { "name": x['name'] }
                        mycolOLD.delete_one(dbdel)

            # spot newly logged in characters in online-list-new and add them to online-list-old
            eachNWorld = mycolNEW.find(findWorld)
            for x in eachNWorld:
                # if the character isn't in the all-characters collection or the chan queue: add it to the char-scan-queue and then add it into the online-list-old collection
                if mycolALL.count_documents({ "name": x['name'] }) < 1:
                    if mycolSCAN.count_documents({ "name": x['name'] }) < 1:
                        dbinsert1 = { "name": x['name'] }
                        mycolSCAN.insert_one(dbinsert1)
                    if mycolOLD.count_documents({ "name": x['name'] }) < 1:
                        dbinsert1 = { "charID": "", "name": x['name'], "vocation": x['vocation'], "level": x['level'], "world": x['world'],  "login_time": x['login_time'] }
                        mycolOLD.insert_one(dbinsert1)
                # if the character is in the all-characters collection:
                else:
                    i = mycolALL.find_one({"name": x['name']})
                    if mycolOLD.count_documents({ "name": x['name'] }) < 1:
                        dbinsert1 = { "charID": i['charID'], "name": x['name'], "vocation": x['vocation'], "level": x['level'], "world": x['world'],  "login_time": x['login_time'] }
                        mycolOLD.insert_one(dbinsert1)
            # empty online-list-new
            mycolNEW.delete_many({})
    except:
        pass

# start-up process
# I always empty online-list-old first so that I dont accidentally get any activity-log entries that are >24h, which would be almost impossible in this game.
# I'd rather have two multi-hour entries with a max 5min gap instead of accidentally have a >24h entry
# I feel it's good housekeeping.
mycolOLD.delete_many({})
OnlineListChecker()
setInterval(OnlineListChecker, 1)
