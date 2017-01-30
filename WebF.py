import BaseHTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from SocketServer import ThreadingMixIn

import urllib
import datetime
from mson import mson


#  See stackoverflow.com for this.  Excellent.
class MultiThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
   pass


class WebF:
    class internalHelp:
        def __init__(self, context):
            self.parent = context['parent']

        def help(self):
            return {}

        def start(self, args):
            pass
        
        def next(self):
            for fname in self.parent.fmap:
                if False == fname.startswith('__'):
                    (href,context) = self.parent.fmap[fname]
                    hh = href(context)
                    hdoc = hh.help()
                    hdoc['funcname'] = fname
                    yield hdoc

        def end(self):
            pass



    class internalErr:
        def __init__(self, errs):
            self.errs = errs

        def start(self, args):
           pass
        
        def next(self):
            for err in self.errs:
               yield err

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
        

        def getArgTypeToString(self, argval):
           ss  = argval.__class__.__name__
           if ss == 'unicode':
              ss = "str"
           elif ss == 'float':           
              ss = "double"
           elif ss == 'Decimal':
              ss = "decimal"
           elif ss == 'list':
              ss = "array"
              
           return ss


        def chkArgs(self, funcHelp, webArgs):
            argerrs = []
            if 'args' in funcHelp:
                for hargs in funcHelp['args']:
                    if hargs['req'] == "Y":
                        if hargs['name'] not in webArgs:
                           argerrs.append({
                                    "errcode":1,
                                    "msg":"req arg not found",
                                    "data":hargs['name']})

                    if hargs['name'] in webArgs:
                       # exists: but is it the right type?
                       # any,string, int, long, double, decimal, datetime, binary, array, dict                           
                       argval = webArgs[hargs['name']]
                       argtype = hargs['type'];
                       if argtype != "any":
                          ss = self.getArgTypeToString(argval)
                          if ss != argtype:
                             argerrs.append({
                                    "errcode":2,
                                    "msg":"arg has wrong type",
                                    "data": {
                                      "arg": hargs['name'],
                                      "expected": argtype,
                                      "found": ss
                                      }})
    
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
                    user = None

                    (hname,context) = xx.fmap[func]

                    # Construct a NEW handler instance!
                    handler = hname(context)

                    args = mson.parse(params['args'], mson.MONGO) if 'args' in params else {}
                    fargs = mson.parse(params['fargs'], mson.MONGO) if 'fargs' in params else {}

                    fmt = None;  #  TBD:  default?
                    if fargs is not None:
                        if "fmt" in fargs:
                            fmt = fargs["fmt"].lower()

                    zz = handler.help()


                    contentType = 'text/json'
                    respCode = 200

                    jfmt = None
                    if fmt == "bson":
                       contentType = 'text/bson'
                    else:
                        jfmt = mson.PURE
                        if fmt == "ejson":
                            jfmt = mson.MONGO


                    argerrs = self.chkArgs(zz, args)

                    if len(argerrs) > 0:
                       handler = xx.internalErr(argerrs)
                       respCode = 400

                    else:
                       authMethod = getattr(handler, "authenticate", None)
                       if callable(authMethod):

                          # Expect (T|F, name, data)
                          tt2 = authMethod(self.headers, args)

                          user = tt2[1]

                          if tt2[0] == False:
                             err = {
                                'errcode': 3,
                                'user': user,
                                'msg': "authentication failure"
                                }
                             if len(tt2) == 3:
                                err['data'] = tt2[2]

                             handler = xx.internalErr([err])
                             respCode = 401

                    self.send_response(respCode)
                    self.send_header('Content-type', contentType)

                    # TBD TBD !!!
                    #    Gotta do something rational with this!
                    # CORS!  Trust our own local tomcat:
                    self.send_header('Access-Control-Allow-Origin', 'http://localhost:8087')
                    self.end_headers()

                    hdrdoc = handler.start(args)
                    if hdrdoc != None:
                        mson.write(self.wfile, hdrdoc, jfmt)

                    for r in handler.next():
                        mson.write(self.wfile, r, jfmt)
                
                    footerdoc = handler.end()
                    if footerdoc != None:
                        mson.write(self.wfile, hdrdoc, jfmt)



                    ee = datetime.datetime.now()

                    if xx.log_handler != None:
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
                              "status": respCode})


            except Exception, e:
                self.wfile.write(e)
                raise e



    #
    #  wargs:
    #  port           int      Port upon which to listen
    #  sslPEMKeyFile  string   Path to file containing PEM to activate SSL
    #                          (required for https access to this service)
    #        
    def __init__(self, wargs=None):
        self.fmap = {}
        self.wargs = wargs if wargs is not None else {}

        listen_addr = "localhost"

        listen_port = int(self.wargs['port']) if 'port' in self.wargs else 7778


        self.httpd = MultiThreadedHTTPServer((listen_addr, listen_port), WebF.HTTPHandler)

        #  To run this server as https:
        #  Make a pem with
        #  openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
        #  Pass that PEM file as value for sslPEMKeyFile
        if 'sslPEMKeyFile' in self.wargs:
           import ssl   # condition import!
           cf = self.wargs['sslPEMKeyFile']

           self.httpd.socket = ssl.wrap_socket (self.httpd.socket, certfile=cf, server_side=True)


        self.log_handler = None   # optional

        self.registerFunction("__help", self.internalHelp, {"parent":self});

        self.httpd.parent = self


    def registerFunction(self, name, handler, context):
        self.fmap[name] = (handler,context)

    def registerLogger(self, handler):
        self.log_handler = handler


    def go(self):
        self.httpd.serve_forever()

    def tickle(self, funcname, args):
        self.process(funcname, args)
