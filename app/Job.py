from configparser import ConfigParser
import os
import datetime
import time
op = os.path
import logging
from xml.sax import handler, make_parser
from datetime import datetime, timedelta
import subprocess
# from . import debug
from . import XmlInfo
from .helpers import utf8lize

debug = True

class Job(object):
    """this class holds every thing to describe a job"""
    job_type = 'cfg'  # these entries will be overwriten at start-up
    job_file = 'proc_config.cfg'
    print ('in beginnng of Job')
    def __init__(self, loc, name):
        self.loc = loc      # QM_xJobs
        self.name = name    # the job directory name
        self.date = os.stat(self.myjobfile) [8]   # will be used for sorting - myjobfile stronger than url
        self.nicedate = datetime.fromtimestamp(self.date).strftime("%d %b %Y %H:%M:%S")
        self.timestarted = time.time()
        # the following will be modified by parsexml/parsecfg
        self.nb_proc = 1
        self.e_mail = "unknown"
        self.info = "unknown"
        self.script = "unknown"
        self.priority = 0
        self.size = "undefined"
        keylist = ["nb_proc", "e_mail", "info", "script", "priority", "size"]  # adapt here
        self.keylist = keylist
        if debug:
            print ('self.loc ',  self.loc)
            print ('self.name ', self.name)
            print ('self.nb_proc ', self.nb_proc)
            print ('self.e_mail ', self.e_mail)
            print ('self.info ', self.info)
            print ('self.script ', self.script)
            print ('self.priority', self.priority)
            print ('self.size', self.size)
        # and get them
        if self.job_type == "xml":
            self.parsexml()
        if self.job_type == "cfg":
            self.parsecfg()
        for intkey in ["nb_proc", "priority", "size"]:
            try:
                setattr(self, intkey, int(getattr(self,intkey)))
            except ValueError:
                setattr(self, intkey, "undefined")

    @classmethod
    def from_json(cls, job_json):
        job_json = utf8lize(job_json)
        name = job_json['name']
        loc = job_json['loc']

        return cls(loc, name)

    @property
    def url(self):
        return op.join(self.loc,self.name)
    @property
    def started(self):
        return self.nicedate
    @property
    def myjobfile(self):
        return op.join(self.loc, self.name, self.job_file)
    def parsecfg(self):
        """    load info.cfg files    """
        config = ConfigParser()
        with open(self.myjobfile) as F:
            config.read_file( F )
        for k in self.keylist:
            if config.has_option("QMOptions", k):
                val = config.get("QMOptions", k)
                setattr(self, k, val)
    def parsexml(self):
        """    load info.xml files    """
        parser = make_parser()
        handle = XmlInfo(self, self.keylist)     # inject values inside current Job
        parser.setContentHandler(handle)
        parser.parse(self.myjobfile)
    @property
    def mylog(self):
        return op.join(self.loc, self.name, "process.log")
    def avancement(self):
        """   
            analyse log file, return avancement as a string 0 ... 100   
        """
        import re
        av = 0.0
        with open(self.mylog,'r') as F:
            for l in F.readlines():
                m = re.search(r"\s+(\d+)\s*/\s*(\d+)",l)   ### Processing col 8154   5 / 32
                if m:
                    av = float(m.group(1))/float(m.group(2))
        if debug: print ("avancement", av)
        return "%.f"%(100.0*av)
    def time(self):
        """   analyse log file, return elapsed time as a string """
        import re
        tt = "- undefined -"
        with open(self.mylog, 'r') as F:
            for l in F.readlines():
                m = re.search(r"time:\s*(\d+)",l)   #
                if m:
                    tt = m.group(1)
        return tt
    def run1(self):
        "run the job - shell script way - blocking"
        Script = self.script+">> process.log 2>&1"
        try:
            self.retcode = subprocess.call(Script, shell=True)
        except OSError as e:
            logging.error("Execution failed:"+ str(e))
            self.retcode = -1
    def run2(self):
        "run the job - Popen way - blocking"
        logfile = open("process.log",'w')
        print('Job started by QM at: ',datetime.now().isoformat(timespec='seconds'), file=logfile)
        logfile.flush()
        Script = self.script.split() #"python"
        if True:
            # sub process in which we run job's scripts
            p1 = subprocess.Popen(Script, stdout=logfile, stderr=subprocess.STDOUT)
            response = p1.communicate()
            self.retcode = p1.returncode
            ok =  True
            if self.retcode != 0:
                ok = False
                print(f'Script could not be run, aborted, with retcode is {self.retcode}, message: {response}', file=logfile)
                return self.retcode
            while ok:
                self.retcode = p1.poll()
                if self.retcode is None:
                    time.sleep(1.0)
                else:
                    print ("Job finished at: %s with code %d"%(datetime.now().isoformat(timespec='seconds'), self.retcode), file=logfile)
                    break
        logfile.close()
        return self.retcode
    run = run2
    def launch(self):
        """
        Launch the job - not blocking
        use self.poll() or self.wait() to monitor the end of the process
        and self.close() to close logfile
        """
        self.logfile = open("process.log",'w')
        Script = self.script.split() #"python"
        self.process = subprocess.Popen(Script, stdout=self.logfile, stderr=subprocess.STDOUT)
    def poll(self):
        return self.process.poll()
    def wait(self):
        return self.process.wait()
    def close(self):
        return self.logfile.close()
    def __repr__(self):
        p = ["JOB  %s"%self.name]
        for k in ["nicedate", "nb_proc", "e_mail", "info", "script", "priority", "myjobfile"]:
            try:
                p.append("    %s : %s"%(k, getattr(self, k)) )
            except:
                pass
        return "\n".join(p)
    
    __str__ = __repr__