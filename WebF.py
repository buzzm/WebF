import BaseHTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from SocketServer import ThreadingMixIn

import urllib
import datetime
from mson import mson

import traceback
import sys

#  See stackoverflow.com for this.  Excellent.
class MultiThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
   pass


class WebF:
    class internalHelp:
        def __init__(self, context):
            self.parent = context['parent']

        def help(self):
            return {}

        def start(self, cmd, hdrs, args, rfile):
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

        def start(self, cmd, hdrs, args, rfile):
           pass
        
        def next(self):
            for err in self.errs:
               yield err

        def end(self):
            pass



    class HTTPHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            (func,params) = self.parse(self.path)
            self.call(func, params)

        def do_POST(self):
            (func,params) = self.parse(self.path)
            self.call(func, params)


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
              ss = "string"
           elif ss == 'str':           
              ss = "string"
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
                            
            

        def respond(self, respCode, args, fmt, handler):
           self.send_response(respCode)

           contentType = 'text/json'

           jfmt = None
           if fmt == "bson":
              contentType = 'text/bson'
           else:
              jfmt = mson.PURE
              if fmt == "ejson":
                 jfmt = mson.MONGO

           self.send_header('Content-type', contentType)

           if self.server.parent.cors is not None:
              self.send_header('Access-Control-Allow-Origin', self.server.parent.cors)

           self.end_headers()

           mmm = getattr(handler, "start", None)
           if callable(mmm):
              hdrdoc = handler.start(self.command, self.headers, args, self.rfile)
              if hdrdoc != None:
                 mson.write(self.wfile, hdrdoc, jfmt)

           mmm = getattr(handler, "next", None)
           if callable(mmm):              
              for r in handler.next():
                 mson.write(self.wfile, r, jfmt)

           mmm = getattr(handler, "end", None)
           if callable(mmm):              
              footerdoc = handler.end()
              if footerdoc != None:
                 mson.write(self.wfile, footerdoc, jfmt)

                    


        def call(self, func, params):
            xx = self.server.parent

            respCode    = 200
            args        = None
            fargs       = None
            fmt         = None; 

            try:
                ss = datetime.datetime.now()

                # The Exception:
                # If func = "help" then it's "__help"  It is The One 
                # function that bridges internal and external handling.
                if func == "help":
                    func = "__help"
                
                #
                # START PRELIM
                # Get the function, parse the args
                #
                if func not in xx.fmap:
                   err = {
                      'errcode': 5,
                      'msg': "no such function",
                      "data": func
                      }
                   handler = xx.internalErr([err])
                   respCode = 404 

                else:
                    user = None

                    (hname,context) = xx.fmap[func]

                    # Construct a NEW handler instance!
                    handler = hname(context)

                    try:
                       args = mson.parse(params['args'], mson.MONGO) if 'args' in params else {}
                    except:
                       err = {
                          'errcode': 4,
                          'msg': "malformed JSON for args"
                          }
                       handler = xx.internalErr([err])
                       respCode = 400

                    try:
                       fargs = mson.parse(params['fargs'], mson.MONGO) if 'fargs' in params else {}
                    except:
                       err = {
                          'errcode': 5,
                          'msg': "malformed JSON for fargs"
                          }
                       handler = xx.internalErr([err])
                       respCode = 400


                # END PRELIM
                if respCode != 200:
                   self.respond(respCode, args, "json", handler)

                else:
                    #  Basic stuff is OK.  Move on.

                    if fargs is not None:
                        if "fmt" in fargs:
                            fmt = fargs["fmt"].lower()


                    zz = handler.help()
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

                    self.respond(respCode, args, fmt, handler)


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
               err = {
                  'errcode': 6,
                  'msg': "internal error",
                  "data": func
                  }
               handler = xx.internalErr([err])
               self.respond(500, args, fmt, handler)

               raise e


    #
    #  wargs:
    #  port           int      listen port (default: 7778)
    #  addr           string   listen addr (default: localhost BUT if you want
    #                          other machines to connect, specify "0.0.0.0"
    #  sslPEMKeyFile  string   Path to file containing PEM to activate SSL
    #                          (required for https access to this service)
    #  cors           URI | *  Set Access-Control-Allow-Origin to this
    #                          value.  See http CORS docs for details.
    #
    def __init__(self, wargs=None):
        self.fmap = {}
        self.wargs = wargs if wargs is not None else {}

        listen_addr = self.wargs['addr'] if 'addr' in self.wargs else "localhost"
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


        self.cors = self.wargs['cors'] if 'cors' in self.wargs else None

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
