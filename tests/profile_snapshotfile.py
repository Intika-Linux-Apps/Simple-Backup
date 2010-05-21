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


import sys
import os.path
import unittest

from nssbackup.util.log import LogFactory
from nssbackup.util import tar
from nssbackup.managers import FileAccessManager as fam

import cProfile

LOGLEVEL = 100


class TestSnapshotfile(object):

	__file = os.path.abspath("./test-datas/test-snapshotfile/files.snar")
#	__file = os.path.abspath("./test-datas/test-snapshotfile/files_ful.snar")
	
	def __init__(self):
		pass
	
	def setUp(self):
		LogFactory.getLogger( level=LOGLEVEL )

	def tearDown(self):
		pass
				
	def test_constructor(self):
		snar = tar.SnapshotFile(self.__file)
#		print str(snar)
		_time = snar.get_time_of_backup()
		print "Time of backup: %s sec" % (_time)
		
#		_dict = snar.get_dict_format2()
		self.read_on_demand(snar)
		
#		_size = sys.getsizeof(_dict)
#		mb = _size / (1000*1000)
#		kb = ( _size % (1000*1000) ) / 1000
#		b = ( _size % (1000*1000) ) % 1000
#		print "Size: %s MB %s kB %s" % (mb, kb, b) 

#		self.read_dict(_dict)

	def read_dict(self, adict):
		for _item in adict:
			adict[_item] = 'M'
			
	def read_on_demand(self, snar):
		for _record in snar.parseFormat2():
			pass


	def main(self):
		self.setUp()
		self.test_constructor()
		self.tearDown()
						

if __name__ == "__main__":
	tsnp = TestSnapshotfile()
	cProfile.run('tsnp.main()')
	
