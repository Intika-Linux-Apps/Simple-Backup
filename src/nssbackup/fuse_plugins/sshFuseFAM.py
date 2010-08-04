#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Authors :
#    Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>


from gettext import gettext as _
import re


from nssbackup.fuse_plugins import pluginFAM
from nssbackup.util.exceptions import FuseFAMException, SBException
from nssbackup.util import local_file_utils
from nssbackup.util import system

try:
    import pexpect
except ImportError:
    raise FuseFAMException("Unable to import required module `pexpect`")


ssh_re = "^sftp://"
ssh_url_re = ssh_re + "([^:]+?)(:([^@]+?))?@([^/^:^@]+?)(:([0-9]+?))?/(.*)"

class sshFuseFAM (pluginFAM)  :
    """
    The fuseFAM plugin for ssh
    @requires: sshfs, python-pexpect
    @author: Oumar Aziz Ouattara
    """
    def __init__(self):
        pluginFAM.__init__(self)

    def match_scheme(self, remoteSource):
        """
        SSH schema is like : ssh://user:pass@example.com/home/user/backup/ 
        (user,pass, the first '/' ) are mandatory
        """
        _res = False
        _search_res = re.compile(ssh_re).search(remoteSource)
        if _search_res is not None:
            _res = True
        return _res

    def match_scheme_full(self, remoteSource):
        """
        SSH schema is like : ssh://user:pass@example.com/home/user/backup/ 
        (user,pass, the first '/' ) are mandatory
        """
        _res = False
        _search_res = re.compile(ssh_url_re).search(remoteSource)
        if _search_res is not None:
            _res = True
        return _res

    def mount(self, source, mountbase):
        """
        Mount the source intor the mountbase dir . This method should create a mount point to mount the source. 
        The name of the mount point should be very expressive so that we avoid collision with other mount points
        @param source: The remote path
        @param mountbase: The mount points base dir
        @return: The mount point complete path
        """
        exp = re.compile(ssh_url_re)
        match = exp.search(source)
        if not match :
            raise FuseFAMException(_("Error matching the schema 'ssh://user:pass@example.com/home/' with '%s' (The '/' after server is mandatory)") % source)
        else :
            remoteSource = "ssh://" + match.group(1)
            if match.group(3):
                remoteSource += ":" + match.group(3)
            remoteSource += "@" + match.group(4)
            if match.group(6):
                remoteSource += ":" + match.group(6)
            remoteSource += "/"

            user = match.group(1)
            mountpoint = local_file_utils.joinpath(mountbase, self._defineMountDirName(source))
            if match.group(7) :
                pathinside = match.group(7)
            else :
                pathinside = ""

        #If the path is already mounted No need to retry
        if self.checkifmounted(source, mountbase) :
            return (remoteSource, mountpoint, pathinside)

        cmd = "sshfs " + user + "@" + match.group(4) + ":/"
        cmd = cmd + " " + mountpoint

        port = match.group(6)
        if port:
            cmd += " -p " + port
        if not local_file_utils.path_exists(mountpoint) :
            local_file_utils.makedir(mountpoint)

        if system.is_superuser():
            cmd += " -o allow_root"

        self.logger.debug("Spawning: " + cmd)
        password = match.group(3)
        sshfsp = pexpect.spawn(cmd)
        i = sshfsp.expect(['(yes/no)', 'password:', 'Password:', pexpect.EOF])

        if i == 0:
            self.logger.info("Accepting to store the key.")
            sshfsp.sendline('yes')
            i = sshfsp.expect(['(yes/no)', 'password:', 'Password:', pexpect.EOF])

        if i == 1 or i == 2:
            self.logger.debug("Expecting password.")
            if not password :
                sshfsp.sendline("fake")
                local_file_utils.delete(mountpoint)
                raise SBException("sshfs is requesting a password and none has been passed.")
            sshfsp.sendline(password)
            i = sshfsp.expect(['(yes/no)', 'password:', 'Password:', pexpect.EOF])

        result = sshfsp.before # print out the result

        if sshfsp.isalive() or sshfsp.exitstatus:
            local_file_utils.delete(mountpoint)
            raise SBException (_("The sshfs command '%(command)s' didn't perform normally. Output => %(erroroutput)s ") % {"command" : cmd, "erroroutput" : result})

        return (remoteSource, mountpoint, pathinside)

    def getdoc(self):
        doc = _("SSH schema is like : ssh://user:pass@example.com:33/home/user/backup/")
        return doc

    def checkifmounted(self, source, mountbase):
        """
        @return: True if mounted, False if not
        """
        mountpoint = local_file_utils.joinpath(mountbase, self._defineMountDirName(source))
        return local_file_utils.is_mount(mountpoint)

    def _defineMountDirName(self, remote):
        """
        """
        exp = re.compile(ssh_url_re)
        match = exp.search(remote)
        if not match :
            raise FuseFAMException(_("Error matching the schema 'ssh://user:pass@example.com:21/home/' with '%s' (The '/' after server is mandatory)") % remote)
        else :
            user = match.group(1)
            dirname = "ssh_" + user + "@" + match.group(4)
            if match.group(6):
                dirname += "_" + match.group(6)
            return dirname
