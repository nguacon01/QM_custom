from configparser import ConfigParser
from . import logging
from datetime import datetime
import sys
from .Jobs import DONE_JOBS, Jobs, QUEUE_JOBS, RUNNING_JOBS, ERROR_JOBS
from .Mail import Email
import os
import time
op = os.path
from pathlib import Path
import shutil
import glob

class QueueManager(object):
    """
    class that deals with all incoming jobs
    It calls sequentially scout that waits for new jobs in the queue
    Then it verifies that no other NPK Job is running
    and it launches the new job
    
    everything is maintained in a self.joblist lists - top job is the first to be run
    """
    def __init__(self, config):
        self.config = config
        self.qm_folder = self.config.get("QMServer", "QM_FOLDER")
        self.MaxNbProcessors = int(self.config.get("QMServer", "MaxNbProcessors"))
        self.launch_type = self.config.get("QMServer", "launch_type")
        self.job_file = self.config.get("QMServer", "job_file")
        if self.job_file.endswith('.xml'):
            self.job_type = 'xml'
        elif self.job_file.endswith('.cfg'):
            self.job_type = 'cfg'
        else:
            raise Exception("job_file should be either .xml or .cfg")
        self.mailactive = config.getboolean("QMServer", "MailActive")

        # dmd
        self.jobs = Jobs(self)
        # dmd
        self.nap_time = 3.0       # in second
    
    def __str__(self):
        return f"Queue with {self.MaxNbProcessors} processor, job type is {self.job_type}, with {len(self.jobs.get_jobs(type=QUEUE_JOBS))} jobs are in queue"
    __repr__ = __str__


    def run(self):
        "the way to start to QM endless loop"
        if self.launch_type == "blocking":
            while True :
                next_one = self.wait_for_job()
                self.run_job(next_one)
        elif self.launch_type == "non-blocking":
            print ('self.launch_type == "non-blocking"')
            while True :
                N = self.clean_running_n_count()
                # self.queue_jobs = job_list(self.qJobs, self.dJobs)
                self.queue_jobs = self.jobs.get_jobs(type=QUEUE_JOBS)
                if self.queue_jobs:
                    next_one = self.queue_jobs.pop()
                    if N + min(next_one.nb_proc, self.MaxNbProcessors) <= self.MaxNbProcessors:  # if there is room
                        self.run_job(next_one)
                self.nap()
        else:
            raise Exception("error in configuration for launch_type")

    def nap(self):
        "waiting method for spooling"
        time.sleep(self.nap_time)
    def wait_for_job(self):
        """
        method that waits for something to show up in QM_qJobs folder
        and returns an ordered list of present jobs.
        oldest (most prio) first
        """
        self.queue_jobs = []
        while len(self.jobs.get_jobs(type=QUEUE_JOBS)) == 0:
            self.nap()
        next_job = self.jobs.get_jobs(type=QUEUE_JOBS).pop()
        return next_job
    def clean_running_n_count(self):
        """
        go through running job list, close finished ones, and count total CPU burden
        """
        N = 0
        job_list = self.running_jobs
        for j in job_list:
            if j.poll() is not None:  # means it's finished
                j.close()
                self.job_clean(j)
            else:
                N +=  min(self.MaxNbProcessors, j.nb_proc)  # cannot be larger than self.MaxNbProcessors
        if self.debug and N>0:
            counttag = "%s clean_running_n_count() found %d"%(datetime.now().strftime("%d %b %Y %H:%M:%S"),N)
            logging.debug(counttag)
            print (counttag)
        return N
            
    def run_job(self, job):
        """
        method that deals with moving job to do around and running  job.script 
        loanch in blocking or non-blocking mode depending on global flag
        """
        if self.config.get('QMServer', 'Debug'):
            print ('QM [%s] Starting job "%s" by %s'%(datetime.now().isoformat(timespec='seconds'), job.name, job.e_mail))
            print ('job.nb_proc ', job.nb_proc)
            print ('job.info ', job.info)
            print ('job.script ', job.script)
            print ('job.priority', job.priority)
            print ('job.size', job.size)
        # self.running_jobs.append(job)
        logging.info('Starting job "%s" by %s'%(job.name,job.e_mail) )
        logging.debug(repr(job))
        source_qJobs = op.join(self.qm_folder, QUEUE_JOBS, job.name)
        to_Jobs = op.join(self.qm_folder, RUNNING_JOBS, job.name)
        # to_dJobs = op.join(self.QM_FOLDER, DONE_JOBS, job.name)
        
        # move job from queue folder to running folder
        shutil.move(src=source_qJobs, dst=to_Jobs, copy_function=shutil.copytree)
        # os.rename(to_qJobs, to_Jobs)    # First move job to work dir
        job.loc = to_Jobs
        os.chdir(to_Jobs)           # and cd there
        if job.script == "unknown":
            job.script = 'echo no-script; pwd; sleep 10; ls -l'
            logging.warning("undefined script in info file")
        if job.nb_proc > self.MaxNbProcessors:    
            msg = "Nb of processors limited to %d"%self.MaxNbProcessors
            logging.warning( msg )
            with open("process.log","w") as F:
                F.write(msg)
            job.nb_proc = self.MaxNbProcessors
        os.putenv("NB_PROC", str(job.nb_proc))  # very primitive way of limiting proc number !
        if self.launch_type == "blocking":
            retcode = job.run()
            self.job_clean(job)
        if self.launch_type == "non-blocking":
            job.launch()
            # clean will be done later, by clean_running_n_count

    def job_clean(self, job):
        """
        closes and move the job folder to done_Jobs
        maybe also send e-mail once the job is done ... 
        """
        source_Jobs = op.join(self.qm_folder, RUNNING_JOBS, job.name)
        now = datetime.now().isoformat(timespec='seconds')
        to_dJobs = op.join(self.qm_folder, DONE_JOBS, now+'-'+job.name)
        to_errorJobs = op.join(self.qm_folder, ERROR_JOBS, now+'-'+job.name)
        # os.chdir(self.qJobs)         # we might be in to_Jobs, so we cd away.
        # os.chdir(to_Jobs)
        if job.retcode != 0:
            # move job from running folder to error folder in case it has any error
            shutil.move(src=source_Jobs, dst=to_errorJobs, copy_function=shutil.copytree)
            # os.rename(to_Jobs, to_errorJobs)
            subject = f"Your job {job.name} is not completed"
            body = f"""The job named - {job.name} - started on QueueManager is not finished
                        Please check your elements"""
        else:
            # move job from running folder to done folder
            shutil.move(src=source_Jobs, dst=to_dJobs, copy_function=shutil.copytree)
            # os.rename(to_Jobs, to_dJobs)
            subject = f"Your job {job.name} is completed"
            body = f"""The job named - {job.name} - started on QueueManager is finished 
                    Info : {job.info}
                    Result can be found here : {to_dJobs}
                    Virtually yours,
                    The QueueManager"""
        
        if self.mailactive:
            receiver = job.e_mail
            try:
                info_mail = Email(config = self.config, receiver=receiver, body=body, subject=subject)
                mes = info_mail.sendMail()
                logging.error("Sent mail to %s"%receiver)
            except:
                logging.error("Mail to %s could not be sent"%receiver)
        logging.info('Finished job "%s" with code %d'%(job.name, job.retcode))