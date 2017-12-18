
import WebF

class Func1:
    def __init__(self, context):
        self.maxCount = 0
        pass
        
    # curl -g 'http://localhost:7778/helloWorld?args={"maxCount":3}'
    def help(self):
        return {"type":"simple",
                "desc":"A function that returns something.",

                "args":[

                {"name":"startTime", "type":"datetime","req":"N",
                 "desc":"Starting time for snacking"},

                {"name":"maxCount", "type":"int","req":"Y",
                 "desc":"max number of snacks"}
                ]}
    

    def authenticate(self, headers, args):
        return (True, "buzz")
        #return (False, "buzz", {"msg":"failed to login"})

    def start(self, cmd, hdrs, args, rfile):
        print "START!"
        print hdrs

        # maxCount must be in args because it is required:
        self.maxCount = args['maxCount']

        for k in args:
            value = args[k]
            print k, value.__class__.__name__, value

        return (200, None)

    def next(self):
        for n in range(0, self.maxCount):
            doc = {"name":"chips", "type":n}
            yield doc

#    No need to specify if not being used...
#    def end(self):
#        pass

def logF(doc):
    print doc

def main():

    webfArgs = {
        "port":7778,
#        "sslPEMKeyFile":"/Users/buzz/git/Webf/server.pem",
        "cors":'*'
        }

    r = WebF.WebF(webfArgs)

    r.registerFunction("helloWorld", Func1, None);
    r.registerLogger(logF)

    print "ready"

    r.go()


main()




