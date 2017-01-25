import BaseHTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from SocketServer import ThreadingMixIn

import urllib
import datetime
import mson
import json

#  See stackoverflow.com for this.  Excellent.
class MultiThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
   pass


class WebF:
    class internalHelp:
        def __init__(self, parent):
            self.parent = parent

        def help(self):
            return {}

        def start(self, args):
            pass
        
        def next(self):
            for fname in self.parent.fmap:
                if False == fname.startswith('__'):
                    hh = self.parent.fmap[fname]
                    hdoc = {
                        "funcname": fname,
                        "args": hh.help()
                        }
                    yield hdoc

        def end(self):
            pass


    class internalArgErr:
        def __init__(self, parent):
            self.parent = parent
            self.args = {}

        def start(self, args):
            self.args = args
        
        def next(self):
            for fname in self.parent.fmap:
                if False == fname.startswith('__'):
                    hh = self.parent.fmap[fname]
                    hdoc = {
                        "funcname": fname,
                        "args": hh.help()
                        }
                    yield hdoc

        def end(self):
            pass



    class HTTPHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            (func,params) = self.parse(self.path)
            self.call(func, params, None)

        def parse(self, reqinfo):
            #print "parse ", reqinfo
            params = {}
            if '?' in reqinfo:
                func, params = reqinfo.split('?', 1)
                params = dict([p.split('=', 1) for p in params.split('&') if '=' in p])
                for k in params:
                    params[k] = urllib.unquote(params[k])
            else:
                func = reqinfo

            func = func.strip('/')

            return ((func, params))
        

        def chkArgs(self, funcHelp, webArgs):
            argerrs = []
            if 'args' in funcHelp:
                for hargs in funcHelp['args']:
                    if hargs['req'] == "Y":
                        if hargs['name'] not in webArgs:
                            argerrs.append({
                                    "errcode":1,
                                    "desc":"req arg not found",
                                    "data":hargs['name']})
            return argerrs
                            
            

        def call(self, func, params, content):
            xx = self.server.parent

            try:
                ss = datetime.datetime.now()

                # The Exception:
                # If func = "help" then it's "__help"  It is The One 
                # function that bridges internal and external handling.
                if func == "help":
                    func = "__help"
                
                if func not in xx.fmap:
                    self.send_response(404)

                else:
                    handler = xx.fmap[func]

                    args = json.loads(params['args']) if 'args' in params else {}
                    fargs = json.loads(params['fargs']) if 'fargs' in params else {}
                    fmt = None;  #  TBD:  default?
                    if fargs is not None:
                        if "fmt" in fargs:
                            fmt = fargs["fmt"].lower()

                    zz = handler.help()

                    argerrs = self.chkArgs(zz, args)

                    if len(argerrs) > 0:
                        handler = xx.fmap['__argErr']                        
                                

                    self.send_response(200)

                    jfmt = None
                    if fmt == "bson":
                        self.send_header('Content-type', 'text/bson')
                    else:
                        self.send_header('Content-type', 'text/json')
                        jfmt = mson.PUREJSON
                        if fmt == "ejson":
                            jfmt = mson.MONGODB


                    hdrdoc = handler.start(args)
                    if hdrdoc != None:
                        mson.emitDict(self.wfile, hdrdoc, jfmt)


                    # TBD TBD !!!
                    #    Gotta do something rational with this!
                    # CORS!  Trust our own local tomcat:
                    self.send_header('Access-Control-Allow-Origin', 'http://localhost:8087')
                    self.end_headers()

                    for r in handler.next():
                        mson.emitDict(self.wfile, r, jfmt)
                
                    footerdoc = handler.end()
                    if footerdoc != None:
                        mson.emitDict(self.wfile, hdrdoc, jfmt)

                    ee = datetime.datetime.now()

                    if xx.log_handler != None:

                        user = self.headers.getheader('X-AVL-User')
                        if user == None:
                            user = "ANONYMOUS"

                        #diffms = int((ee - ss)/1000)
                        tdelta = ee - ss
                        diffms = int(tdelta.microseconds/1000)

                        xx.log_handler({
                                "user": user,
                         "func": func,
                         "params": params,
                         "stime": ss,
                         "etime": ee,
                         "millis": diffms,
                         "status": "OK"})


            except Exception, e:
                self.wfile.write(e)
                raise e



    def __init__(self, args):
        self.fmap = {}
        self.rargs = {}

        listen_addr = "localhost"
        listen_port = 7778

        self.httpd = MultiThreadedHTTPServer((listen_addr, listen_port), WebF.HTTPHandler)

        self.log_handler = None   # optional

        self.registerFunction("__help", self.internalHelp(self));
        self.registerFunction("__argErr", self.internalArgErr(self));


        self.httpd.parent = self


    def registerFunction(self, name, handler):
        self.fmap[name] = handler

    def registerLogger(self, handler):
        self.log_handler = handler


    def go(self):
        self.httpd.serve_forever()

    def tickle(self, funcname, args):
        self.process(funcname, args)
