import requests
import json
import time
import pymongo
import datetime
import threading
import tibiapy
import sys

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
# as tibia.com has anti-flooding and no API of it's own
# and I cant afford being flooded by the TibiaData API
# I have separated what I get from the API and what I get from tibia.com directly
# for character pages, I use tibiapy (1000% cred: Galarzaa90) for the tibia.com scraping
# hence the difference force_get method here compared to 1. online-list-creator
#
def force_get_char_json(name):
    url = tibiapy.Character.get_url(name)
    try:
        r = requests.get(url)
        content = r.text
        data = tibiapy.Character.from_content(content)
        char = json.loads(data.to_json())
        time.sleep(0.5)
        return char
    except:
        pass

#
#
# the purpose of this script is to process any of the characters added to the char-scan-queue collection by 1. online-list-creator.py
# if they dont exist: it adds them into all-characters
# if it does exist: update the name change of the character in all-characters and then make a record of it in change-log
#
#



def scan_the_queue_json():
    #
    # it always starts with fetching the highest available charID and deathID and +1 to both
    # my entire system is id-based, so all changes/deaths/etc links back to the characterID in all-characters
    # this way I dont have to update 3473846 collections every time a character changes name (or other changes)
    #
    identifier = 0
    death_ID = 0
    try:
        findCharID = mycolALL.find().sort([("charID", -1)])
        for x in findCharID:
            ID = x['charID']
            ID += 1
            identifier = ID
            break
    except:
        pass

    try:
        findDeathID = mycolDEA.find().sort([("deathID", -1)])
        for x in findDeathID:
            ID = x['deathID']
            ID += 1
            death_ID = ID
            break
    except:
        pass

    for x in mycolSCAN.find():
        existingChar = 0
        charData = force_get_char_json(x['name'])
        if charData != None:
            charName = charData['name']
            charSex = charData['sex']
            charVoc = charData['vocation']
            charLevel = charData['level']
            charAP = charData['achievement_points']
            charCity = charData['residence']
            guildID = 0
            worldID = charData['world']
            charID = identifier
            accID = 0
            if 'last_login' in charData:
                lastLoginDate = charData['last_login']
            else:
                lastLoginDate = 0
            charAS = charData['account_status']
            charFNames = charData['former_names']
            if 'former_world' in charData:
                charFWorld = charData['former_world']
            charDeaths = charData['deaths']
            # here I run through all potential former_names to see if the name is already present in all-characters
            # if it is present, it means (with 99.9999999%) certainty that the character recently (last 15min) changed name
            # if it is present, I update the all-character record then break the loop, as it's completed.
            for y in charFNames:
                if mycolALL.count_documents({"name": y}) > 0:
                    existingChar = 1
                    z = mycolALL.find_one({"name": y})
                    dbinsert4 = { "charID": z['charID'], "value": "namechange", "old_value": y, "new_value": charName, "date": datetime.datetime.now() }
                    mycolCHANGE.insert_one(dbinsert4)
                    query = {"name": y}
                    update = {"$set":{"name": charName}}
                    mycolALL.update_one(query, update)
                    dbdel = { "name": charName }
                    mycolSCAN.delete_many(dbdel)
                    break
                else:
                    pass

            # if existingChar is less than 1, this is a new char and we proceed to create an entry
            if existingChar < 1:
                identifier += 1
                # remove former names from scan queue, so I dont accidentally scan the same character multiple times in short succession
                # as mentioned before, anti-flooding measures is necessary, so less requests = good
                for y in charFNames:
                    dbinsert4 = { "charID": charID, "value": "namechange", "old_value": y, "new_value": charName, "date": datetime.datetime.now() }
                    mycolCHANGE.insert_one(dbinsert4)
                    dbdel = { "name": y }
                    mycolSCAN.delete_many(dbdel)

                if 'former_world' in charData:
                    former_world = charFWorld
                    dbinsert5 = { "charID": charID, "value": "worldchange", "old_value": former_world, "new_value": worldID, "date": datetime.datetime.now() }
                    mycolCHANGE.insert_one(dbinsert5)
                else:
                    pass


                # insert scan info to the all-chars collection and delete it from the scan queue
                # this creates the first ID-based record of the character in my tracking
                dbinsert1 = { "charID": charID, "name": charName, "level": charLevel, "vocation": charVoc, "world": worldID, "sex": charSex, "city": charCity, "last_login": lastLoginDate, "achievement_points": charAP, "account_status": charAS, "guild": guildID, "accountID": accID }
                mycolALL.create_index([("charID", pymongo.ASCENDING)], unique=True)
                try:
                    mycolALL.insert_one(dbinsert1)
                except:
                    pass
                dbdel = { "name": charName }
                mycolSCAN.delete_many(dbdel)

                # here I check the death-fraggers collection to see if the character names shows up
                # if it does, I replace the character name with the charID
                if mycolFRAG.count_documents({"name": charName}) > 0:
                    b = mycolALL.find_one({"name": charName})
                    query = {"charID": charName}
                    update = {"$set":{"charID": b['charID']}}
                    mycolFRAG.update_many(query, update)

                # insert all found deaths to the deathlist collection
                # each death gets one deathID
                # each killer gets entered into the death-fraggers collection either by name or charID
                for y in charDeaths:
                    death_ID += 1
                    levelondeath = y['level']
                    timeofdeath = y['time']
                    deathID = death_ID
                    deathType = "Undefined"
                    expLoss = 0
                    goldLoss = 0
                    killers = y['killers']
                    for z in killers:
                        char_ID = z['name']
                        if mycolALL.count_documents({"name": char_ID}) > 0:
                            a = mycolALL.find_one({"name": char_ID})
                            char_ID = a['charID']
                        dbinsert2 = { "deathID": deathID, "charID": char_ID }
                        mycolFRAG.create_index([("deathID", pymongo.ASCENDING), ("charID", pymongo.ASCENDING)], unique=True)
                        mycolFRAG.insert_one(dbinsert2)
                    dbinsert3 = { "deathID": deathID, "charID": charID, "levelondeath": levelondeath, "timeofdeath": timeofdeath, "deathType": deathType, "expLoss": expLoss, "goldLoss": goldLoss }
                    mycolDEA.create_index([("deathID", pymongo.ASCENDING), ("charID", pymongo.ASCENDING), ("timeofdeath", pymongo.ASCENDING)], unique=True)
                    try:
                        mycolDEA.insert_one(dbinsert3)
                    except:
                        pass

            else:
                dbdel = { "name": charName }
                mycolSCAN.delete_many(dbdel)
        else:
            pass



print('Scan queue scraper started...')
try:
    scan_the_queue_json()
except requests.exceptions.RequestException as e:  # This is the correct syntax
    print(e)
    sys.exit(1)
setInterval(scan_the_queue_json, 1)