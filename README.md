# tibia-id-based

to run all of this, you need at least:
pymongo
requests
tibiapy
time
json
datetime

Might be some more, just check the import of the scripts... :P

I know that most of the files include imports and mongo collection references that arent used.
That's because I've decided to just copy/paste the top for each script.
That way I don't have to re-write anything if I forget to write it at the start.
tl:dr - im lazy :D

Of the 24/7 scripts, ideally the scripts are started in order:
1. online-list-creator.py
2. char-queue-scanner.py
3. char-change-checker.py

Of the ad hoc scripts, start them whenever:
,5. scan-update-all-chars.py
,300. extract-guild-exp-per-day

The numbering is only so they are listed in the order I want them in my normal folder.
There are probably more "best practice"-ways of achieving the same thing but this works for me.

I've tried to do as much commenting as possible in each file without repeating myself too much.
If you read the files in order (1,2,3,5,300), you should be able to follow along my very un-pythonic code with ease.
