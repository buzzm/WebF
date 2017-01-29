WebF
=============

A very lightweight simple web server with pluggable function handling.

UNDER CONSTRUCTION!

Basic Use
---------

```python
$ cat mysvc1.py
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
        pass
        
    def next(self):
        for doc in [{"name":"chips", "count":6},
                      {"name":"fruit", "count":1}]:
            yield doc

    def end(self):
        pass

def main():
    websvc = WebF.WebF({})
    websvc.registerFunction("helloWorld", Func1, context)
    print "Waiting for web calls"
    websvc.go()

main()

$ python mysvc.py &
Waiting for web calls

$ curl -g 'http://localhost:7778/helloWorld?args={"startTime":"2017-01-02T19:00:06.000Z","corn":5}'
{"count":6,"name":"chips"}
{"count":1,"name":"fruit"}

$ curl -g 'http://localhost:7778/help
{"funcname":"helloWorld","args":{"args":[{"req":"Y","type":"datetime","name":"startTime","desc":"Starting time for snacking"},{"req":"N","type":"int","name":"maxCount","desc":"max number of snacks"}],"desc":"A function that returns something."}}

```

The WebF framework has these design goals:
1. Lightweight.  WebF relies only on internal python libs and one other lib (included)
2. Standardized handling of web service args.  All functions in WebF take a
single arg called "args" which is a JSON string.  This permits standardization
of representing extended types like Decimal and Dates and facilitates array and
substructure processing.
3. Ability to generate JSON, EJSON, BSON, or XML for output.  EJSON is extended
JSON which originated at MongoDB and implements a convention for identifying
types of data beyond the basic JSON types WITHOUT requiring a non-JSON compliant
parser.
4. Automatic handling of help.  Calling http://machine:port/help will return
the set of functions and descriptions and arguments to the caller.   



Overview
--------

WebF starts a web server on the host machine at the designated port.  This 
is a "service."  A service can have many functions associated with it.  
A function is named by the first path component in the URL, e.g. function foo
would be
```
      http://machine:port/foo
```
Functions are created by binding a string name to a class (*not* the instance,
the class; not the class name, the class!) plus "context" or variables to pass to the function class upon
construction:
```
websvc = WebF.WebF({})
websvc.registerFunction("helloWorld", Func1, context)
```
This approach differs slightly from Java servlets where typically the 
servlet is instantiated only once in the lifetime of the container and
shared across multiple threads.  This requires special attention to not
putting anything in class scope (without special handling) to prevent
concurrency issues.   WebF is simpler: when the function is called, a
new handler instance is created.  Shared material, if desired, can be
accessed via the context.  

The class must support these methods:
* __init__:  Is passed context as argument.
* help:  More on this later.
* start:  Called once at the start of the web service call and is passed
the args sent in the URL.
* next:  Called iteratively as necessary for the function to vend units of
content.   It is not necessary, for example, to build a giant array of 1m
items and send it out as one thing.  next() leverages python's yield 
operator.
* end:  Called after iteration to next() has concluded.

Functions can have zero more arguments.  Unlike traditional functions,
there are only arguments in the framework `args` and `fargs`.  The latter
is framework arguments which we'll cover later.  `args` is simply a JSON
string that itself carries all the "real" arguments.  This provides a 
standard, easily externalizable format to supply arguments of any type
including lists of structures, binary data, etc.  The incoming JSON
is parsed into a real python dictionary so functions never have to deal 
with JSON itsel, http decoding, etc.  In addition, EJSON is always honored
upon input to specify non-standard JSON types.  Some args examples:
```
Assume http://machine:port/ is the URL prefix; then:

Pass one arg "name" with value buzz:
    foo?args={"name":"buzz"}      

A call with several types of args, some complex:
    foo?args={"name":"buzz","fpets":["bird","dog","cat"],"idx":83}}

Pass value = 1    
    foo?args={"value":1}
    value will be class int in the args

Pass value = 1.0   
    foo?args={"value":1.0}
    value will be class float in the args

Pass value = 1L (long)
    foo?args={"value":{"$numberLong":"1"}}
    value will be class long in the args.  Note we pass 1 as a string
    to prevent any int/long trunc issues along the way

Pass value = 1D (decimal128)
    foo?args={"value":{"$numberDecimal":"1"}}
    value will be class Decimal in the args.  Note we pass 1 as a string
    to prevent any int/long trunc issues along the way

Pass value = date(2017-01-20)
    foo?args={"value":{"$date":"2017-01-28T21:47:46.333"}}
    EJSON requires dates to be passed as ISO8601 strings.
    value will be class datetime.datetime 

```
Remember it is important to encode spaces and other special characters in the
web service call, and if calling from the shell, protecting the whole thing 
with single quotes and -g if using curl to prevent globbing:
```
This will not work:
curl -g http://machine:port/foo?args={"value":"one two three"}

This will:
curl -g 'http://machine:port/foo?args={"value":"one%20two%20three"}'
```
Again, WebF will properly decode URLs and convert args to a native
python dictionary containing the proper types.


`fargs` are framework-level args and are common across ALL functions
in ANY service that is deployed.  
(This is largely unexplored space)
fmt   	 bson, json, ejson
	 Emit output in one of these formats

Help
----
A key feature of WebF is built-in help for functions.  When the service 
is called with the reserved function name `help`, the help() method of
each registered function will be called and the details of the args and
a description will be returned as structured payload in whatever format
is indicated by the `fmt` arg in `fargs` (JSON by default).  The data
in help() is also used for required argument and argument type enforcement.

The help() method has a specific structure:
```
{
  "type": "simple",
  "desc": "Tp level description of the function",
  "args": [
    {"name": "argName", "type": "argType", "req": Y|N, "desc":"description"}
    ...
   ]
}
```
`type` is currently only "simple" and indicates the structure of the help
data.  In the future, "type":"json-schema" might be used to provide very
comprehensive and detailed help on arguments.

argType is a string, one of the following:
any,string, int, long, double, datetime, binary, array, dict
Note that the simple help format cannot dive deep into array or dict types;
that is for json-schema or similar.   Also, the simple type does not have
a provision to return an error upon detection of extra / superfluous args.

When a call is made to WebF, the help is accessed and the args checked
for `req` and type.  Any errors will be collected and HTTP error 400 
returned along with the error payload:
```
A successful call:

$ curl -i -g 'http://localhost:7778/helloWorld?args={"startTime":{"$date":"2017-01-02T19:00:06.000Z"}}'
HTTP/1.0 200 OK
Content-type: text/json

{"type":6,"name":"chips"}
{"type":1,"name":"fruit"}


Missing required arg startTime:
$ curl -i -g 'http://localhost:7778/helloWorld?args={"bedTime":{"$date":"2017-01-02T19:00:06.000Z"}}'
HTTP/1.0 400 Bad Request
Content-type: text/json

{"data":"startTime","errcode":1,"msg":"req arg not found"}


Wrong arg type ($foo is not EJSON so it will remain as a dict)
$ curl -i -g 'http://localhost:7778/helloWorld?args={"startTime":{"$foo":"2017-01-02T19:00:06.000Z"}}'
HTTP/1.0 400 Bad Request
Content-type: text/json

{"msg":"arg has wrong type","data":{"expected":"datetime","found":"dict","arg":"startTime"},"errcode":2}
```

Logging
-------
If a logger is registered thusly:
```
    r.registerLogger(logF)
```
then function `logF` will be called upon completion each time the service is
hit (successful or not) with the 
following dict as an argment (here filled in with representative examples):
```
{'respCode': 200,
 'stime': datetime.datetime(2017, 1, 29, 10, 56, 13, 374307)}
 'etime': datetime.datetime(2017, 1, 29, 10, 56, 13, 374909), 
 'millis': 12,
 'params': {'args': '{"startTime":{"$date":"2017-01-02T19:00:06.000Z"}}'},
 'user': 'ANONYMOUS',
 'func': 'helloWorld',
}
```

TBD:  user/password stuff


License
-------
Copyright (C) {2017} {Buzz Moschetti}

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.


Disclaimer
----------

This software is not supported by MongoDB, Inc. under any of their commercial support subscriptions or otherwise. Any usage of Firehose is at your own risk. Bug reports, feature requests and questions can be posted in the Issues section here on github.
