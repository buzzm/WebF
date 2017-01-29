import pymongo
from pymongo import MongoClient

import WebF

import sys

class Func1:
    def __init__(self, context):
        self.db = context['db']

    def help(self):
        return {"desc":"Fetch product info from DB",
                "args":[
                {"name":"productType", "type":"array","req":"N","desc":"fetch only products of this type(s)"}
                ]}
    
    def start(self, args):
        self.args = args

    def next(self):
        pred = {}  # Fetch all
        if 'productType' in self.args:
            pred = {"prodType": {"$in": self.args['productType']}}

        for doc in self.db['product'].find(pred):
            yield doc

    def end(self):
        pass


def main(args):
    client = MongoClient()
    db = client['testX']

    r = WebF.WebF(args)
    r.registerFunction("getProducts", Func1, {"db": db})
    r.go()

main(sys.argv)



