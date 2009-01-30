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


import os
import unittest
from nssbackup.util.exceptions import SBException,NonValidOptionException
from nssbackup.managers.ConfigManager import ConfigManager 

class TestConfigManager(unittest.TestCase):

	def setUp(self):
		self.config = ConfigManager()

	def testinitSection(self):
		" Init the config sections "
		self.config.initSection()
		self.assertTrue(self.config.has_section("general"))
		self.assertTrue(self.config.has_section("dirconfig"))
		self.assertTrue(self.config.has_section("places"))
		self.assertTrue(self.config.has_section("exclude"))
		self.assertEqual(len(self.config.sections()),7)
	
	def testsetDefaultForRoot(self):
		"Set the default config for root user"
		if os.geteuid() != 0 :
			self.assertRaises(IOError, self.config.setDefaultForRoot )
		else :
			self.config.setDefaultForRoot()
			self.assertTrue(os.path.exists("/var/log/nssbackup.log"))
	
	def testsetDefaultForUsers(self):
		"Set the default config for normal users"	
		self.config.setDefaultForUsers()
	
	def testread(self):
		"Testing the config file read function "
		self.assertRaises(SBException, ConfigManager, "sbackup.conf.fake")
		self.config = ConfigManager("test-datas/sbackup.conf.good")
		self.assertEqual(self.config.conffile, "test-datas/sbackup.conf.good")
#		for s in self.config.sections():
#			print str(s)
#		self.assertEqual(len(self.config.sections()),3)
		self.assertEqual(len(self.config.options("dirconfig")),10)
		self.assertEqual(len(self.config.options("general")),4)
		self.assertEqual(len(self.config.options("exclude")),2)
		
	def testparse_commandline(self):
		""
		self.config.parseCmdLine()
		
	def testIsConfigEquals(self):
		""
		self.assertFalse(self.config.isConfigEquals(ConfigManager("test-datas/sbackup.conf.good")))
		self.config = ConfigManager("test-datas/sbackup.conf.good")
		self.assertTrue(self.config.isConfigEquals(ConfigManager("test-datas/sbackup.conf.good")))

	def testvalidate_config_file_options(self):
		"Validate config file"
		self.assertRaises(NonValidOptionException, ConfigManager, "test-datas/sbackup.conf.bad")
		self.config = ConfigManager("test-datas/sbackup.conf.good")
		self.assertTrue(self.config.validateConfigFileOpts)
		
suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigManager)
unittest.TextTestRunner(verbosity=2).run(suite)
