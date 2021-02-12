from xml.sax import handler, make_parser

class XmlInfo(handler.ContentHandler):
    "used to parse infos.xml files"
    def __init__(self, job, keylist):
        self.job = job
        self.keylist = keylist
    def startElement(self, name, attrs):
        if name in self.keylist:
            value = attrs.get("value")
            setattr(self.job, name, value)