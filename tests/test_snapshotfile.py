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
#   (c)2010 - Jean-Peer Lorenz <peer.loz@gmx.net>

"""Unittests for testing...
"""

import sys
import os.path
import unittest

from nssbackup.util.log import LogFactory
from nssbackup.util import tar
from nssbackup.util import file_handling as fam


LOGLEVEL = 100


class TestSnapshotfile(unittest.TestCase):

#	__file = os.path.abspath("./test-datas/test-snapshotfile/files_big.snar")
	__file = os.path.abspath("./test-datas/test-snapshotfile/files_ful.snar")

	def setUp(self):
		LogFactory.getLogger(level = LOGLEVEL)

	def tearDown(self):
		pass

	def test_constructor(self):
		snar = tar.SnapshotFile(self.__file)
#		print str(snar)
		_time = snar.get_time_of_backup()
		print "Time of backup: %s sec" % (_time)

		_dict = snar.get_dict_format2()

		for _item in _dict:
			print _item, _dict[_item]

#		_size = sys.getsizeof(_dict)
#		mb = _size / (1000*1000)
#		kb = ( _size % (1000*1000) ) / 1000
#		b = ( _size % (1000*1000) ) % 1000
#		print "Size: %s MB %s kB %s" % (mb, kb, b) 


def suite():
	"""Returns a test suite containing all test cases from this module.
	"""
	_loader = unittest.TestLoader().loadTestsFromTestCase
	_suite = unittest.TestSuite()
	_suite.addTests(
		[
		 _loader(TestSnapshotfile)
		])
	return _suite


if __name__ == "__main__":
	unittest.TextTestRunner(verbosity = 2).run(suite())
