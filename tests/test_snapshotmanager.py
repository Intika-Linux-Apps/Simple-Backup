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
#   Jean-Peer Lorenz <peer.loz@gmx.net>

"""Module privides unittest for testing of classes/methods related to
snapshot managing.
"""

import os
import subprocess
import unittest

from nssbackup.managers.SnapshotManager import SnapshotManager 
from nssbackup.managers.SnapshotManager import debug_print_snarfile
from nssbackup.managers.SnapshotManager import debug_snarfile_to_list

from nssbackup.util.log import LogFactory
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import RebaseFullSnpForbidden
from nssbackup.util.exceptions import RebaseSnpException
from nssbackup.util.tar import SnapshotFile


class _TestSnapshotManagerPaths(object):
	"""This class only purpose is to provide pathnames to input/output test
	data from a single place to avoid multiple definitions of them.
	"""
	# definition of paths for testing the class 'SnapshotManager'
	__abspath_testdir = os.path.abspath("./")
	__snp_path_rel = "test-datas/test-snapshotmanager/out"
	__tar_rel = "test-datas/test-snapshotmanager/test-snpmanager.tar.bz2"

	@classmethod
	def get_snp_path(cls):
		"""Returns the absolute path to the existing snapshots to be tested.
		"""
		_path = os.path.join(cls.__abspath_testdir,
							 cls.__snp_path_rel)
		return _path

	@classmethod
	def get_tar_path(cls):
		"""Returns the absolute path to the tar-archive containing the
		snapshots to be tested.
		"""
		_path = os.path.join(cls.__abspath_testdir,
							 cls.__tar_rel)
		return _path
	
	
class _TestSnapshotMergePaths(object):
	"""This class only purpose is to provide pathnames to input/output test
	data from a single place to avoid multiple definitions of them.
	"""
	# definition of paths for testing the class 'SnapshotManager'
	__abspath_testdir	= os.path.abspath("./")
	__snp_path_rel		= "test-datas/test-snapshotmanager/test-merge/onestep"
	__tar_rel = "test-datas/test-snapshotmanager/test-merge/bak-state1-3inc.ver2.tar.bz2"
	__result_snar = "test-datas/test-snapshotmanager/test-merge/target-results-onestep/files-onestep-res.snar"
	
	@classmethod
	def get_snp_path(cls):
		"""Returns the absolute path to the existing snapshots to be tested.
		"""
		_path = os.path.join(cls.__abspath_testdir,
							 cls.__snp_path_rel)
		return _path

	@classmethod	
	def get_tar_path(cls):
		"""Returns the absolute path to the tar-archive containing the
		snapshots to be tested.
		"""
		_path = os.path.join(cls.__abspath_testdir,
							 cls.__tar_rel)
		return _path

	@classmethod	
	def get_res_snar(cls):
		"""
		"""
		_path = os.path.join(cls.__abspath_testdir,
							 cls.__result_snar)
		return _path


class TestSnapshotManager(unittest.TestCase):
	"""Test case for testing basic functionality of the
	class 'SnapshotManager'. This test case covers tests that
	neither read from disk nor write to it. 
	"""
	
	def setUp(self):
		"""Set-up the test to be run.
		"""
		LogFactory.getLogger( level=10 )

	def test_instantiation_fails(self):
		"""Test instantiation of SnapshotManager with invalid parameter
		"""
		tdir = None
		self.assertRaises(SBException, SnapshotManager, tdir)

		tdir = "/hopefully/thispath/doesnot/exist"
		self.assertRaises(SBException, SnapshotManager, tdir)

	def test_instantiation(self):
		"""Test creation of SnapshotManager with valid parameter
		"""
		tdir = _TestSnapshotManagerPaths.get_snp_path()
		SnapshotManager(tdir)


class TestSnapshotManagerFromDisk(unittest.TestCase):
	"""Test case for testing 'read-only' functionality of the
	class 'SnapshotManager'. This test case covers tests that
	read from disk but do not write to the disk. 
	"""

	# Setting of path names
	snpname = [	"2009-01-20_10.17.15.090738.hostname.inc",
				"2009-01-19_18.52.23.861532.hostname.inc",
				"2009-01-19_18.49.12.837677.hostname.inc",
				"2009-01-19_18.47.28.188518.hostname.ful"				
			  ]
	
	def setUp(self):
		LogFactory.getLogger( level=10 )
	
		self.snppath = []
		for name in self.snpname:
			self.snppath.append(os.path.join(\
								_TestSnapshotManagerPaths.get_snp_path(), name))

	
		self.__clean_dir()
		self.__untar_snapshots()

		# create SnapshotManager
		self.snpman = SnapshotManager(_TestSnapshotManagerPaths.get_snp_path())
		
#	def tearDown(self):
#		self.__clean_dir()

	def __clean_dir(self):
		for _path in self.snppath:
			rmcmd = ["rm", "-rf", _path]
			subprocess.call(rmcmd)

	def __untar_snapshots(self):
		tarcmd = ["tar", "-xj",
				  "--directory=%s" % _TestSnapshotManagerPaths.get_snp_path(),
				  "-f", "%s" % _TestSnapshotManagerPaths.get_tar_path()]
		subprocess.call(tarcmd)
	
	def test_get_snapshots_all(self):
		"""Getting list of snapshots from target directory. Force reload of the
		list. It is checked against number of returned values and the names
		of the snapshots. Additional for full snapshots it is checked whether
		the stored base is correct.
		"""
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		self.assertEqual(len(snp_list), len(self.snpname))
		for _idx in range(0, len(snp_list)):
			_snp = snp_list[_idx]
			self.assertEqual(_snp.getName(), self.snpname[_idx])
			
			if not _snp.isfull():
				_base = _snp.getBase()
				if (_idx + 1) < len(self.snpname):
					self.assertEqual(_base, self.snpname[_idx + 1])

	def test_get_snapshots_by_timespan(self):
		raise NotImplementedError
	
	def test_get_snapshots_by_date(self):
		raise NotImplementedError

	def test_get_snp_history(self):
		raise NotImplementedError
	
	def testExportSnapshot(self):
		"""
		"""
		
	def test_rebase_ful_forbidden(self):
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_ful = snp_list[3]
				
		self.assertTrue(snp_ful.isfull())
		self.assertRaises(RebaseFullSnpForbidden, self.snpman.rebaseSnapshot,
						  snp_ful)

	def test_rebase_same_age_forbidden(self):
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_torebase = snp_list[0]
		snp_newbase = snp_list[0]
		self.assertRaises(RebaseSnpException, self.snpman.rebaseSnapshot,
						  snp_torebase, snp_newbase)

	def test_rebase_younger_forbidden(self):
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_torebase = snp_list[1]
		snp_newbase = snp_list[0]
		self.assertRaises(RebaseSnpException, self.snpman.rebaseSnapshot,
						  snp_torebase, snp_newbase)

	def test_rebase_onestep_ful_forbidden(self):
		"""
		@todo: Should raise a RebaseFullSnpForbidden exception!
		"""
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_ful = snp_list[3]
				
		self.assertTrue(snp_ful.isfull())
		self.assertRaises(SBException, self.snpman._rebaseOnLastSnp,
						  snp_ful)
	
	def test_pullsnp_inc_on_inc(self):
		"""
		"""
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_inc = snp_list[1]
		snp_inc_older = snp_list[2]
		
		self.assertFalse(snp_inc.isfull())
		self.assertFalse(snp_inc_older.isfull())
		
		self.snpman._pullSnpContent(snapshot=snp_inc, topullSnp=snp_inc_older)



	
class TestSnapshotMerge(unittest.TestCase):

	# Setting of path names
	snpname = [	"2009-01-21_13.07.43.156208.ayida.inc",
				"2009-01-21_13.05.19.000782.ayida.inc",
				"2009-01-21_12.59.16.564046.ayida.ful"				
			  ]
	
	def setUp(self):
		LogFactory.getLogger( level=10 )
	
		self.snppath = []
		for name in self.snpname:
			self.snppath.append(os.path.join(\
								_TestSnapshotMergePaths.get_snp_path(), name))

	
		self.__clean_dir()
		self.__untar_snapshots()

		# create SnapshotManager
		self.snpman = SnapshotManager(_TestSnapshotMergePaths.get_snp_path())
		
		
		
#	def tearDown(self):
#		self.__clean_dir()

	def __clean_dir(self):
		for _path in self.snppath:
			rmcmd = ["rm", "-rf", _path]
			subprocess.call(rmcmd)

	def __untar_snapshots(self):
		tarcmd = ["tar", "-xj",
				  "--directory=%s" % _TestSnapshotMergePaths.get_snp_path(),
				  "-f", "%s" % _TestSnapshotMergePaths.get_tar_path()]
		subprocess.call(tarcmd)
	
	def test_rebase_snapshot(self):
		raise NotImplementedError
	
	def test_convert_tofull_snapshot(self):
		raise NotImplementedError
	
	def test_rebaseonlast_inc_on_inc(self):
		"""
		"""
		snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
		snp_inc = snp_list[0]
		snp_inc_older = snp_list[1]
		
		self.assertFalse(snp_inc.isfull())
		self.assertFalse(snp_inc_older.isfull())
		
#		self.snpman._pullSnpContent(snapshot=snp_inc, topullSnp=snp_inc_older)
		self.snpman._rebaseOnLastSnp(snapshot=snp_inc)
		
		
		# only for debugging
		debug_print_snarfile(snp_inc.getSnarFile())
		debug_print_snarfile(_TestSnapshotMergePaths.get_res_snar())

		_snar1 = debug_snarfile_to_list(snp_inc.getSnarFile())
		_snar2 = debug_snarfile_to_list(_TestSnapshotMergePaths.get_res_snar())

		self.assertEqual(len(_snar1), len(_snar2))
		for idx in range(0, len(_snar1)):
			_record1 = _snar1[idx]
			_record2 = _snar2[idx]
			self.assertEqual(len(_record1), len(_record2))
			for idx2 in range(0, len(_record1) - 1):
				self.assertEqual(_record1[idx2], _record2[idx2])
				
			_content1 = _record1[-1]
			_content2 = _record2[-1]
			self.assertEqual(len(_content1), len(_content2))
			for idx2 in range(0, len(_content1)):
				self.assertEqual(_content1[idx2].getFilename(),
								 _content2[idx2].getFilename())
				self.assertEqual(_content1[idx2].getControl(),
								 _content2[idx2].getControl())
				
			
			

#	def test_rebase_onestep_inc_on_ful(self):
#		"""
#		"""
#		snp_list = self.snpman.getSnapshots(forceReload=True)
#		snp_inc = snp_list[1]
#		snp_ful = snp_list[3]
#		
#		self.assertFalse(snp_inc.isfull())
#		self.assertTrue(snp_ful.isfull())
#		
#		self.snpman._rebaseOnLastSnp(snp_inc)

#	def test_rebase_inc_on_ful(self):
#		"""
#		"""
#		snp_list = self.snpman.getSnapshots(forceReload=True)
#		snp_inc = snp_list[1]
#		snp_ful = snp_list[3]
#		
#		self.assertFalse(snp_inc.isfull())
#		self.assertTrue(snp_ful.isfull())
#		
#		self.snpman.rebaseSnapshot(torebase=snp_inc, newbase=snp_ful)
		
	
		
	def testCompareSnapshots(self):
		"""
		"""
	
#	def testGetRevertState(self):
#		"""
#		"""
#		snapshots = self.snpman.getSnapshots()
#		revertstate = self.snpman.getRevertState(snapshots[0], os.sep)
#		self.assertEqual(len(revertstate),3)
#		for k, v in revertstate.iteritems() :
#			print(k+" = "+str(v)) 
#		self.assertFalse(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_13.45.45.609201.wattazoum-vm.ful')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		revertstate = self.snpman.getRevertState(snapshots[1], "/home/wattazoum/Desktop/sbackup-test/")
#		self.assertEqual(len(revertstate),2)
#		self.assertFalse(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_13.45.45.609201.wattazoum-vm.ful')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		self.assertTrue(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_19.45.08.812921.wattazoum-vm.inc')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		
	def testPurge(self):
		"""
		"""
		
class TestSnapshotRemove(unittest.TestCase):
	"""Test case especially for testing the removal and purging
	of snapshots.
	"""

	# Setting of path names
	snpname = [	"2009-01-21_13.07.43.156208.ayida.inc",
				"2009-01-21_13.05.19.000782.ayida.inc",
				"2009-01-21_12.59.16.564046.ayida.ful"				
			  ]
	
	def setUp(self):
		LogFactory.getLogger( level=10 )
	
		self.snppath = []
		for name in self.snpname:
			self.snppath.append(os.path.join(\
								_TestSnapshotMergePaths.get_snp_path(), name))

	
		self.__clean_dir()
		self.__untar_snapshots()

		# create SnapshotManager
		self.snpman = SnapshotManager(_TestSnapshotMergePaths.get_snp_path())
	
#	def tearDown(self):
#		self.__clean_dir()

	def __clean_dir(self):
		for _path in self.snppath:
			rmcmd = ["rm", "-rf", _path]
			subprocess.call(rmcmd)

	def __untar_snapshots(self):
		tarcmd = ["tar", "-xj",
				  "--directory=%s" % _TestSnapshotMergePaths.get_snp_path(),
				  "-f", "%s" % _TestSnapshotMergePaths.get_tar_path()]
		subprocess.call(tarcmd)
	
	def test_remove_snapshot(self):
		"""
		"""
		raise NotImplementedError

def suite():
	"""Returns a test suite containing all test cases from this module.
	"""
	_suite = unittest.TestSuite()
	_suite.addTests(
		[
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshotRemove),
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshotManager),
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshotManagerFromDisk),
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshotMerge)
		])
	return _suite


if __name__ == "__main__":	
	unittest.TextTestRunner(verbosity=2).run(suite())

