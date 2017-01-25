WebF
=============

A very lightweight simple web server with pluggable function handling.

UNDER CONSTRUCTION!

Basic Use
---------

```
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


License
-------
Copyright (C) {2017} {Buzz Moschetti}

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.


Disclaimer
----------

This software is not supported by MongoDB, Inc. under any of their commercial support subscriptions or otherwise. Any usage of Firehose is at your own risk. Bug reports, feature requests and questions can be posted in the Issues section here on github.
