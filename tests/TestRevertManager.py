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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>

from nssbackup.managers.RestoreManager import RestoreManager
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import getLogger
import unittest
import os

class TestRestoreManager(unittest.TestCase) :
	
	def setUp(self):
		getLogger(level=10)
 		self.rvtman = RestoreManager()
 		self.snpman = SnapshotManager(os.path.abspath("test-datas/backupdir"))
	
	def testRestore(self):
		"""
		Restore a dir into it's location
		"""
		snapshots = self.snpman.getSnapshots()
		self.rvtman.restore(snapshots[0],"/home/wattazoum/Desktop/sbackup-test/d17/")
		self.assertTrue(os.path.exists("/home/wattazoum/Desktop/sbackup-test/d17/"))
		
		
	def testRestoreAs(self):
		"""
		"""
		snapshots = self.snpman.getSnapshots()
		self.rvtman.restoreAs(snapshots[0],"/home/wattazoum/Desktop/sbackup-test/d17/", os.path.abspath('./test-datas/restoredir/') )
		self.assertTrue(os.path.exists(os.path.abspath('./test-datas/restoredir/')+"/home/wattazoum/Desktop/sbackup-test/d17/"))
		
		
	def testRevert(self):
		"""
		"""
		snapshots = self.snpman.getSnapshots()
		self.rvtman.revert(snapshots[0],"/home/wattazoum/Desktop/sbackup-test/")
		self.assertTrue(os.path.exists("/home/wattazoum/Desktop/sbackup-test/"))
	
	def testRevertAs(self):
		"""
		"""
		snapshots = self.snpman.getSnapshots()
		self.rvtman.revertAs(snapshots[0],"/home/wattazoum/Desktop/sbackup-test/",os.path.abspath('./test-datas/restoredir/'))
		self.assertTrue(os.path.exists(os.path.abspath('./test-datas/restoredir/')+"/home/wattazoum/Desktop/sbackup-test/"))


suite = unittest.TestLoader().loadTestsFromTestCase(TestRestoreManager)
unittest.TextTestRunner(verbosity=2).run(suite)
