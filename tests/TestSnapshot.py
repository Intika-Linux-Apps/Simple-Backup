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

from nssbackup.util import Snapshot
import os
import os.path
import unittest
import pickle
from sbackup.util.exceptions import SBException

class TestSnapshot(unittest.TestCase):
	
	abspath = os.path.abspath("./")
	snappath = abspath+"/test-datas/backupdir/2007-05-17_13.45.45.609201.wattazoum-vm.ful"
	snappath2 = abspath+"/test-datas/backupdir/2007-05-17_19.45.08.812921.wattazoum-vm.inc"
	
	def setUp(self):
 		self.snapshot = Snapshot.Snapshot(self.snappath)

	def testgetName(self) :
		" get the right name of a snapshot "
		self.assertEqual( self.snapshot.getName(), "2007-05-17_13.45.45.609201.wattazoum-vm.ful")
		
	def testgetPath(self) :
		" get the right path of a snapshot "
		self.assertEqual( self.snapshot.getPath(), self.snappath)

	def testsetPath(self) :
		" set another path/name after the snapshot creation "
		self.snapshot.setPath("/home/wattazoum/2007-05-03_21.58.59.109550.SetPath.inc")
		self.assertEqual( self.snapshot.getPath(), "/home/wattazoum/2007-05-03_21.58.59.109550.SetPath.inc")
		self.assertEqual( self.snapshot.getName(), "2007-05-03_21.58.59.109550.SetPath.inc")

	def testsetFalsePath(self):
		" an exception is raised if the path is not valid "
		self.assertRaises( SBException , self.snapshot.setPath, "/home/wattazoum/2007-05-03_21.58.59.109550.SetPath")
	
	def testgetBase1(self) :
		" base snapshot of this Inc snapshot "
		self.snapshot = Snapshot.Snapshot(self.snappath2)
		self.assertEqual(self.snapshot.getBase(),"2007-05-17_13.45.45.609201.wattazoum-vm.ful")
		
	def testgetBase2(self) :
		"Full backups got no base file"
		self.assertFalse(self.snapshot.getBase())

	def testgetFilesList(self) :
		"can compute flist and fprops "
		self.assert_(self.snapshot.getFilesList())
		
	def testgetFileProps(self) :
		" get the props of one item "
		self.assertEqual(self.snapshot.getFileProps("/home/wattazoum/Desktop/sbackup-test/d9/d12/f6.txt"),"3318810001000131179399776.0")
	
	def testgetVersion(self) :
		" Test if we get the version 1.4 "
		self.assertEqual(self.snapshot.getVersion(), "1.4")
		
	def testgetExcludes(self) :
		" get the exclude file content "
		f = open(self.snappath+"/excludes")
		toget = pickle.load(f)
		f.close()
		self.assertEqual(self.snapshot.getExcludes(), toget)		
		
	def testcommit (self) :
		"""
		Commit the snapshot infos ( write to the disk )
		"""
		
	# Setters
	
	def testsetFilesList(self) :
		" setFilesList with a dictionnary "
		test = {'item1': 'v1','item2': 'v2','item3': 'v3'}
		self.snapshot.setFilesList(test)
		self.assertEqual(self.snapshot.getFilesList(),test)
		l1 = ['item1','item2','item3']
		l2 = ['111','222','333']
		self.snapshot.setFilesList(dict(zip(l1, l2)))
		self.assertEqual(self.snapshot.getFilesList(), dict(zip(l1,l2)))
		for i in range(3) :
			self.assertTrue(self.snapshot.getFilesList()[l1[i]] == l2[i])
	
	def testsetBase(self) :
		"""
		Set the name of the base snapshot of this snapshot
		"""
			
	def testaddFile(self) :
		"""
		Add an item to be backup into the snapshot.
		 Usage :  addFile(item, props) where
		 - item is the item to be add (file, dir, or link)
		 - props is this item properties
		"""
		
	def testsetVersion(self) :
		" Set the version of the snapshot "
		self.snapshot.setVersion("1.9")
		self.assertEqual(self.snapshot.getVersion(), "1.9")
		
	def testsetExcludes(self) :
		"""
		Set the content of excludes
		"""
		
	def testsetPackages(self) :
		" set the packages list for debian based distros "
		p = os.popen("dpkg --get-selections")
		pack = p.read()
		self.snapshot.setPackages(pack)
		p.close()
		self.assertEqual(self.snapshot.getPackages(),pack)
	
	def testgetPackages(self) :
		" get the packages "
		f = open(self.snappath+"/packages")
		toget = f.read()
		f.close()
		self.assertEqual(self.snapshot.getPackages(), toget)

suite = unittest.TestLoader().loadTestsFromTestCase(TestSnapshot)
unittest.TextTestRunner(verbosity=2).run(suite)