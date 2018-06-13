import BaseHTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from SocketServer import ThreadingMixIn

import urllib
import datetime
from mson import mson
import bson

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
           return (200, None)

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
        def __init__(self, respcode, errs):
            self.respcode = respcode
            self.errs = errs

        def start(self, cmd, hdrs, args, rfile):
           return (self.respcode, None)
        
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

        def do_PUT(self):
            (func,params) = self.parse(self.path)
            self.call(func, params)

        def do_PATCH(self):
            (func,params) = self.parse(self.path)
            self.call(func, params)

        def do_DELETE(self):
            (func,params) = self.parse(self.path)
            self.call(func, params)

        def log_message(self, format, *args):
           xx = self.server.parent
           if xx.log_handler == None:
              print "%s - - [%s] %s" % (self.address_string(),self.log_date_time_string(),format%args)




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

            #func = func.strip('/')

            qq = func.split('/')
            qq.pop(0)  # URL always has leading / so toss it...

            func = qq.pop(0)

            if len(qq) > 0:  
                # is function/RESTarg
                params['_'] = qq

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
            allowUnknownArgs = False

            if 'allowUnknownArgs' in funcHelp:
               allowUnknownArgs = funcHelp['allowUnknownArgs']

            declaredArgs = {}

            if 'args' in funcHelp:
                for hargs in funcHelp['args']:

                    declaredArgs[hargs['name']] = 1

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
                             
                # Now go the other way:  Check webargs:
                if allowUnknownArgs == False:
                   for warg in webArgs:
                      if warg != '_' and warg not in declaredArgs:
                         argerrs.append({
                             "errcode":2,
                             "msg":"unknown arg",
                             "data": {
                                "arg": warg
                                }})
                       
            return argerrs
                            
            

        @staticmethod
        def bsonWriter(ostream, doc, fmt):
           # fmt is unused
           ostream.write( bson.BSON.encode(doc) )




        def respond(self, args, handler):

           hdrdoc = None

           # Give start() a chance to do something; it is required mostly
           # because it must provide a response code.
           (respCode, hdrdoc) = handler.start(self.command, self.headers, args, self.rfile)

           self.send_response(respCode)

           # Regular ol' json is the default:
           contentType = 'application/json'
           jfmt = mson.PURE
           theWriter = mson.write

           if "Accept" in self.headers:
              fmt = self.headers['Accept']

              if fmt == "application/bson":
                 contentType = 'application/bson'
                 theWriter = self.bsonWriter

              else:
                 if fmt == "application/ejson":
                    jfmt = mson.MONGO

           # else regular ol' json


           self.send_header('Content-type', contentType)

           if self.server.parent.cors is not None:
              self.send_header('Access-Control-Allow-Origin', self.server.parent.cors)
           self.end_headers()

           if hdrdoc != None:
#                 mson.write(self.wfile, hdrdoc, jfmt)
              theWriter(self.wfile, hdrdoc, jfmt)

           mmm = getattr(handler, "next", None)
           if callable(mmm):              
              for r in handler.next():
#                 mson.write(self.wfile, r, jfmt)
                 theWriter(self.wfile, r, jfmt)

           mmm = getattr(handler, "end", None)
           if callable(mmm):              
              footerdoc = handler.end()
              if footerdoc != None:
#                 mson.write(self.wfile, footerdoc, jfmt)
                 theWriter(self.wfile, footerdoc, jfmt)

                    


        def call(self, func, params):
            xx = self.server.parent

            respCode    = 200
            args        = None
            fargs       = None
            fmt         = None; 

            try:
                user = None

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
                      'errcode': 5,  # TBD
                      'msg': "no such function",
                      "data": func
                      }
                   respCode = 404 
                   handler = xx.internalErr(respCode, [err])

                else:
                    (hname,context) = xx.fmap[func]

                    # Construct a NEW handler instance!
                    handler = hname(context)

                    try:
                       args = mson.parse(params['args'], mson.MONGO) if 'args' in params else {}
                       if '_' in params:
                           args['_'] = params['_'] 

                    except:
                       err = {
                          'errcode': 4,
                          'msg': "malformed JSON for args"
                          }
                       respCode = 400
                       handler = xx.internalErr(respCode, [err])


                    try:
                       fargs = mson.parse(params['fargs'], mson.MONGO) if 'fargs' in params else {}
                    except:
                       err = {
                          'errcode': 5,
                          'msg': "malformed JSON for fargs"
                          }
                       respCode = 400
                       handler = xx.internalErr(respCode, [err])



                # END PRELIM
                if respCode != 200:
                   self.respond(args, handler)

                else:
                    #  Basic stuff is OK and handler is set.  Move on.
                    #  Check args and authentication.  If either is bad, then
                    #  SWITCH the handler to the error handler and set an
                    #  appropriate HTTP return code.
                    zz = handler.help()
                    argerrs = self.chkArgs(zz, args)
                    if len(argerrs) > 0:
                       respCode = 400
                       handler = xx.internalErr(respCode, argerrs)

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

                             handler = xx.internalErr(401, [err])

                    self.respond(args, handler)


                ee = datetime.datetime.now()

                if xx.log_handler != None:
                   if user == None:
                      user = "ANONYMOUS"

                   #diffms = int((ee - ss)/1000)
                   tdelta = ee - ss
                   diffms = int(tdelta.microseconds/1000)

                   xx.log_handler({
                         "addr": self.address_string(),
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
               handler = xx.internalErr(500, [err])
               self.respond(args, handler)

               import traceback
               traceback.print_exc()

               raise e


    #
    #  wargs:
    #  port           int      listen port (default: 7778)
    #  addr           string   listen addr (default: localhost BUT if you want
    #                          other machines to connect, specify "0.0.0.0"
    #  sslPEMKeyFile  string   Path to file in PEM format containing concatenation of
    #                          private key plus ALL certs (the full cert chain)
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
        #  Make a key and cert files:
        #    openssl req -x509 -nodes -newkey rsa:2048 -subj "/CN=localhost" -keyout key.pem -out cert.pem -days 3650
        #    cat key.pem cert.pem > mycert.pem
        #  Pass the mycert.pem file as value for sslPEMKeyFile
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

