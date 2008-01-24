import os
import socket
from gettext import gettext as _

class Infos :
    """
    """
    
    NAME = "Not So Simple Backup Suite"
    VERSION = "0.1-5"
    DESCRIPTION = _("This is a user friendly backup solution for common desktop needs.")
    WEBSITE = "https://launchpad.net/nssbackup/"
    
    hostname = socket.gethostname()
    if "." in hostname :
        mailsuffix = hostname
    else :
        mailsuffix = hostname + ".ext"
    SMTPFROM = _("NSsbackup Daemon <%(login)s@%(hostname)s>") % {'login' : os.getenv("USERNAME"), 'hostname': mailsuffix}