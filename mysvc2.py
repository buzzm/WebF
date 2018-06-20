import pymongo
from pymongo import MongoClient

import WebF

import logging
import argparse
import sys


class Func1:
    def __init__(self, context):
        self.parent = context['parent']
        self.cursor = None

    def help(self):
        return {"desc":"Fetch product info from DB",
                "args":[
                {"name":"productType", "type":"array","req":"N","desc":"fetch only products of this type(s)"}
                ]}
    

    def start(self, cmd, hdrs, args, rfile):
        logging.info("YO start()")

        pred = {}  # Fetch all
        if 'productType' in args:
            logging.info("subset requested")
            pred = {"prodType": {"$in": args['productType']}}

        # Set up cursor:
        self.cursor = self.parent.db['product'].find(pred)
        
        # Assume all OK; normally we'd catch exceptions and such.  We'll
        # let the next() method iterate over the cursor:
        return (200, None)

    def next(self):
        for doc in self.cursor:
            doc['val'] = self.parent.fancyCalculation(5,6)
            yield doc


class MyProgram:
    def __init__(self, rargs):
        self.rargs = rargs

        client = MongoClient(host=self.rargs.host)
        self.db = client['testX']

        webfArgs = {
            "port":self.rargs.port,
            "cors":'*'
            }

        if 'cert' in self.rargs:
            webfArgs['sslPEMKeyFile'] = self.rargs.cert
            print "activating SSL"

        self.websvc = WebF.WebF(webfArgs)

        # Give the Func1 access to the complete parent!
        self.websvc.registerFunction("getProducts", Func1, {"parent": self})

        # Give the authenticator access to the complete parent!
        self.websvc.registerAuthentication(self.authF, self)


    def run(self):
        print "settling into loop..."
        self.websvc.go()  # drop into loop

    def fancyCalculation(self, a, b):
        return a + b

    #
    #  The auth method is "not part of this class"; it is for the WebF
    #  framework.   WebF will be calling it as if it is a standalone
    #  function so it must be declared staticmethod here:
    @staticmethod
    def authF(instance, context, hdrs, args):
        print "instance:",instance
        print "context:", context
        print "hdrs:",hdrs
        print "args:",args
        #return (False, "buzz", {"msg":"failed to login"})
        return (True, "buzz")


def main(args):
    parser = argparse.ArgumentParser(description=
   """A service to fetch products
   """,
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
   )

    parser.add_argument('--host',
                        metavar='mongoDBhost',
                        default="mongodb://localhost:27017",
                        help='connection string to product DB7')

    parser.add_argument('--port',
                        type=int,
                        metavar='int',
                        default=9119,    # 9119  !
                        help='port upon which to listen')

    parser.add_argument('--cert',
                        metavar='key+cert file',
                        help='cert file to activate SSL mode')

    parser.add_argument('--log', choices=['DEBUG', 'INFO'],
                        help='level below WARNING to emit in logs.  WARNING, ERROR, and CRITICAL are always logged')


    rargs = parser.parse_args()

    loglevel = 30   # see logging docs for levels; 30 is WARNING
    if rargs.log == 'INFO':
        loglevel = 20
    elif rargs.log == 'DEBUG':
        loglevel = 10
            
    logging.basicConfig(format="%(asctime)-15s:%(levelname)s:%(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=loglevel
                    )

    r = MyProgram(rargs)
    r.run()

if __name__ == "__main__":
    main(sys.argv)



