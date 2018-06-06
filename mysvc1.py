#
# curl -g 'http://localhost:7778/helloWorld?args={"maxCount":3}'
#

import WebF

class Func1:
    def __init__(self, context):
        self.maxCount = 0
        pass
        
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

        if '_' in args:
            print "RESTful args: ", args['_']

        return (200, None)


    def next(self):
        for n in range(0, self.maxCount):
            doc = {"name":"chips", "type":n}
            yield doc

#    No need to specify if not being used...
#    def end(self):
#        pass



class Func2:
    def __init__(self, context):
        pass
        
    def help(self):
        return {"type":"simple",
                "desc":"print incoming rfile data stream to stdout"
                }

    def start(self, cmd, hdrs, args, rfile):
        print "CMD:", cmd
        print hdrs

        for k in args:
            value = args[k]
            print k, value.__class__.__name__, value

        if '_' in args:
            print "RESTful args: ", args['_']

        length = 0
        clenhdr = hdrs.getheader('content-length')
        if clenhdr != None:
            length = int(clenhdr)

        content = None

        if length > 0:
            print "slurp len", length
            content = rfile.read(length)

        print content

        return (200, None)





def logF(doc):
    print doc

def main():

    webfArgs = {
        "port":7778,
#        "sslPEMKeyFile":"/Users/buzz/git/Webf/newkey.pem",
        "cors":'*'
        }

    r = WebF.WebF(webfArgs)

    r.registerFunction("helloWorld", Func1, None);
    r.registerFunction("echo", Func2, None);

    r.registerLogger(logF)

    print "ready"

    r.go()


main()




