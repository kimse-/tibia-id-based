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
mycolDEA = mydb3["deathlist"]
mycolFRAG = mydb3["death-fraggers"]
mycolALL = mydb3["all-characters"]
mycolCHANGE = mydb3["change-log"]
mycollACCS = mydb3["accounts"]


def setInterval(func,time):
    e = threading.Event()
    while not e.wait(time):
        func()



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
        print("Blocked by Tibia")


worlds = ['Peloria', 'Estela', 'Vunira', 'Kenora', 'Premia']

#
#
# this is basically 2.char-queue-scanner.py
# but for characters already logged in the all-characters collection
# the reason why I have a for worlds-loop is that all-characters collection has >150k entries and 
# sometimes the "mouse cursor" times out (I cant recall the exact error message) and I've found that doing for world in worlds...
# helps with this issue
#
# I _know_ that isn't how you fix it but in my defence:
# 1. I'm fairly lazy
# 2. Google-fu hasnt helped me with an alternative
# 3. I only need to run this script once every 14~ days so it's NBD if I have to 'restart' it
#
# the reason why I have .sort([("level", -1)]) is because 
# the lower levelled a character is, the less important a recent complete scan is.
# basically once a character is below level 15, it doesnt really matter
#

def update_all_chars():
    death_ID = 0
    try:
        findDeathID = mycolDEA.find().sort([("deathID", -1)])
        for x in findDeathID:
            ID = x['deathID']
            ID += 1
            death_ID = ID
            break
    except:
        pass

    for world in worlds:
        for x in mycolALL.find({"world": world}).sort([("level", -1)]):
            if x['level'] > 8:
                print("Scanning charID: " + str(x['charID']) + ", which is character " + x['name'])
                charData = force_get_char_json(x['name'])
                if charData != None:
                    charName = charData['name']
                    charSex = charData['sex']
                    charVoc = charData['vocation']
                    charCity = charData['residence']
                    worldID = charData['world']
                    charID = x['charID']
                    charAS = charData['account_status']
                    charDeaths = charData['deaths']

                    if charName != x['name']:
                        dbinsert = { "charID": charID, "value": "namechange", "old_value": x['name'], "new_value": charName, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    if charVoc != x['vocation']:
                        dbinsert = { "charID": charID, "value": "vocationchange", "old_value": x['vocation'], "new_value": charVoc, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    if charSex != x['sex']:
                        dbinsert = { "charID": charID, "value": "sexchange", "old_value": x['sex'], "new_value": charSex, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    if charCity != x['city']:
                        dbinsert = { "charID": charID, "value": "citychange", "old_value": x['city'], "new_value": charCity, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    if worldID != x['world']:
                        dbinsert = { "charID": charID, "value": "worldchange", "old_value": x['world'], "new_value": worldID, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    if charAS != x['account_status']:
                        dbinsert = { "charID": charID, "value": "accountstatuschange", "old_value": x['account_status'], "new_value": charAS, "date": datetime.datetime.now() }
                        mycolCHANGE.insert_one(dbinsert)

                    # insert scanned death info
                    for y in charDeaths:
                        timeofdeath = y['time']
                        if mycolDEA.count_documents({'charID': charID, "timeofdeath": timeofdeath}) > 0:
                            pass
                        else:
                            death_ID += 1
                            levelondeath = y['level']
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
                                try:
                                    mycolFRAG.insert_one(dbinsert2)
                                except:
                                    pass
                            dbinsert3 = { "deathID": deathID, "charID": charID, "levelondeath": levelondeath, "timeofdeath": timeofdeath, "deathType": deathType, "expLoss": expLoss, "goldLoss": goldLoss }
                            mycolDEA.create_index([("deathID", pymongo.ASCENDING), ("charID", pymongo.ASCENDING), ("timeofdeath", pymongo.ASCENDING)], unique=True)
                            try:
                                mycolDEA.insert_one(dbinsert3)
                            except:
                                pass

                    myquery = { "charID": charID }
                    newvalues = { "$set": { "name": charName, "sex": charSex, "vocation": charVoc, "city": charCity, "world": worldID, "account_status": charAS } }
                    mycolALL.update_one(myquery, newvalues)
                else:
                    pass
            else:
                pass
    print('done')



print('Updating "all chars" collection...')
update_all_chars()
