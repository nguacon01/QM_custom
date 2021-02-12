__version__ = 0.4
import sys
import logging
from configparser import ConfigParser
from .QueueManager import QueueManager as QM

def config(*args, **kwarg):
    config = ConfigParser()
    config.read('QMserv.cfg')
    for key, val in kwarg:
        config.set('QMServer', key, val)
    return config

def start_logger():
    "configurate and start logger"
    # create logger
    logging.basicConfig(level=logging.INFO, \
        format="%(asctime)s %(levelname)s %(message)s", filename="QueueManager.log")
        
logging = start_logger()

def get_QM():
    """
        Get queue of jobs
    """
    config_queue = config()
    queue = QM(config_queue)
    queue.run()