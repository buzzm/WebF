import pymongo
from pymongo import MongoClient
import datetime

import WebF

import sys


#  m:p/help

class Func1:
    def __init__(self, db):
        self.db = db

    def help(self):
        return {"desc":"grimble",
                "args":[
                {"name":"startTime", "type":"datetime","req":"Y","desc":"foo"},
                {"name":"endTime", "type":"datetime","req":"N","desc":"foo"}
                ]}
    
    def start(self, args):
        self.args = args
        return {"foo":"bar"}
        
    def next(self):
        for doc in self.db['product'].find():
            yield doc

    def end(self):
        pass

def logF(doc):
    print doc


def main(args):
    client = MongoClient()
    db = client['testX']

    r = WebF.WebF(args)

    r.registerFunction("helloWorld", Func1(db))

    r.registerLogger(logF)

    print "Waiting."
    r.go()


main(sys.argv)



