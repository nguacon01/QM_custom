# QueueManager #

# Presentation
The QM (QueueManager) program implements a simplistic Queue Manager, i.e. it allows to run programs in batch, with a queueing system.
It is pure python and has no external dependency but bottle which is included in this repository.

The program QM runs in background, with a very small CPU overhead, it waits for jobs to appear in the query folder, verify it, and launch it.
Once the job is finished, the results are moved to a folder were all done jobs are waiting for you for inspection.

To performed this task, jobs have to be packaged to run in a stand alone manner, independently of the location from where they are started.
A small file giving some information describing the job has to be written.

QM has been tested and used on Linux, MacOsX, and Windows. It is written in python, but can launch codes written in any langages

QM comes with two independent programs :

 * **QueueManager.py** is the QM program itself
 * **WEB_QMserver.py** is a utility allowing to monitor QM through a web page - not fully debuged yet !



### Version
`__version__ = 0.4`

The current version is working, but still preliminary. Some features are still missing (see below).
Version 0.3 introduces a non-blocking mode, which enables several jobs to run in parallel in order to use all the available processors.
Version 0.4 is a port to python 3, and brings some more tuning

This code is Licenced under the [Cecill 2.1](http://www.cecill.info/licences/Licence_CeCILL_V2.1-en.html) licence code

---

# Set-up

### dependences
* The QM program and the Web monitor rely only on standard libraries. They run on python 2.7 (not tested anymore) and python 3.x
* The Web monitor program requires the additional [bottle](http://bottlepy.org/)  program, which is packaged as a single file into this repository.

### program installation
simply download the repository anywhere on your disk

`git clone https://github.com/delsuc/QM.git`

should do it


### program setup
QM operations are organized around 4 folders, which should be created anywhere on your disk.

     `QM_qJobs`       queuing jobs
     `QM_Jobs`        running jobs
     `QM_dJobs`       done jobs
     `QM_lost+found`  when something goes wrong, jobs are moved here

Then QM and the monitor are parametrized in a configuration file called `QMserv.cfg`

### configuration
The configuration is done in the file `QMserv.cfg`.
This is a text configuration file, read by the `ConfigParser` python module
There are two sections `[QMServer]` and `[WEB_QMserver]`

#### QMServer
contains the parameters for the QueueManager program

- `QM_FOLDER` :  the path where you have placed QM_* folders
- `MaxNbProcessors` : the maximum number of processors allowed for one job
- `job_file` : name of the job description file, file can be xml or cfg file types (see below)
- `MailActive` : If MailActive is TRUE, a mail is sent when a job is finished
- `launch_type` : The way jobs are launched - either blocking (one at a time) or non-blocking (as many jobs in parallele as MaxNbProcessors allows)
- `Debug` : debug mode, should not be active in production mode

#### WEB_QMserver
contains the parameters for the WEB_QMserver monitoring program

- `Host` : the hostname uder which the web page is served, if you choose `localhost` the page will available only on your local machine; if you put the complete name of your computer, the page will be seen on your local network
- `The_Port` : the port on which the server is serving, default is 8000
- `Refresh_Rate` : the main page is self refreshing, this is the delay in second between refreshes
- `Display_details` : Display or not Jobs details in the list
- `Delete_Jobs` : Deletation of Jobs (waiting and done) can be allowed
- `Licence_to_kill` : if True, the kill button will be present (to kill the running job) - use at your own risks
- `Debug` : debug mode, should not be active in production mode

---

# Creating and launching jobs
## basic jobs

jobs are folders, they contain all the need information to run code.
Minimum job is

  - a info file, either in xml or cfg format (defined in QMserv.cfg)
  - a script to launch

but you can put in there everything you need (data, code, etc...)

The info file should contain :

typical xml is:
```
<PARAMETER>
    <nb_proc value="12"/>
    <e-mail value="me@gmail.com"/>
    <script value="python process.py param1 param2"/>
    <info value="some description of the job"/>
</PARAMETER>
```

typical cfg is:
```
[QMOptions]
nb_proc : 12
e_mail : me@gmail.com
info : some description of the job
script : python process.py param1 param2
```

The only required entry is script
You can use this file for your own entries


- `script` : **required** the command to execute
- `e_mail` : if this is configured, a mail is sent to this adress at the end of the run
- `info` : used to describde the job in the WEB job list
- `nb_proc` : is used to limit the number of processors.

`nb_proc` mechanism is still preliminary. 
What is done for the moment is to set an environment variable `NB_PROC` which is not enforced, but should be checked by the script itself.

The job program is then runs inside the job folder, which may contain any associated files.
If you use `python` One nice trick you may use is to put there your python module as a zip file (remove all `*.pyc  *.pyo`  and `__pychache__` files).
Then write a little starter program, with the following line :
```
import sys
sys.path.insert(0,'mymodule.zip')
import mymodule
```
The python import will then be able to import your code directly from the zip file.


## one example
Here is an example job (we assume `QueueManager.py` is configured and running)

- the job is called `test_QM` ; a folder, with this name contains the following files

```
>ls -l test_QM
-rw-r--r--@ 1 mad  admin     141 May 20 18:28 proc_config.cfg
-rw-r--r--@ 1 mad  admin  817708 Apr 30 16:02 spike.zip
-rw-r--r--@ 1 mad  admin     853 May 22 15:09 test.py

```

- `proc_config.cfg` is as follows :

```
[Proc]
Size : 50

[QMOptions]
nb_proc : 4
e_mail : madelsuc@unistra.fr
info : Test of the QM manager
script : python test.py proc_config.cfg
```

- The test.py program is as follows :

```
import sys
import time
sys.path.insert(0,'spike.zip')    # to show how a big project can be included
from spike.NPKConfigParser import NPKConfigParser

'''
Dummy processing,  as a test for QM
'''
def PROC(config):
    size = config.getint("Proc","Size")
    total = 0
    for i in range(size):
        print ("processing %d / %d"%(i+1,size) )  # produces : processing i / size   
        sys.stdout.flush()                        # this updates the log file, and allows to monitor how far we are so far
        total = total  + i*(total+i)
        time.sleep(30./size)                # this is just to slow the program down - for demo
    with open('results.txt','w') as F:
        F.write("Final result is :\n%d"%total)
    print ("Done")
if __name__=='__main__':
    configfile = sys.argv[1]
    config = NPKConfigParser()
    config.read(configfile)
    processing = PROC(config)
```

Note :

 - how the program get the Size parameter from the proc_config.cfg, which has here a double use.
 - how the [QMOptions] section contains the info for QM, but the [Proc] section, ignored by QM, is used by the script for getting its parameters.
 - writing something like   `xxxx   i / n`  on the standard output helps the WEB monitor to follow the processing ( use `sys.stdout.flush()` to force flushing the output, so that QM may monitor it)
 - a file is created ( `results.txt` ) This file is created locally inside the job folder.
  
When the `test_QM` folder is copied into QM_qJobs, it should disappear after a few seconds, and move to QM_Jobs.
The script is executed, and `test.py` launched with the parameters.

After a few minutes, the program finishes, and `test_QM` is moved to the QM_dJobs folder.
You should find now this :

```
>ls -l QM_dJobs/test_QM
-rw-r--r--@ 1 mad  admin     141 May 20 18:28 proc_config.cfg
-rw-r--r--  1 mad  admin     898 May 22 15:10 process.log
-rw-r--r--  1 mad  admin      25 May 22 15:10 results.txt
-rw-r--r--@ 1 mad  admin  817708 Apr 30 16:02 spike.zip
-rw-r--r--@ 1 mad  admin     853 May 22 15:09 test.py
```
where

- `process.log` contains the output of the program
- `results.txt` has been created by running the program


---

# contact

This code has been written by Marc-André Delsuc (madelsuc@unistra.fr).

# Remarks
This is a preliminary version. There are still bugs and missing features

### Bugs
- the mail feature is probably broken
- no other known bug at this stage - except an ugly html output

 
### missing features - *planned* -
- a better way of limiting the number of processor should be installed - *an idea anybody* ?
- a third configuration mode based on a single shell script ( *à la slurm* )
