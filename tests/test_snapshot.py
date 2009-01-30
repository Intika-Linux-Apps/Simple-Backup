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

"""Unittests for testing the class 'Snapshot'.
"""


import os
import os.path
import unittest
import pickle
import subprocess

from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import NotValidSnapshotNameException
from nssbackup.util.exceptions import NotValidSnapshotException

from nssbackup.util import Snapshot
from nssbackup.util.log import LogFactory


class _TestSnapshotPaths(object):
	"""This class only purpose is to provide pathnames to input/output test
	data from a single place to avoid multiple definitions of them.
	"""
	# definition of paths for testing the class 'Snapshot'
	__abspath_testdir	= os.path.abspath("./")
	__snp_path_rel		= "test-datas/test-snapshot/out"
	__in_path_rel  		= "test-datas/test-snapshot/in"
	__tar_rel      		= "test-datas/test-snapshot/test-snapshot.tar.bz2"
	
	def __init__(self):
		pass

	def get_snp_path():
		"""Returns the absolute path to the existing snapshots to be tested.
		"""
		_path = os.path.join(_TestSnapshotPaths.__abspath_testdir,
							 _TestSnapshotPaths.__snp_path_rel)
		return _path
	get_snp_path = staticmethod(get_snp_path)

	def get_docinput_path():
		"""Returns the absolute path to the documents for creation of a new
		snapshot.
		"""
		_path = os.path.join(_TestSnapshotPaths.__abspath_testdir,
							 _TestSnapshotPaths.__in_path_rel)
		return _path
	get_docinput_path = staticmethod(get_docinput_path)

	def get_tar_path():
		"""Returns the absolute path to the tar-archive containing the
		snapshots to be tested.
		"""
		_path = os.path.join(_TestSnapshotPaths.__abspath_testdir,
							 _TestSnapshotPaths.__tar_rel)
		return _path
	get_tar_path = staticmethod(get_tar_path)


class TestSnapshot(unittest.TestCase):
	version = "1.5"

	# name of the snapshot to be created
	snp_valid_ful_names = ["2005-11-11_10.27.17.276340.created.ful",
					       "2005-11-11_10:27:17.276340.created.ful"
					  ]

	snp_valid_inc_names = ["2005-11-11_10.27.17.276340.created.inc",
					       "2005-11-11_10:27:17.276340.created.inc"
					  ]
	
	snp_invalid_names = [ "205-11-11_10.27.17.276340.created.ful",
						  "2005-1-11_10.27.17.276340.created.ful",
						  "2005-11-1_10.27.17.276340.created.ful",
						  "205-1-1_10.27.17.276340.created.ful",
						  "2005.11.11_10.27.17.276340.created.ful",
						  "2005.11.11-10.27.17.276340.created.ful",
						  "2005-11-11_1.27.17.276340.created.ful",
						  "2005-11-11_10.2.17.276340.created.ful",
						  "2005-11-11_10.27.7.276340.created.ful",
						  "2005-11-11_10.27.17.created.ful",
						  "2005-11-11_10.27.17.276340.created.flu",
						  "2005-11-11_10.27.17.276340.created.dif"
					    ]
	
	def setUp(self):
		LogFactory.getLogger( level=10 )
		self.__clean_dir()

	def tearDown(self):
		self.__clean_dir()

	def __clean_dir(self):
		for val_name in self.__get_all_valid_names():
			tdir = os.path.join(_TestSnapshotPaths.get_snp_path(), val_name)
#			print "VAL: %s" % tdir
			rmcmd = ["rm", "-rf", tdir]
			subprocess.call(rmcmd)
				
	def test_constructor(self):
		"""Creation of snapshot without commit.
		"""
		val_names = self.__get_all_valid_names()
		for val_name in val_names:
			tdir = os.path.join(_TestSnapshotPaths.get_snp_path(), val_name)
#			print "VAL: %s" % tdir
			snp = Snapshot.Snapshot(tdir)
		
			# evaluate test
			self.assertTrue(os.path.exists(tdir))
			self.assertFalse( os.path.exists( os.path.join(tdir, "ver") ) )
			del snp
		
	def test_constructor_fails(self):
		"""Creation of snapshot that will fail.
		"""
		for ill_name in self.snp_invalid_names:
			tdir = os.path.join(_TestSnapshotPaths.get_snp_path(), ill_name)
#			print "ILL: %s" % tdir
			self.assertRaises(NotValidSnapshotNameException,
							  Snapshot.Snapshot, tdir)

	# test the setter methods	
	def test_set_splitted_size(self):
		"""Test setting of split size
		
		@todo: Wrong parameter type should raise a TypeError!
		"""
		snp = self.__create_full_snapshot()
		
		# giving no parameter raises TypeError
		self.assertRaises( TypeError, snp.setSplitedSize )

		# integer is required
		self.assertRaises( TypeError, snp.setSplitedSize, "100" )
		
		size = 1024
		snp.setSplitedSize(size)
		self.assertEqual(size, snp.getSplitedSize())
		
	def test_set_base_full(self):
		"""Test setting of base snapshot for full snapshot
		"""
		snp = self.__create_full_snapshot()
		
		for name in self.snp_invalid_names:
			self.assertRaises( SBException, snp.setBase, name )

		for name in self.__get_all_valid_names():
			self.assertRaises( SBException, snp.setBase, name )
			self.assertEqual(None, snp.getBase())
			self.assertEqual(None, snp.getBaseSnapshot())
			
	def test_set_base_inc(self):
		"""Test setting of base snapshot for incremental snapshot
		"""
		snp = self.__create_inc_snapshot()
		
		for name in self.snp_invalid_names:
			self.assertRaises( SBException, snp.setBase, name )

		for name in self.__get_all_valid_names():
			snp.setBase(name)
			self.assertEqual(name, snp.getBase())

			
#	def testaddFile(self) :
#		"""
#		Add an item to be backup into the snapshot.
#		Usage :  addFile(item, props) where
#		- item is the item to be add (file, dir, or link)
#		- props is this item properties
#		"""
				
#	def testsetExcludes(self) :
#		"""
#		Set the content of excludes
#		"""

	def __get_all_valid_names(self):
		val_names = self.snp_valid_ful_names[:]
		val_names.extend(self.snp_valid_inc_names)
		return val_names

	def __create_full_snapshot(self):
		val_name = self.snp_valid_ful_names[0]
		tdir = os.path.join(_TestSnapshotPaths.get_snp_path(), val_name)
		snp = Snapshot.Snapshot(tdir)
		return snp

	def __create_inc_snapshot(self):
		val_name = self.snp_valid_inc_names[0]
		tdir = os.path.join(_TestSnapshotPaths.get_snp_path(), val_name)
		snp = Snapshot.Snapshot(tdir)
		return snp


class TestSnapshotFromDisk(unittest.TestCase):
	version = "1.5"

	# Setting of path names
	snp_ful_name = "2009-01-18_19.58.47.492348.hostname.ful"
	snp_inc_name = "2009-01-18_19.59.15.167252.hostname.inc"
	
	def setUp(self):
		LogFactory.getLogger( level=10 )
	
		self.snappath_ful = os.path.join(_TestSnapshotPaths.get_snp_path(), self.snp_ful_name)
		self.snappath_inc = os.path.join(_TestSnapshotPaths.get_snp_path(), self.snp_inc_name)

		self.in_path_abs = _TestSnapshotPaths.get_docinput_path()
		
#		print "ABSPATH TESTDIR: '%s'\nSNAPPATH FUL: '%s'\nSNAPPATH INC: '%s'"\
#			  "\nSNAPPATH NEW: '%s'"\
#				% (self.abspath_testdir, self.snappath_ful,
#				   self.snappath_inc, self.snappath_new)
	
		self.__clean_dir()
		self.__untar_snapshots()

		# creation of snapshots
		self.snapshot_ful = Snapshot.Snapshot(self.snappath_ful)
		self.snapshot_inc = Snapshot.Snapshot(self.snappath_inc)

	def tearDown(self):
		self.__clean_dir()

	def __clean_dir(self):
		rmcmd = ["rm", "-rf", self.snappath_ful, self.snappath_inc]
		subprocess.call(rmcmd)

	def __untar_snapshots(self):
		tarcmd = ["tar", "-xj",
				  "--directory=%s" % _TestSnapshotPaths.get_snp_path(),
				  "-f", "%s" % _TestSnapshotPaths.get_tar_path()]
		subprocess.call(tarcmd)
		
	def testgetName(self) :
		"""get the right name of a snapshot"""
		self.assertEqual( self.snapshot_ful.getName(), self.snp_ful_name)
		
	def testgetPath(self) :
		"""get the right path of a snapshot"""
		self.assertEqual( self.snapshot_ful.getPath(), self.snappath_ful)
		
	def test_getdate(self):
		_date_templ = "2009-01-18_19.58.47"
		_date = self.snapshot_ful.getDate()
		
		self.assertTrue(isinstance(_date, dict))
		
		for _key, _item in _date.items():
			self.assertTrue(isinstance(_item, int))

		_date_str = "%04d-%02d-%02d_%02d.%02d.%02d" % (_date['year'],
								_date['month'], _date['day'],
								_date['hour'], _date['minute'], _date['second']) 
		self.assertEqual(_date_templ, _date_str)

	def testsetPath(self) :
		"""set another path/name after the snapshot creation"""
		self.snapshot_inc.setPath("/home/a_directory/2007-05-03_21.58.59.109550.SetPath.inc")
		self.assertEqual( self.snapshot_inc.getPath(),
					"/home/a_directory/2007-05-03_21.58.59.109550.SetPath.inc")
		self.assertEqual( self.snapshot_inc.getName(),
					"2007-05-03_21.58.59.109550.SetPath.inc")

	def testsetFalsePath(self):
		"""an exception is raised if the path is not valid"""
		self.assertRaises( SBException , self.snapshot_ful.setPath,
						"/xyz/xyz/xyz-hopefully this path does not exist")
	
	def testgetBase_inc(self) :
		"""base snapshot of this Inc snapshot"""
		self.assertEqual(self.snapshot_inc.getBase(), self.snp_ful_name)
		
	def testgetBase_ful(self) :
		"""Full backups got no base file"""
		self.assertFalse(self.snapshot_ful.getBase())

	def testgetVersion(self) :
		"""Test if we get the correct version"""
		self.assertEqual(self.snapshot_ful.getVersion(), self.version)
		self.assertEqual(self.snapshot_inc.getVersion(), self.version)
		
	def testgetExcludes(self) :
		"""get the exclude file content"""
		f = open(os.path.join(self.snappath_ful, "excludes"))
		toget = pickle.load(f)
		f.close()
		self.assertEqual(self.snapshot_ful.getExcludes(), toget)		

		f = open(os.path.join(self.snappath_inc, "excludes"))
		toget = pickle.load(f)
		f.close()
		self.assertEqual(self.snapshot_inc.getExcludes(), toget)		
		

	
	# Setters
	
	
#	def testsetBase(self) :
#		"""
#		Set the name of the base snapshot of this snapshot
#		"""
#			
#	def testaddFile(self) :
#		"""
#		Add an item to be backup into the snapshot.
#		Usage :  addFile(item, props) where
#		- item is the item to be add (file, dir, or link)
#		- props is this item properties
#		"""
		
	def testsetVersion(self) :
		" Set the version of the snapshot "
		self.snapshot_ful.setVersion("1.9")
		self.assertEqual(self.snapshot_ful.getVersion(), "1.9")
		
#	def testsetExcludes(self) :
#		"""
#		Set the content of excludes
#		"""
		
	def testsetPackages(self) :
		" set the packages list for debian based distros "
		p = os.popen("dpkg --get-selections")
		pack = p.read()
		self.snapshot_ful.setPackages(pack)
		p.close()
		self.assertEqual(self.snapshot_ful.getPackages(),pack)
	
	def testgetPackages(self) :
		"""get the packages"""
		f = open(os.path.join(self.snappath_ful, "packages"))
		toget = f.read()
		f.close()
		self.assertEqual(self.snapshot_ful.getPackages(), toget)

		f = open(os.path.join(self.snappath_inc, "packages"))
		toget = f.read()
		f.close()
		self.assertEqual(self.snapshot_inc.getPackages(), toget)


class TestSnapshotCreateToDisk(unittest.TestCase):
	version = "1.5"

	# name of the snapshot to be created
	snp_new_name = "2009-01-16_13.27.17.276540.created.ful"
	
	def setUp(self):
		LogFactory.getLogger( level=10 )

		self.snappath_new = os.path.join(_TestSnapshotPaths.get_snp_path(), self.snp_new_name)
		self.in_path_abs = _TestSnapshotPaths.get_docinput_path()		
#		print "SNAPPATH NEW: '%s'"\ % (self.snappath_new)
		self.__clean_dir()

	def tearDown(self):
		self.__clean_dir()

	def __clean_dir(self):
		rmcmd = ["rm", "-rf", self.snappath_new]
		subprocess.call(rmcmd)
				
	def test_create_full_snapshot(self):
		"""Creation of snapshot including 'commit' i.e. writing to the disk.
		"""
		# this is the list of files that should be stored in the created archive
		tar_list_result = "%s/\n%s" % (os.path.join(self.in_path_abs,
											"some_directory").lstrip(os.sep),
							os.path.join(self.in_path_abs,
							"some_directory/this is a testdoc").lstrip(os.sep))

		# creation of a new snapshot
		tdir = self.snappath_new
		snp = Snapshot.Snapshot(tdir)
		
		# including and excluding some files
		snp.addToIncludeFlist(os.path.join(self.in_path_abs, "some_directory"))
		snp.addToIncludeFlist(os.path.join(self.in_path_abs, "some_directory",
										"another_directory/test.txt"))
		snp.addToExcludeFlist(os.path.join(self.in_path_abs,
										"some_directory/another_directory"))
		
		snp.commit()

		# evaluate test
		self.assertTrue(snp.isfull())
		self.assertTrue(os.path.exists(tdir))
		self.assertTrue(os.path.exists(os.path.join(tdir, "ver")))
		self.assertEqual(snp.getVersion(), self.version)
		
		# compare file lists
		tarcmd = ["tar", "-z", "--list",
				  "-f", "%s" % os.path.join(self.snappath_new, "files.tar.gz")]
		outp = subprocess.Popen(tarcmd, stdout=subprocess.PIPE).communicate()[0]		
		self.assertEqual(outp.strip(), tar_list_result)
	
	
	
	# Setters
	
	
#	def testsetBase(self) :
#		"""
#		Set the name of the base snapshot of this snapshot
#		"""
#			
#	def testaddFile(self) :
#		"""
#		Add an item to be backup into the snapshot.
#		Usage :  addFile(item, props) where
#		- item is the item to be add (file, dir, or link)
#		- props is this item properties
#		"""
				
#	def testsetExcludes(self) :
#		"""
#		Set the content of excludes
#		"""
		
		
		
def suite():
	"""Returns a test suite containing all test cases from this module.
	"""
	_suite = unittest.TestSuite()
	_suite.addTests(
		[
	     unittest.TestLoader().loadTestsFromTestCase( TestSnapshotFromDisk ),
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshotCreateToDisk),
		 unittest.TestLoader().loadTestsFromTestCase( TestSnapshot )
		])
	return _suite


if __name__ == "__main__":	
	unittest.TextTestRunner(verbosity=2).run(suite())
