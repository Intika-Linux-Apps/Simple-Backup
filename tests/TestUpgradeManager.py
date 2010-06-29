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

from nssbackup.managers.UpgradeManager import UpgradeManager
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.util import log
import unittest
import os

class TestUpgradeManager(unittest.TestCase) :

    def setUp(self):
        log.LogFactory.getLogger(level = 20)
        self.upgman = UpgradeManager()
        self.snpman = SnapshotManager(os.path.abspath("test-datas/backupdir"))

    def testUpgrade(self):
        """
        Upgrade a snapshot to the Upper version
        """
        path = os.path.abspath("test-datas/backupdir")
        self.upgman.upgradeAll(path)
#        snapshots = self.snpman.getSnapshots()
#        snapshots.sort(reverse=True)
#        self.upgman.upgradeSnapshot(snapshots[0])
#        self.assertEqual(snapshots[0].getVersion(),"1.5")


suite = unittest.TestLoader().loadTestsFromTestCase(TestUpgradeManager)
unittest.TextTestRunner(verbosity = 2).run(suite)
