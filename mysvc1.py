
import WebF

class Func1:
    def help(self):
        return {"desc":"A function that returns something.",
                "args":[
                {"name":"startTime", "type":"datetime","req":"Y",
                 "desc":"Starting time for snacking"},
                {"name":"maxCount", "type":"int","req":"N",
                 "desc":"max number of snacks"}
                ]}
    
    def start(self, args):
        pass
        
    def next(self):
        for doc in [{"name":"chips", "type":6},
                      {"name":"fruit", "type":1}]:
            yield doc

    def end(self):
        pass


def main():
    r = WebF.WebF({})
    r.registerFunction("helloWorld", Func1())
    r.go()


main()




