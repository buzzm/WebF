import datetime

import bson
from bson.objectid import ObjectId
from bson.binary import Binary

import base64


def XprocessThing(thing):
    newval = None

    if isinstance(thing, dict):
        cks = thing.keys()

        #  Sigh.... special case for $binary...
        if len(cks) == 2:
            ck1 = cks[0]
            ck2 = cks[1]

            if ck1 == "$binary" and ck2 == "$type":
                v = thing[ck1]
                q2 = base64.b64decode(v);
                q = Binary(q2)
                newval = q    

            if ck2 == "$binary" and ck1 == "$type":
                v = thing[ck2]
                q2 = base64.b64decode(v);
                q = Binary(q2)
                newval = q    

        elif len(cks) == 1:

            ck = cks[0]
            v = thing[ck]

            if ck == "$int":
                newval = int(v)
                
            elif ck == "$date":
                #q = datetime.datetime.utcfromtimestamp(v)
                #  Huh?!?  Can't create from timestamp with
                #  standard millis since epoch?!?  Pbbbb
                q = datetime.datetime.fromtimestamp(v/1000)
                #q = datetime.datetime.fromtimestamp(v)
                newval = q

            elif ck == "$long":
                newval = long(v)
                
            elif ck == "$float":
                newval = float(v)

            elif ck == "$double":
                newval = float(v)
                
            elif ck == "$binary":
                q2 = base64.b64decode(v);
                q = Binary(q2)
                newval = q    

            elif ck == "$oid":
                q = ObjectId(v)
                newval = q    


        if newval == None:
            XprocessMap(thing)

    elif isinstance(thing, list):
        for i in range(0, len(thing)):
            v = thing[i]
            nv2 = XprocessThing(v)
            if nv2 is not None:
                thing[i] = nv2

    return newval

                
def processMap(m):
    for k in m:
        item = m[k]
        
        newval = XprocessThing(item)

        if newval is not None:
            m[k] = newval



PUREJSON=0
MONGODB=1
def emitDict(ostream, m, fmt):

    class _internal():
        def emit(self, spcs, str):
            self.ostream.write(str)

        #  A JSON String that prints like this:
        #
        #    {"server": "julia", "bob \"and\" danA"}
        #
        #  needs to look like this when captured a string
        #
        #    {\"server\": \"julia\", \"bob \\\"and\\\" danA\"}
        #
        def groomJSONStr(self, instr):
            return instr.replace('\\','\\\\').replace('"', '\\\"')

        def emitItem(self, lvl, ith, v):
            spcs = ""
            spcs2 = " " * ith

            if v == None:
                self.emit(spcs, "null")

            elif isinstance(v, Binary):
                q = base64.b64encode(v);
                self.emit(spcs,  "{\"$binary\":\"%s\", \"$type\":\"00\"}" % q )
         
            elif isinstance(v, unicode):
                q = v.encode('ascii', 'replace')
                s2 = self.groomJSONStr(q)
                self.emit(spcs, "\"%s\"" % s2)
                
            elif isinstance(v, str):
                s2 = self.groomJSONStr(v)
                self.emit(spcs, "\"%s\"" % s2)

            # Test for isinstance bool MUST precede test for int
            # because it will satisfy that condition too!
            elif isinstance(v, bool):
                # toString of bool works just fine...
                self.emit(spcs, "%s" % v)

            elif isinstance(v, int):
                if fmt == MONGODB:
                    self.emit(spcs,  "{\"$int\":%s}" % v )
                else:
                    self.emit(spcs, v)

            elif isinstance(v, float):
                if fmt == MONGODB:
                    self.emit(spcs,  "{\"$double\":%s}" % v )
                else:
                    self.emit(spcs, v)

            elif isinstance(v, long):
                if fmt == MONGODB:
                    self.emit(spcs,  "{\"$numberLong\":%s}" % v )
                else:
                    self.emit(spcs, v)

            elif isinstance(v, datetime.datetime):
                q = v.strftime('%s')
                if fmt == MONGODB:
                    self.emit(spcs,  "{\"$date\":%s}" % q )
                else:
                    self.emit(spcs, q)

            elif isinstance(v, ObjectId):
                # toString of ObjectId mercifully does the right thing....
                self.emit(spcs,  "{\"$oid\":\"%s\"}" % v )
         

            elif isinstance(v, list):
                self.emit (spcs2,  "[" )
                i = 0
                for item in v:
                    if i > 0:
                        self.emit( spcs2, "," )
               
                    self.emitItem(lvl + 1, i, item)
                    i = i + 1

                self.emit( spcs2, "]" ) 

            elif isinstance(v, dict):
                self.emitDoc(lvl + 1, v)

            else:
                #  UNKNOWN type?
                t = type(v)
                self.emit(spcs,  "\"%s::%s\"" % (t,v) )



        def emitDoc(self, lvl, m):
            i = 0

            spcs = ""

            self.emit( spcs, "{")

            for k in m:
                item = m[k]
                if i > 0:
                    self.emit(spcs,  ",\"%s\":" % (k) )
                else:
                    self.emit(spcs,  "\"%s\":" % (k) )

                self.emitItem(lvl + 1, i, item)
                i = i + 1

            self.emit(spcs,  "}")

            if lvl == 0:
                self.ostream.write("\n")

         #print ""   # force the CR

    qq = _internal()
    qq.ostream = ostream
    qq.fmt = fmt
    qq.emitDoc(0, m)

