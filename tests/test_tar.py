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
#    Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>
#   Jean-Peer Lorenz <peer.loz@gmx.net>

import unittest
import os
import subprocess
import datetime

from sbackup.util.tar import SnapshotFile
from sbackup.util.tar import MemSnapshotFile
from sbackup.util.tar import ProcSnapshotFile
from sbackup.util.tar import Dumpdir
from sbackup.util.tar import getArchiveType
from sbackup.util.tar import get_dumpdir_from_list

from sbackup.util.log import LogFactory
from sbackup.util.exceptions import SBException


class _TestTarPaths(object):
    """This class only purpose is to provide pathnames to input/output test
    data from a single place to avoid multiple definitions of them.
    """
    # definition of paths for testing the class 'SnapshotManager'
    __abspath_testdir = os.path.abspath("./")
    __data_path_rel = "test-datas/test-tar"

    @classmethod
    def get_data_path(cls):
        """Returns the absolute path to the existing test data.
        """
        _path = os.path.join(cls.__abspath_testdir,
                             cls.__data_path_rel)
        return _path

    @classmethod
    def get_path(cls, filename):
        """Returns the absolute path to the filename in test data directory.
        """
        _path = os.path.join(cls.__abspath_testdir,
                             cls.__data_path_rel,
                             filename.strip(os.path.sep))
        return _path


class TestDumpdir(unittest.TestCase):
    """Test case for testing the class Dumpdir from the tar module.
    """

    def test_constructor_fails(self):
        self.assertRaises(TypeError, Dumpdir, None)
        self.assertRaises(TypeError, Dumpdir, ["testline"])
        self.assertRaises(ValueError, Dumpdir, "Y")

    def test_constructor(self):
        line = "testline"
        Dumpdir(line)

    def test_getter(self):
        """Getting control and filename that should partially fail.
        
        @todo: More checks need to be implemented in class!
        """
        line = "testline"
        dmpd = Dumpdir(line)
        self.assertEqual("t", dmpd.getControl())
        self.assertEqual("estline", dmpd.getFilename())

        line = "testline\0"
        dmpd = Dumpdir(line)
        self.assertEqual("t", dmpd.getControl())
        self.assertEqual("estline", dmpd.getFilename())

        line = "Y/home/username/doc/filename"
        dmpd = Dumpdir(line)
        self.assertEqual("Y", dmpd.getControl())
        self.assertEqual("/home/username/doc/filename", dmpd.getFilename())


class TestSnapshotFile(unittest.TestCase):
    snarfn_new = "test-snapshotfile.created.snar"
    snarfn_notexist = "test-snapshotfile.notexisting.snar"

    def setUp(self):
        """This method is called before processing of each test.
        
        @todo: Modify setting of file paths!
        """
        self.snarfile = _TestTarPaths.get_path("test-snapshotfile.snar")
        self.snarsnpfile_path = _TestTarPaths.get_path("files.snar")
        self.snarsnpfile2_path = _TestTarPaths.get_path("files-2.snar")

        self.snarf_new = _TestTarPaths.get_path(self.snarfn_new)
        self.snarf_notexist = _TestTarPaths.get_path(self.snarfn_notexist)
        self.__clean_dir()
        self.__copy_template()

        # existing snarfiles
        self.snarSNPfile = SnapshotFile(self.snarsnpfile_path)
        self.snarSNPfile2 = SnapshotFile(self.snarsnpfile2_path)


    def tearDown(self):
        """This method is called after processing of each test.
        """
        self.__clean_dir()

    def __clean_dir(self):
        """Private helper method that removes eventually created test data
        from the test-data directory to keep it clean.
        """
        rmlst = [ self.snarfile, self.snarf_new, self.snarf_notexist,
                  self.snarsnpfile_path, self.snarsnpfile2_path
                ]
        for rm in rmlst:
            if os.path.exists(rm):
                os.remove(rm)

    def __get_templates(self):
        _rel_dir = "templates"
        _templates = [ "test-snapshotfile.snar.template",
                       "files.snar.template",
                       "files-2.snar.template"
                     ]
        _res = []
        for _templ in _templates:
            _path_templ = _TestTarPaths.get_path(os.path.join(_rel_dir, _templ))
            _path_target = _TestTarPaths.get_path(_templ.rstrip(".template"))
            _res.append({"template": _path_templ, "target": _path_target})
        return _res

    def __copy_template(self):
        """Private helper method that copies the template snarfile
        into the destination snarfile. This is done to avoid unwanted
        modifications of the snarfile for further tests.
        """
        _templates = self.__get_templates()
        print "TEMPLATES: %s" % _templates
        for _templ in _templates:
            rmcmd = ["cp", "-f", _templ["template"], _templ["target"]]
            subprocess.call(rmcmd)

    def testGetFormatVersion(self):
        """Get the SNAR file version"""
        self.assertEqual(self.snarSNPfile.getFormatVersion(), 2)

    def testParseFormat2(self):
        """Parse the SNAR file"""
        for f in self.snarSNPfile.parseFormat2():
            print f[-2] + "\t"
            for d in f[-1] :
                print str(d)

    def testMemSnasphotFile(self):
        " Create and read a MemSnapshotFile "
        msnpf = MemSnapshotFile(self.snarSNPfile)
        for i in msnpf.getContent("/home/wattazoum/Images/camescope/2007-04-08--09.09.05") :
            print str(i)
        print msnpf

    def testGetFirstItems(self):
        " Get the list of first items into a snarfile"
        psnpf = ProcSnapshotFile(self.snarSNPfile)
        #print psnpf.getFirstItems()
        self.assertEqual(len(psnpf.getFirstItems()), 1)
        self.assertEquals(psnpf.getFirstItems(), ['/home/wattazoum/Images/camescope'])

        psnpf = ProcSnapshotFile(self.snarSNPfile2)
        #print psnpf.getFirstItems()
        self.assertEqual(len(psnpf.getFirstItems()), 4)

        msnpf = MemSnapshotFile(self.snarSNPfile2)
        #print msnpf.getFirstItems()
        self.assertEqual(len(msnpf.getFirstItems()), 4)
        self.assertEqual(msnpf.getFirstItems(), psnpf.getFirstItems())

    def testWriteSNARfile(self):
        " Test the writng of SNARfile functionalities "
        if os.path.exists("test-datas" + os.sep + "test-files.snar"):
            os.remove("test-datas" + os.sep + "test-files.snar")
        snpf = SnapshotFile("test-datas" + os.sep + "test-files.snar", True)
        import datetime
        snpf.setHeader(datetime.datetime.now())
        self.assertEqual(snpf.getFormatVersion(), 2)
        entry = ['0', '1195399253', '1195399253', '2049', '420738', "/home/wattazoum/Images",
            [Dumpdir('%scamescope' % Dumpdir.DIRECTORY),
             Dumpdir('%sarticle.html' % Dumpdir.INCLUDED)]
            ]
        snpf.addRecord(entry)

        snpf2 = ProcSnapshotFile(snpf)
        self.assertTrue(snpf2.hasFile("/home/wattazoum/Images/article.html"))
        self.assertTrue(snpf2.hasPath("/home/wattazoum/Images"))

    def test_create_SnapshotFile_newfile(self):
        """Instantiation of SnapshotFile with creation of SNAR-file.
        """
        header_templ = None
        version_templ = int(0)

        snpf = SnapshotFile(self.snarf_new, writeFlag = True)
        header = snpf.getHeader()
        self.assertEqual(header_templ, header)
        version = snpf.getFormatVersion()
        self.assertEqual(version_templ, version)

    def test_create_SnapshotFile_fails(self):
        """Instantiation of SnapshotFile with creation of SNAR-file.
        """
        self.assertRaises(SBException, SnapshotFile, self.snarf_notexist, writeFlag = False)

    def test_create_SnapshotFile(self):
        """Instantiation of SnapshotFile using an existing SNAR-file.
        """
        SnapshotFile(self.snarfile)

    def test_get_header_existing(self):
        """
        """
        header_templ = "GNU tar-1.20-2\n1232387353\x00128841398\x00"

        snpf = SnapshotFile(self.snarfile)
        header = snpf.getHeader()
        self.assertEqual(header_templ, header)

    def test_get_formatversion_existing(self):
        """
        """
        version_templ = int(2)

        snpf = SnapshotFile(self.snarfile)
        version = snpf.getFormatVersion()
        self.assertEqual(version_templ, version)

    def test_parse_format2(self):
        """Parse existing SNAR-file and checks its content
        
        @todo: Check what exactly happens to the leading slashes!
        """
        dumpdir1_name = "/home/peer/backups/testdocs/docs"
        dumpdir1 = ["N case_Wellcome.pdf",
                    "N fables_01_01_aesop.spx",
                    "Y new file",
                    "N new file.bak",
                    "Y new file~",
                    "D new folder",
                    "N oo-derivatives.doc",
                    "Y oo-trig.xls"
                    ]

        dumpdir2_name = "/home/peer/backups/testdocs/docs/new folder"
        dumpdir2 = ["Y here is another new file",
                    "Y here is another new file~",
                    "Y oo-maxwell.odt",
                    "Y oo-payment-schedule.ods"
                    ]

        dir_file = []
        snpf = SnapshotFile(self.snarfile)
        for entr in snpf.parseFormat2():
            dir_file.append(entr)
        self.assertTrue(len(dir_file) == 2)

        entry1 = dir_file[0]
        entry2 = dir_file[1]

        print "ENTRY:\n%s" % entry2

        # evaluate the results
        self.assertEqual(dumpdir1_name, entry1[SnapshotFile.REC_DIRNAME])
        self.assertEqual(dumpdir2_name, entry2[SnapshotFile.REC_DIRNAME])

        self.assertEqual(len(dumpdir1), len(entry1[SnapshotFile.REC_CONTENT]))
        self.assertEqual(len(dumpdir2), len(entry2[SnapshotFile.REC_CONTENT]))

        dmpd_lst = entry1[SnapshotFile.REC_CONTENT]
        self.assertTrue(isinstance(dmpd_lst, list))

        for _idx in range(0, len(dumpdir1)):
            dmpd = dmpd_lst[_idx]
            self.assertTrue(isinstance(dmpd, Dumpdir))
            dmpd_str = "%s %s" % (dmpd.getControl(), dmpd.getFilename())
            self.assertEqual(dmpd_str, dumpdir1[_idx])

        dmpd_lst = entry2[SnapshotFile.REC_CONTENT]
        self.assertTrue(isinstance(dmpd_lst, list))

        for _idx in range(0, len(dumpdir2)):
            dmpd = dmpd_lst[_idx]
            self.assertTrue(isinstance(dmpd, Dumpdir))
            dmpd_str = "%s %s" % (dmpd.getControl(), dmpd.getFilename())
            self.assertEqual(dmpd_str, dumpdir2[_idx])


    def test_header_newfile(self):
        """Test methods related to header on fresh created file.
        """
        header_templ = "GNU tar-1.19-2\n1169216967\x001169216967\x00"
        version_templ = int(2)
        datet = datetime.datetime(2007, 1, 19, 15, 29, 27)

        snpf = SnapshotFile(self.snarf_new, writeFlag = True)
        snpf.setHeader(datet)

        header = snpf.getHeader()
        self.assertEqual(header_templ, header)
        version = snpf.getFormatVersion()
        self.assertEqual(version_templ, version)

    def test_createcontent(self):
        _dumpdirs = [ Dumpdir("Yhere is another new file\0"),
                      Dumpdir("Yhere is another new file~\0"),
                      Dumpdir("Yoo-maxwell.odt\0"),
                      Dumpdir("Yoo-payment-schedule.ods\0")
                    ]
        snpf = SnapshotFile(self.snarf_new, writeFlag = True)
        _res = snpf.createContent(_dumpdirs)
        print "CONTENT: '%s'" % (_res)

    def test_addrecord(self):
        dumpdir1_name = "/home/peer/backups/testdocs/docs/new folder"
        dumpdir1 = ["Y here is another new file",
                    "Y here is another new file~",
                    "Y oo-maxwell.odt",
                    "Y oo-payment-schedule.ods"
                    ]

        _dumpdirs = [ Dumpdir("Yhere is another new file\0"),
                      Dumpdir("Yhere is another new file~"),
                      Dumpdir("Yoo-maxwell.odt"),
                      Dumpdir("Yoo-payment-schedule.ods")
                    ]

        _rec = ['0', '1232387286', '0', '2055', '90478',
                '/home/peer/backups/testdocs/docs/new folder',
                _dumpdirs
               ]

        datet = datetime.datetime(2007, 1, 19, 15, 29, 27)

        snpf = SnapshotFile(self.snarf_new, writeFlag = True)
        snpf.setHeader(datet)
        snpf.addRecord(_rec)

        del snpf
        # now re-read the created SNAR-file
#        print "\n\n\nnow re-read the created SNAR-file"

        dir_file = []
        snpf = SnapshotFile(self.snarf_new)
        for entr in snpf.parseFormat2():
            dir_file.append(entr)
        self.assertTrue(len(dir_file) == 1)

        entry1 = dir_file[0]

#        print "ENTRY after addrecord:\n%s" % entry1

        # evaluate the results
        self.assertEqual(dumpdir1_name, entry1[SnapshotFile.REC_DIRNAME])
        self.assertEqual(len(dumpdir1), len(entry1[SnapshotFile.REC_CONTENT]))

        dmpd_lst = entry1[SnapshotFile.REC_CONTENT]
        self.assertTrue(isinstance(dmpd_lst, list))

        for _idx in range(0, len(dumpdir1)):
            dmpd = dmpd_lst[_idx]
            self.assertTrue(isinstance(dmpd, Dumpdir))
            dmpd_str = "%s %s" % (dmpd.getControl(), dmpd.getFilename())
            self.assertEqual(dmpd_str, dumpdir1[_idx])


class TestProcSnapshotFile(unittest.TestCase):
    """
    
    @todo: Shared code for test preparing must be put in PATH class!
    """

    def setUp(self):
        """This method is called before processing of each test.
        
        @todo: Modify setting of file paths!
        """
        self.snarfile = _TestTarPaths.get_path("test-snapshotfile.snar")
        self.snarsnpfile_path = _TestTarPaths.get_path("files.snar")
        self.snarsnpfile2_path = _TestTarPaths.get_path("files-2.snar")

        self.__clean_dir()
        self.__copy_template()

        # existing snarfiles
        self.snarSNPfile = SnapshotFile(self.snarsnpfile_path)
        self.snarSNPfile2 = SnapshotFile(self.snarsnpfile2_path)

    def tearDown(self):
        """This method is called after processing of each test.
        """
        self.__clean_dir()

    def __clean_dir(self):
        """Private helper method that removes eventually created test data
        from the test-data directory to keep it clean.
        """
        rmlst = [ self.snarsnpfile_path, self.snarsnpfile2_path
                ]
        for rm in rmlst:
            if os.path.exists(rm):
                os.remove(rm)

    def __get_templates(self):
        _rel_dir = "templates"
        _templates = [ "files.snar.template",
                       "files-2.snar.template"
                     ]
        _res = []
        for _templ in _templates:
            _path_templ = _TestTarPaths.get_path(os.path.join(_rel_dir, _templ))
            _path_target = _TestTarPaths.get_path(_templ.rstrip(".template"))
            _res.append({"template": _path_templ, "target": _path_target})
        return _res

    def __copy_template(self):
        """Private helper method that copies the template snarfile
        into the destination snarfile. This is done to avoid unwanted
        modifications of the snarfile for further tests.
        """
        _templates = self.__get_templates()
        print "TEMPLATES: %s" % _templates
        for _templ in _templates:
            rmcmd = ["cp", "-f", _templ["template"], _templ["target"]]
            subprocess.call(rmcmd)

    def testProcSnapshotFile(self):
        " Create and read a ProcSnapshotFile "
        psnpf = ProcSnapshotFile(self.snarSNPfile)
        for i in psnpf.getContent("/home/wattazoum/Images/camescope/2007-04-08--09.09.05") :
            print str(i)
        print psnpf

        psnpf = ProcSnapshotFile(self.snarSNPfile2)
        self.assertRaises(SBException, psnpf.getContent, "/home/wattazoum/Images/camescope/2007-04-08--09.09.05")
        for i in psnpf.getContent("/home/wattazoum/Images") :
            print str(i)
        print psnpf


class TestTarUtilsArchiveType(unittest.TestCase) :
    """Test case for function 'getArchiveType' defined in module 'tar'.
    """

    LogFactory.getLogger(level = 10)

    def test_get_archive_type(self):
        """Test determination of archive types using mime types
        """
        rel_dir = "archivetype"

        input_data = [{ "file" : "test-tar.tar", "type" : "tar" },
                      { "file" : "test-tar.tar.gz", "type" : "gzip" },
                      { "file" : "test-tar.tar.bz2", "type" : "bzip2" },
                      { "file" : "test-tar.archive", "type" : "tar" },
                      { "file" : "test-tar.tar.zip", "type" : "gzip" },
                      { "file" : "test-tar.archive.lzma", "type" : "bzip2" },
                      { "file" : "test-tar.fake.tar", "type" : None },
                      { "file" : "test-tar.fake.tar.gz", "type" : None },
                      { "file" : "test-tar.fake.tar.bz2", "type" : None }
                     ]
        for _data in input_data:
            _res = getArchiveType(_TestTarPaths.get_path(rel_dir +
                                                         os.path.sep +
                                                         _data["file"]))
            self.assertEqual(_res, _data["type"])


class TestTarUtilsGetDumpdir(unittest.TestCase) :
    """Test case for function 'get_dumpdir_from_list' defined in module 'tar'.
    """

    LogFactory.getLogger(level = 10)

    def test_getdumpdirfromlist_nolist(self):
        """Get dumpdir from list with invalid list parameter
        """
        input_data = [ ("test", "test"),
                       {"test" : "test"},
                       "test",
                       1200
                     ]
        for _data in input_data:
            self.assertRaises(TypeError, get_dumpdir_from_list, _data, "test")

    def test_getdumpdirfromlist_nodumpdir(self):
        """Get dumpdir from list with invalid elements in list
        """
        input_data = [ ["test", "test"],
                       [{"test" : "test"}],
                       ["test"],
                       [1200]
                     ]
        for _data in input_data:
            self.assertRaises(TypeError, get_dumpdir_from_list, _data, "test")

    def test_getdumpdirfromlist_notfound(self):
        """Get dumpdir from list but filename not found
        """
        input_data = [ [ Dumpdir("Ytestname"), Dumpdir("Nsome file"),
                         Dumpdir("NSome File"), Dumpdir("Ytestname~") ]
                     ]
        for _data in input_data:
            self.assertRaises(SBException, get_dumpdir_from_list, _data, "test")

    def test_get_dumpdir_from_list(self):
        """Test get dumpdir from list with valid parameters
        """
        input_data = [ { "list" : [ Dumpdir("Ytestname"),
                                    Dumpdir("Nsome file"),
                                    Dumpdir("NSome File"),
                                    Dumpdir("Ytestname~") ],
                         "name" : "testname",
                         "result" : 0
                       },
                       { "list" : [ Dumpdir("Ytestname"),
                                    Dumpdir("Nsome file"),
                                    Dumpdir("NSome File"),
                                    Dumpdir("Ytestname~") ],
                         "name" : "some file",
                         "result" : 1
                       },
                       { "list" : [ Dumpdir("Ytestname"),
                                    Dumpdir("Nsome file"),
                                    Dumpdir("NSome File"),
                                    Dumpdir("Ytestname~") ],
                         "name" : "Some File",
                         "result" : 2
                       },
                       { "list" : [ Dumpdir("Ytestname"),
                                    Dumpdir("Nsome file"),
                                    Dumpdir("NSome File"),
                                    Dumpdir("Ytestname~") ],
                         "name" : "testname~",
                         "result" : 3
                       }
                     ]
        for _data in input_data:
            _res = get_dumpdir_from_list(_data["list"], _data["name"])
            self.assertTrue(_res is _data["list"][_data["result"]])


class TestTarUtilsAppendTar(unittest.TestCase) :
    """Test case for functions 'appendToTar..' defined in module 'tar'.
    """

    LogFactory.getLogger(level = 10)

    def test_append_to_tar(self):
#        rel_dir = "archivetype"
#        
#        input_data = [{ "file" : "test-tar.tar", "type" : "tar" },
#                      { "file" : "test-tar.tar.gz", "type" : "gzip" },
#                      { "file" : "test-tar.tar.bz2", "type" : "bzip2" },
#                      { "file" : "test-tar.archive", "type" : "tar" },
#                      { "file" : "test-tar.tar.zip", "type" : "gzip" },
#                      { "file" : "test-tar.archive.lzma", "type" : "bzip2" },
#                      { "file" : "test-tar.fake.tar", "type" : None },
#                      { "file" : "test-tar.fake.tar.gz", "type" : None },
#                      { "file" : "test-tar.fake.tar.bz2", "type" : None } 
#                     ]
#        for _data in input_data:
#            _res = getArchiveType(_TestTarPaths.get_path(rel_dir +
#                                                         os.path.sep +
#                                                         _data["file"]))

        raise NotImplementedError


def suite():
    """Returns a test suite containing all test cases from this module.
    """
    _suite = unittest.TestSuite()
    _suite.addTests(
        [ unittest.TestLoader().loadTestsFromTestCase(TestDumpdir),
          unittest.TestLoader().loadTestsFromTestCase(TestProcSnapshotFile),
          unittest.TestLoader().loadTestsFromTestCase(TestSnapshotFile),
          unittest.TestLoader().loadTestsFromTestCase(TestTarUtilsArchiveType),
          unittest.TestLoader().loadTestsFromTestCase(TestTarUtilsGetDumpdir),
          unittest.TestLoader().loadTestsFromTestCase(TestTarUtilsAppendTar)

           ])
    return _suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity = 2).run(suite())
