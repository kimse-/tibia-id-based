import requests
import json
import time
import pymongo
import datetime
import threading
import tibiapy
import sys
from datetime import datetime

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb3 = myclient["master-data"]
mycollACCS = mydb3["accounts"]
mycolACT = mydb3["activity-log"]
mycolALL = mydb3["all-characters"]
mycolCHANGE = mydb3["change-log"]
mycolFRAG = mydb3["death-fraggers"]
mycolDEA = mydb3["deathlist"]


def force_get_guild_json(name):
    url = tibiapy.Guild.get_url(name)
    try:
        r = requests.get(url)
        content = r.text
        data = tibiapy.Guild.from_content(content)
        guild = json.loads(data.to_json())
        time.sleep(0.5)
        return guild
    except:
        force_get_guild_json(name)

guilds = ['Triggered', 'Under Siege', 'Nevermind', 'Reapers', 'Sleepers', 'Here to Stay', 'Senpais', 'Non Lifers', 'Slaughters']



startmonth = 9
endmonth = 9
startday = 6
endday = 7

#
# this script gives me an output that shows the exp gain of each guild for the period assigned above
# the force_get again uses tibiapy and the guildData['members'] is a list of character names that are in the guild called
#
# the reason why I have a manual date entry (startmonth, endmonth, ...) is that I dont run this every day and I only need the output for the days that I missed
# the output is stored separately in an excel file
#
# the way it's running right now, doing a "for each day since the tracking begun" would take days/weeks
# as of writing this comment, I started the script at 11:25 and at 14:20, 3 hours later, it's still not complete
# I'm 10000% certain it's because I'm not doing it efficiently at all
# but as it's not something where I'm in a rush, I havent been arsed learning how to improve it further
# the output when done looks something like this: 
# 7	Triggered	1215067600.0
# 7	Under Siege	189715000.0
# 7	Nevermind	1242534000.0
# 7	Reapers	619322400.0
# 7	Sleepers	386629700.0
# 7	Here to Stay	1032407600.0
# ....
#
#
#


def extract_exp_gain():
    for guild in guilds:
        guildData = force_get_guild_json(guild)
        if guildData != None:
            guildMembers = guildData['members']
            # the reason why I run this loop was on a hunch that it would make the script complete faster
            # after testing, instead of taking 20+ hours, it now completes in approx 4-5hrs
            # all the loop does is de-select any player that hasnt gained/lost exp in the time period selected
            members = []
            for member in guildMembers:
                start = datetime(2020, startmonth, startday, 0, 0, 0)
                end = datetime(2020, endmonth, endday, 0, 0, 0)
                if mycolALL.count_documents({"name": member['name']}) > 0:
                    y = mycolALL.find_one({"name": member['name']})
                    if mycolCHANGE.count_documents({"charID": y['charID'], "date": {'$gte': start, '$lt': end}, "value": "levelchange"}) > 0:
                        members.append(y['charID'])
                    else:
                        pass
            guildExpTaken = 0
            start = datetime(2020, startmonth, startday, 0, 0, 0)
            end = datetime(2020, endmonth, endday, 0, 0, 0)
            for x in members:
                if mycolCHANGE.count_documents({"charID": x, "date": {'$gte': start, '$lt': end}, "value": "levelchange"}) > 0:
                    for z in mycolCHANGE.find({"charID": x, "date": {'$gte': start, '$lt': end}, "value": "levelchange"}):
                        oldlvl = z['old_value']
                        newlvl = z['new_value']
                        oldexp = ( 50 * (oldlvl - 1) ** 3 - 150 * (oldlvl - 1) ** 2 + 400 * (oldlvl - 1)) / 3
                        newexp = ( 50 * (newlvl - 1) ** 3 - 150 * (newlvl - 1) ** 2 + 400 * (newlvl - 1)) / 3
                        expchange = newexp - oldexp
                        guildExpTaken += expchange
                else:
                    pass
            print(str(startday) + "\t" + guild + "\t" + str(guildExpTaken))


extract_exp_gain()