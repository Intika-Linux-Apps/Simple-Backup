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
#    Jean-Peer Lorenz <peer.loz@gmx.net>


import os
import unittest
from nssbackup import util as Util

class TestUtilsRemoveConfEntry(unittest.TestCase):
    """Testing function 'util.remove_conf_entry'.
    """

    def setUp(self):
        pass

    def test_types(self):
        """Given parameter types for function 'util.remove_conf_entry'.
        """
        confline = ["adjh", "fdshf"]
        rm_entry = "skjsfhk"
        delim = "akjdlj"
        self.assertRaises(TypeError, Util.remove_conf_entry, confline, rm_entry, delim)

        confline = "skjsfhk"
        rm_entry = ["adjh", "fdshf"]
        delim = "akjdlj"
        self.assertRaises(TypeError, Util.remove_conf_entry, confline, rm_entry, delim)

        confline = "skjsfhk"
        rm_entry = "skjsfhk"
        delim = ["adjh", "fdshf"]
        self.assertRaises(TypeError, Util.remove_conf_entry, confline, rm_entry, delim)

    def test_simple(self):
        """Simple removal of configuration entry.
        """
        confline = "entry_a,entry_b,entry_c"

        target_val = "entry_b,entry_c"
        rm_entry = "entry_a"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

        target_val = "entry_a,entry_c"
        rm_entry = "entry_b"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

        target_val = "entry_a,entry_b"
        rm_entry = "entry_c"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

    def test_simple_with_spaces(self):
        """Simple removal of configuration entry from input containing spaces.
        """
        confline = " entry_a , entry_b , entry_c "

        target_val = " entry_b , entry_c "
        rm_entry = " entry_a "
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

        target_val = " entry_a , entry_c "
        rm_entry = " entry_b "
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

        target_val = " entry_a , entry_b "
        rm_entry = " entry_c "
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

    def test_entry_not_contained(self):
        """Removal of not contained configuration entry.
        """
        confline = "entry_a,entry_b,entry_c"
        target_val = "entry_a,entry_b,entry_c"
        rm_entry = "entry_d"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

    def test_entry_double_not_contained(self):
        """Removal of two entries not in given order.
        @todo: This test case needs to be reviewed!
        """
        confline = "entry_a,entry_b,entry_c"
        target_val = "entry_a,entry_b,entry_c"
        rm_entry = "entry_a,entry_c"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)

    def test_entry_double(self):
        """Removal of two entries in given order.
        @todo: This test case needs to be reviewed!
        """
        confline = "entry_a,entry_b,entry_c"
        target_val = "entry_c"
        rm_entry = "entry_a,entry_b"
        res = Util.remove_conf_entry(confline, rm_entry)
        self.assertEqual(res, target_val)


class TestUtilsRegex(unittest.TestCase):
    """Testing of regexp related functions.
    """

    def setUp(self):
        pass

    def test_types(self):
        """Given parameter types for regexp related functions.
        """
        regex = ["[]", "{}"]
        self.assertRaises(TypeError, Util.is_empty_regexp, regex)
        self.assertRaises(TypeError, Util.is_valid_regexp, regex)

    def test_is_valid(self):
        """Given regexp is valid.
        @todo: Extend number of tested expressions!
        """
        regex = ""
        self.assertTrue(Util.is_valid_regexp(regex))
        regex = "()"
        self.assertTrue(Util.is_valid_regexp(regex))

    def test_is_not_valid(self):
        """Given regexp is invalid.
        @todo: Extend number of tested expressions!
        """
        regex = "[[["
        self.assertFalse(Util.is_valid_regexp(regex))

    def test_is_empty(self):
        """Given regexp is empty.
        """
        regex = ""
        self.assertTrue(Util.is_empty_regexp(regex))
        regex = " "
        self.assertTrue(Util.is_empty_regexp(regex))
        regex = "\t"
        self.assertTrue(Util.is_empty_regexp(regex))
        regex = "\t \n"
        self.assertTrue(Util.is_empty_regexp(regex))

    def test_is_not_empty(self):
        """Given regexp is not empty.
        """
        regex = "[[["
        self.assertFalse(Util.is_empty_regexp(regex))

        regex = "[  [["
        self.assertFalse(Util.is_empty_regexp(regex))


class TestUtilsNssbCopy(unittest.TestCase):
    """Testing of nssbcopy related functions.
    """

    def setUp(self):
        self.src_relpath = "./test-datas/test_utils.src"
        self.dst_relpath = "./test-datas/test_utils.dst"
        self.dst_reldir = "./test-datas/test-utils/"
        self.dst_reldir_notexist = "./test-datas/test-utils.notexisting/"

        self.src_abspath = os.path.abspath(self.src_relpath)
        self.dst_abspath = os.path.abspath(self.dst_relpath)
        self.dst_absdir = os.path.abspath(self.dst_reldir)
        self.dst_absdir_notexist = os.path.abspath(self.dst_reldir_notexist).rstrip(os.path.sep) + os.path.sep

    def test_prepare_types(self):
        """Given parameter types for nssbcopy related functions.
        """
        src = ["test", "test"]
        dst = "test"
        self.assertRaises(TypeError, Util._prepare_nssb_copy, src, dst)

        src = "test"
        dst = ["test", "test"]
        self.assertRaises(TypeError, Util._prepare_nssb_copy, src, dst)

    def test_prepare_relpath(self):
        self.assertRaises(ValueError, Util._prepare_nssb_copy,
                          self.src_relpath,
                          self.dst_abspath)

        self.assertRaises(ValueError, Util._prepare_nssb_copy,
                          self.src_abspath,
                          self.dst_relpath)

    def test_prepare_not_exist(self):
        src = self.src_abspath + "notexisting"
        self.assertRaises(IOError, Util._prepare_nssb_copy,
                          src,
                          self.dst_abspath)

#    def test_prepare_new_name(self):
#        Util._prepare_nssb_copy( self.src_abspath, self.dst_abspath )
#
#    def test_prepare_same_name(self):
#        Util._prepare_nssb_copy( self.src_abspath, self.dst_absdir )

    def test_prepare_same_name_not_exist(self):
        self.assertRaises(IOError, Util._prepare_nssb_copy,
                          self.src_abspath,
                          self.dst_absdir_notexist)

    def test_copy_same_name(self):
        Util.nssb_copy(self.src_abspath, self.dst_absdir)


def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([ unittest.TestLoader().loadTestsFromTestCase(TestUtilsRemoveConfEntry),
                     unittest.TestLoader().loadTestsFromTestCase(TestUtilsRegex),
                     unittest.TestLoader().loadTestsFromTestCase(TestUtilsNssbCopy)
                   ])
    return _suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity = 2).run(suite())
