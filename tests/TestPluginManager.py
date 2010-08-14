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
from sbackup.plugins import PluginManager

class TestPluginManager(unittest.TestCase):
    """
    """
    manager = None

    def setUp(self):
        ""
        self.manager = PluginManager()


    def testGetPlugins(self):
        " Get Plugins "
        for p_name, p_value in self.manager.getPlugins().iteritems() :
            print p_name, p_value , type(p_value)
            foo = p_value()
            print foo.match_scheme_full("ssh://user:pass@example.com/home/user/backup/")

suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginManager)
unittest.TextTestRunner(verbosity = 2).run(suite)
