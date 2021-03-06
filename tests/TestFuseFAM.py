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


import unittest

from sbackup.plugins.sshFuseFAM import sshFuseFAM
from sbackup.util.exceptions import SBException
from sbackup.plugins.ftpFuseFAM import ftpFuseFAM

class TestFuseFAM(unittest.TestCase):
    """
    """
    def testsshPluginMatchScheme(self):
        "Test sshPlugin Matching URL"
        sshPlugin = sshFuseFAM()
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user:pass@server/"));
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user:pass@server:21/my/dir"));
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user@server:21/my/dir"));
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user@server/my/dir"));
        self.assertFalse(sshPlugin.match_scheme_full("ssh://userserver/my/dir"));
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user@mail.com@192.168.0.4:11/"))
        self.assertTrue(sshPlugin.match_scheme_full("ssh://user@mail.com:password@192.168.0.4:11/test"))

    def testftpPluginMatchScheme(self):
        "Test ftpPlugin Matching URL"
        ftpPlugin = ftpFuseFAM()
        self.assertTrue(ftpPlugin.match_scheme_full("ftp://user:pass@server/"));
        self.assertTrue(ftpPlugin.match_scheme_full("ftp://user:pass@server:21/my/dir"));
        self.assertFalse(ftpPlugin.match_scheme_full("ftp://user@server:21/my/dir"));
        self.assertFalse(ftpPlugin.match_scheme_full("ftp://user@server/my/dir"));
        self.assertTrue(ftpPlugin.match_scheme_full("ftp://userserver/my/dir"));
        self.assertFalse(ftpPlugin.match_scheme_full("ftp://user@mail.com@192.168.0.4:11/"))
        self.assertTrue(ftpPlugin.match_scheme_full("ftp://user@mail.com:password@192.168.0.4:11/test"))


    def testsshPlugindefineMount(self):
        "Test sshPlugin define mount point"
        sshPlugin = sshFuseFAM()
        self.assertEqual("ssh_user@server", sshPlugin._defineMountDirName("ssh://user:pass@server/"));
        self.assertEqual("ssh_user@server_21", sshPlugin._defineMountDirName("ssh://user:pass@server:21/my/dir"));
        self.assertEqual("ssh_user@server_21", sshPlugin._defineMountDirName("ssh://user@server:21/my/dir"));
        self.assertEqual("ssh_user@server", sshPlugin._defineMountDirName("ssh://user@server/my/dir"));

    def testsshPluginMount(self):
        "Test mounting "
        sshPlugin = sshFuseFAM()
        rep = sshPlugin.mount("ssh://wattazoum:mpsilife@192.168.0.1/etc/", "test-tmp")
        sshPlugin.umount(rep[1])
        try:
            sshPlugin.mount("ssh://wattazoum@192.168.0.1:22/etc/", "test-tmp")
            self.fail("should fail")
        except SBException, e:
            self.assertEqual("sshfs is requesting a password and none has been passed.", str(e))

        #sshPlugin.mount("ssh://wattazoum@192.168.0.1:21/etc/", "test-tmp")

suite = unittest.TestLoader().loadTestsFromTestCase(TestFuseFAM)
unittest.TextTestRunner(verbosity = 2).run(suite)
