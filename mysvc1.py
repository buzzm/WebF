
import WebF

class Func1:
    def __init__(self, context):
        pass
        
    def help(self):
        return {"type":"simple",
                "desc":"A function that returns something.",
                "args":[
                {"name":"startTime", "type":"datetime","req":"Y",
                 "desc":"Starting time for snacking"},
                {"name":"maxCount", "type":"int","req":"N",
                 "desc":"max number of snacks"}
                ]}
    
    def start(self, args):
        for k in args:
            value = args[k]
            print k, value.__class__.__name__, value
        
    def next(self):
        for doc in [{"name":"chips", "type":6},
                      {"name":"fruit", "type":1}]:
            yield doc

    def end(self):
        pass


def logF(doc):
    print doc

def main():
    r = WebF.WebF({})

    r.registerFunction("helloWorld", Func1, None);
    r.registerLogger(logF)

    r.go()


main()




