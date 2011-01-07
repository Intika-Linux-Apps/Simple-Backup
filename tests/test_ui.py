#   Simple Backup - UI unit tests 
#
#   Copyright (c)2011: Jean-Peer Lorenz <peer.loz@gmx.net>
#
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


import unittest
import gtk

from sbackup.ui import misc

class TestMiscMessageDialog(unittest.TestCase):
    """Testing function 'misc.msgdialog'.
    """

    def setUp(self):
        pass

    def test_simple_plain(self):
        _msg = "Test with content 'user xy.com'"
        _mtype = gtk.MESSAGE_ERROR
        _par = None
        _dialog = misc.msgdialog(message_str = _msg, msgtype = _mtype, parent = _par)
        self.assertTrue(isinstance(_dialog, gtk.MessageDialog))

    def test_simple_commercial(self):
        _msg = "Test with commercial: 'user@xy.com'"
        _mtype = gtk.MESSAGE_ERROR
        _par = None
        _dialog = misc.msgdialog(message_str = _msg, msgtype = _mtype, parent = _par)
        self.assertTrue(isinstance(_dialog, gtk.MessageDialog))

    def test_simple_ampersand(self):
        _msg = "Test with ampersand: 'user & xy.com'"
        _mtype = gtk.MESSAGE_ERROR
        _par = None
        _dialog = misc.msgdialog(message_str = _msg, msgtype = _mtype, parent = _par)
        self.assertTrue(isinstance(_dialog, gtk.MessageDialog))

    def test_simple_greater(self):
        _msg = "Test with <content>: 'user xy.com'"
        _mtype = gtk.MESSAGE_ERROR
        _par = None
        _dialog = misc.msgdialog(message_str = _msg, msgtype = _mtype, parent = _par)
        self.assertTrue(isinstance(_dialog, gtk.MessageDialog))

    def test_simple(self):
        _msg = "Test with <content>: 'user@xy.com' & 'another@ab.org'"
        _mtype = gtk.MESSAGE_ERROR
        _par = None
        _dialog = misc.msgdialog(message_str = _msg, msgtype = _mtype, parent = _par)
        self.assertTrue(isinstance(_dialog, gtk.MessageDialog))

def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([ unittest.TestLoader().loadTestsFromTestCase(TestMiscMessageDialog)
                   ])
    return _suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity = 2).run(suite())
