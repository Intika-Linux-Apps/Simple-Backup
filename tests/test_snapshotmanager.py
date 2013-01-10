# -*- coding: latin-1 -*-

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
#   Jean-Peer Lorenz <peer.loz@gmx.net>

"""Module privides unittest for testing of classes/methods related to
snapshot managing.

Required tests related to snapshot managing:

1. General instantiation
2. Read operations from disk (loading of snapshots...) 
3. Re-basing of both incremental and full snapshots
4. Removal of incremental and full snapshots, with and without
   dependencies
...

"""

import os
import subprocess
import unittest

from sbackup.managers.SnapshotManager import SnapshotManager
from sbackup.managers.SnapshotManager import debug_print_snarfile
from sbackup.managers.SnapshotManager import debug_snarfile_to_list

from sbackup import util
from sbackup.util.log import LogFactory
from sbackup.util.exceptions import SBException


LOGLEVEL = 100

TESTDATA_PREFIX = os.path.abspath("./test-datas/test-snapshotmanager/")


class _TestSnapshotManagerPathsBase(object):
    """Base class with the only purpose to provide pathnames to
    input/output test data from a single place to avoid multiple
    definitions of them.
    
    Each test case derives a class from this one and overwrites the
    according paths.
    """
    _relpath_prefix = ""

    # relative paths to test input, working directory and (targeted) results
    _relpath_input = ""
    _relpath_wd = ""
    _relpath_results = ""

    # file names for certain test case
    _reltar_input = ""
    _reltar_results = ""
    _result_snar = ""

    @classmethod
    def _check_relpath_prefix(cls):
        """
        """
        if cls._relpath_prefix == "":
            raise ValueError("Relative path prefix for current test case is not defined.")

    @classmethod
    def get_path_input_dir(cls):
        """Returns the absolute path to input data.
        """
        cls._check_relpath_prefix()
        if cls._relpath_input == "":
            raise ValueError("Path to input data directory is not defined.")
        _path = os.path.join(TESTDATA_PREFIX,
                             cls._relpath_prefix,
                             cls._relpath_input)
        return _path

    @classmethod
    def get_path_working_dir(cls):
        """Returns the absolute path to the existing snapshots to be tested.
        """
        cls._check_relpath_prefix()
        if cls._relpath_wd == "":
            raise ValueError("Path to working directory is not defined.")
        _path = os.path.join(TESTDATA_PREFIX,
                             cls._relpath_prefix,
                             cls._relpath_wd)
        return _path

    @classmethod
    def get_path_result_dir(cls):
        """Returns the absolute path to the (targeted) results.
        """
        cls._check_relpath_prefix()
        if cls._relpath_results == "":
            raise ValueError("Path to reference results directory is not defined.")
        _path = os.path.join(TESTDATA_PREFIX,
                             cls._relpath_prefix,
                             cls._relpath_results)
        return _path

    @classmethod
    def get_path_input_tar(cls):
        """Returns the absolute path to the tar-archive containing the
        snapshots to be tested.
        """
        if cls._reltar_input == "":
            raise ValueError("Archive containing input data is not defined.")
        _path = os.path.join(cls.get_path_input_dir(), cls._reltar_input)
        return _path

    @classmethod
    def get_path_result_tar(cls):
        """Returns the absolute path to the tar-archive containing the results.
        """
        if cls._reltar_results == "":
            raise ValueError("Archive containing reference results is not defined.")
        _path = os.path.join(cls.get_path_input_dir(), cls._reltar_results)
        return _path

    @classmethod
    def has_result_tar(cls):
        """Checks whether the path to the tar-archive containing the results
        is set.
        """
        _res = True
        if cls._reltar_results == "":
            _res = False
        return _res

    @classmethod
    def has_result_snar(cls):
        """Checks whether the name of the result snar file is defined.
        """
        _res = True
        if cls._result_snar == "":
            _res = False
        return _res

    @classmethod
    def get_res_snar_input(cls):
        """
        """
        if cls._result_snar == "":
            raise ValueError("Reference snar file is not defined.")
        _path = os.path.join(cls.get_path_input_dir(), cls._result_snar)
        return _path

    @classmethod
    def get_res_snar(cls):
        """
        """
        if cls._result_snar == "":
            raise ValueError("Name of snar file is not defined.")
        _path = os.path.join(cls.get_path_result_dir(), cls._result_snar)
        return _path


class _TestSnapshotManagerPaths(_TestSnapshotManagerPathsBase):
    """Path definitions for general tests.
    """
    _relpath_prefix = "manager"
    # relative paths to test input, working directory and (targeted) results
    _relpath_input = "input"
    _relpath_wd = "working-dir"
    _relpath_results = "reference-results"

    # file names for certain test case
    _reltar_input = "state3.inc.tar.lzma"
    _reltar_results = ""
    _result_snar = ""


class _TestSnapshotRemoveV1Paths(_TestSnapshotManagerPathsBase):
    """Path definitions for test related to removal of snapshots.
    Version 1 (V1) uses 4 snapshots (3 incr., 1 full) with real
    life data.
    
    @attention: The snapshots are apparently broken, so not all
                of the tests can be applied.
    
    @todo: Create a new real life scenario that fulfills following
           requirements:
           1. several types of files including *~ and *.bak
           2. some read-only files and directories
           3. complex ownership (user and groups)
           4. soft and hard links are present in the files to archive
           5. special characters (spaces, newlines, ü, á etc.)
           6. unicode coded filenames (japanese...)
           7. excluded files
           8. (apply these requirements to files and directories)
           9. more than 1 full snapshot
           
    """
    _relpath_prefix = "manager"
    # relative paths to test input, working directory and (targeted) results
    _relpath_input = "input"
    _relpath_wd = "working-dir"
    _relpath_results = "reference-results"

    # file names for certain test case
    _reltar_input = "state4.inc.v1.tar.lzma"
    _reltar_results = ""
    _result_snar = ""


class _TestSnapshotRemoveV2Paths(_TestSnapshotManagerPathsBase):
    """Path definitions for test related to removal of snapshots.
    Version 2 (V2) uses 3 snapshots (2 incr., 1 full) with generic
    data.
    """
    _relpath_prefix = "manager"
    # relative paths to test input, working directory and (targeted) results
    _relpath_input = "input"
    _relpath_wd = "working-dir"
    _relpath_results = "reference-results"

    # file names for certain test case
    _reltar_input = "state3.inc.tar.lzma"
    _reltar_results = ""
    _result_snar = ""

# end of path definition


class TestSnapshotManager(unittest.TestCase):
    """Test case for testing basic functionality of the
    class 'SnapshotManager'. This test case covers tests that
    neither read from disk nor write to it. 
    """
    _path_class = _TestSnapshotManagerPaths

    def setUp(self):
        """Set-up the test to be run.
        """
        LogFactory.getLogger(level = LOGLEVEL)

    def test_instantiation_fails(self):
        """Test instantiation of SnapshotManager with invalid parameter
        """
        tdir = None
        self.assertRaises(SBException, SnapshotManager, tdir)

        tdir = "/hopefully/thispath/doesnot/exist"
        self.assertRaises(SBException, SnapshotManager, tdir)

    def test_instantiation_fails_missing_param(self):
        """Test instantiation of SnapshotManager with missing parameter
        """
        self.assertRaises(TypeError, SnapshotManager)

    def test_instantiation(self):
        """Test instantiation of SnapshotManager with valid parameter
        """
        tdir = self._path_class.get_path_input_dir()
        SnapshotManager(tdir)


class _TestSnapshotManagerBase(unittest.TestCase):
    """Base class for test cases using the snapshot manager. The class
    provides the unpacking of input data and reference results.
    Beside common preparation code, this class provides methods for
    result comparison. Use these in your own defined test methods.
    
    Input data for the test cases are stored in directory 'input'. It is
    extracted into the 'working-dir' where the tests are proceeded. Reference
    values (the targeted results) are extracted into the according directory
    'reference-results' and then compared with the results from the tests.
    
    It is supposed that:
    1. paths are stored in a class derived from `_TestSnapshotMergePaths`
    2. all working copies are packed in a single archive compressed with
       tar --lzma. Same holds for reference results.
    3. Reference values for the resulting snar file are provided in a separate
       file.    
    """
    _path_class = None

    def setUp(self):
        """Common setup method: creates required directories, extracts the
        test data and retrieves the names of input and result snapshots.
        """
        LogFactory.getLogger(level = LOGLEVEL)

        # sorting order is important!    
        self.snpname = []
        self.res_snpname = []
        self.snppath = []
        self.res_snppath = []

        self._clean_dirs()
        self._make_dirs()
        self._untar()
        self._setup_snppaths()
        self._copy_result_snar()

        # create SnapshotManager
        self.snpman = SnapshotManager(self._path_class.get_path_working_dir())

    def tearDown(self):
        self._clean_dirs()

    def _setup_workingdir_paths(self):
        """Retrieves names of existing snapshots in the working directory.
        In order to reduce maintenance effort this is done automatically.
        
        :attention: The retrieval is done in a brute and dumb way! Take
                    care what files/directories are present in the working
                    directory when calling this method.
                    
        :result: The object variable `snpname` and `snppath` are updated.  
        """
        self.snpname = []
        self.snppath = []
        _dir = self._path_class.get_path_working_dir()
        listing = os.listdir(_dir)
        listing.sort(reverse = True)
        for name in listing:
            self.snpname.append(name)
            self.snppath.append(os.path.join(_dir, name))
        # debug output
        if LogFactory.getLogger().isEnabledFor(10):
            print "Paths to snapshots to proceed:"
            for _path in self.snppath:
                print "   %s" % _path
        # end of debug output

    def _setup_resultdir_paths(self):
        """Retrieves names of existing snapshots in the result directory.
        In order to reduce maintenance effort this is done automatically.
        
        :attention: The retrieval is done in a brute and dumb way! Take
                    care what files/directories are present in the working
                    directory when calling this method.
                    
        :result: The object variable `res_snpname` and `res_snppath` are
                 updated.  
        """
        self.res_snpname = []
        self.res_snppath = []
        _dir = self._path_class.get_path_result_dir()
        listing = os.listdir(_dir)
        listing.sort(reverse = True)
        for name in listing:
            self.res_snpname.append(name)
            self.res_snppath.append(os.path.join(_dir, name))
        # debug output
        if LogFactory.getLogger().isEnabledFor(10):
            print "Paths to result snapshots (targeted):"
            for _path in self.res_snppath:
                print "   %s" % _path
        # end of debug output

    def _setup_snppaths(self):
        """Retrieves names of existing snapshots in both working directory
        and results directory.
        """
        self._setup_workingdir_paths()
        self._setup_resultdir_paths()

    def _make_dirs(self):
        os.makedirs(self._path_class.get_path_working_dir())
        os.makedirs(self._path_class.get_path_result_dir())

    def _clean_dirs(self):
        _dirs = [ self._path_class.get_path_working_dir(),
                  self._path_class.get_path_result_dir()
                ]
        for _dir in _dirs:
            rmcmd = ["rm", "-rf", _dir]
            subprocess.call(rmcmd)

    def _untar(self):
        """Extracts the archives defined in the according class `paths`.
        """
        LogFactory.getLogger().info("\nPrepare test: now un-tar input")
        tarcmd = ['tar', '--extract', '--lzma',
                  '--directory=%s' % self._path_class.get_path_working_dir(),
                  '--file=%s' % self._path_class.get_path_input_tar()]
        LogFactory.getLogger().debug("  tar command: %s" % tarcmd)
        subprocess.call(tarcmd)

        LogFactory.getLogger().info("Prepare test: now un-tar results")
        if self._path_class.has_result_tar():
            tarcmd = ['tar', '--extract', '--lzma',
                      '--directory=%s' % self._path_class.get_path_result_dir(),
                      '--file=%s' % self._path_class.get_path_result_tar()]
            LogFactory.getLogger().debug("  tar command: %s" % tarcmd)
            subprocess.call(tarcmd)
        else:
            LogFactory.getLogger().info("No results defined")

    def _copy_result_snar(self):
        """Copies the snar file containing target values from the input
        directory to the results directory.
        """
        if self._path_class.has_result_snar():
            cpcmd = ["cp", "-f", self._path_class.get_res_snar_input(),
                    self._path_class.get_path_result_dir()]
            subprocess.call(cpcmd)

    def _compare_snar_files(self, snapshot, snarfile):
        """Compares the snar file of the given `snapshot` and the given
        (result) `snarfile`.
        
        The header of the snar files (i.e. the tar version, time of backup)
        is not compared. Any following records (mtime, inode, filenames) are
        compared and must be identical to pass the comparison.        
        """
        # only for debugging
        if LogFactory.getLogger().isEnabledFor(10):
            debug_print_snarfile(snapshot.getSnarFile())
            debug_print_snarfile(snarfile)
        # end of debug output

        _snar1 = debug_snarfile_to_list(snapshot.getSnarFile())
        _snar2 = debug_snarfile_to_list(snarfile)

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

    def _compare_tar_archives(self, snapshot_path, result_path):
        """Compares the content of the `files.tar.gz` archive that are
        stored in the given locations (`snapshot_path` and `result_path`).
        
        The archives are not extracted. The content of the archives using
        the tar option `--list` is compared. The content must be completely
        identical (same file owners, same dates, same files) to pass
        the comparison.
        """
        wd_tar = os.path.join(snapshot_path, "files.tar.gz")
        cmd = "tar"
        opts = ["--list",
                "--verbose",
                "--file=%s" % wd_tar]
        stdo_wd, stde_wd, exc_wd = util.launch(cmd = cmd, opts = opts)

        res_tar = os.path.join(result_path, "files.tar.gz")
        cmd = "tar"
        opts = ["--list",
                "--verbose",
                "--file=%s" % res_tar]
        stdo_res, stde_res, exc_res = util.launch(cmd = cmd, opts = opts)

        self.assertEqual(exc_wd, 0)
        self.assertEqual(exc_res, 0)

        stdo_wd = stdo_wd.split("\n")
        stdo_res = stdo_res.split("\n")

        stdo_wd.sort()
        stdo_res.sort()

        stdo_wd = "\n".join(stdo_wd)
        stdo_res = "\n".join(stdo_res)

        # only for debugging
        if LogFactory.getLogger().isEnabledFor(10):
            print "\nworking dir:"; print stdo_wd
            print "\ntarget result:"; print stdo_res
        # end of debug output

        self.assertEqual(stdo_wd, stdo_res)


class TestSnapshotManagerFromDisk(_TestSnapshotManagerBase):
    """Test case for testing 'read-only' functionality of the
    class 'SnapshotManager'. This test case covers tests that
    read from disk but do not write to the disk. 
    """
    _path_class = _TestSnapshotManagerPaths

    def test_get_snapshots_all(self):
        """Getting list of snapshots in the target directory. Force reload
        
        It is checked against number of returned values and the names
        of the snapshots. Additional for full snapshots it is checked whether
        the stored base is correct.
        """
        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)

        self.assertEqual(len(snp_list), len(self.snpname))
        for _idx in range(0, len(snp_list)):
            _snp = snp_list[_idx]
            self.assertEqual(_snp.getName(), self.snpname[_idx])

    def test_base_of_get_snapshots_all(self):
        """Getting list of snapshots and check the base of incremental ones

        For incr. snapshots it is checked whether the stored base is correct.
        """
        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)

        for _idx in range(0, len(snp_list)):
            _snp = snp_list[_idx]
            self.assertEqual(_snp.getName(), self.snpname[_idx])
            if not _snp.isfull():
                _base = _snp.getBase()
                if (_idx + 1) < len(self.snpname):
                    self.assertEqual(_base, self.snpname[_idx + 1])

#    def test_get_snapshots_by_timespan(self):
#        raise NotImplementedError
#    
#    def test_get_snapshots_by_date(self):
#        raise NotImplementedError
#
#    def test_get_snp_history(self):
#        raise NotImplementedError



class _TestSnapshotRemoveBase(_TestSnapshotManagerBase):
    """Base class for test cases related to removal and purging
    of snapshots.
    """
    _path_class = None

    def _remove_incr_snapshot(self, idx_to_remove):
        """Remove  given incremental snapshot.
        """
        # list of resulting names, latest incr. snapshot is removed.
        res_snpname = self.snpname
        del res_snpname[idx_to_remove]

        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[idx_to_remove]

        self.assertFalse(snp.isfull())

        self.snpman.removeSnapshot(snapshot = snp)

        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        self.assertEqual(len(snp_list), len(res_snpname))
        for _idx in range(0, len(snp_list)):
            _snp = snp_list[_idx]
            self.assertEqual(_snp.getName(), res_snpname[_idx])

            if not _snp.isfull():
                _base = _snp.getBase()
                if (_idx + 1) < len(res_snpname):
                    self.assertEqual(_base, res_snpname[_idx + 1])


class TestSnapshotRemoveV1(_TestSnapshotRemoveBase):
    """Test case for testing the removal of snapshots (version 1).

    @note: The test `test_remove_full_snapshot` does currently
           not work due to a corrupt snapshot. See comments above.
    """
    _path_class = _TestSnapshotRemoveV1Paths

#    def test_remove_full_snapshot(self):
#        """
#        """
#        snp_list = self.snpman.get_snapshots_allformats(forceReload=True)
#        snp = snp_list[3]
#        snp_child = snp_list[2]
#        
#        self.assertTrue(snp.isfull())
#        self.assertEqual(snp_child.getBase(), snp.getName())
#        self.assertNotEqual(snp_list[1].getBase(), snp.getName())
#        self.assertNotEqual(snp_list[0].getBase(), snp.getName())
#        
#        # only for debugging
#        if LogFactory.getLogger().isEnabledFor(10):
#            LogFactory.logger.debug("Snapshot file parent:")
#            debug_print_snarfile(snp.getSnarFile())
#            LogFactory.logger.debug("Snapshot file child:")
#            debug_print_snarfile(snp_child.getSnarFile())
#        # end of debug output
#
#        _snar1 = debug_snarfile_to_list(snp.getSnarFile())
#        _snar2 = debug_snarfile_to_list(snp_child.getSnarFile())
#        
#        
##        self.snpman.removeSnapshot(snapshot=snp)

    def test_remove_latest_incr_snapshot(self):
        """Remove latest (i.e. most recent) incremental snapshot
        which is not the base of other snapshots.
        """
        self._remove_incr_snapshot(idx_to_remove = 0)

    def test_remove_2ndlatest_incr_snapshot(self):
        """Remove incr. snapshot which is the base of other incr. snapshot
        """
        self._remove_incr_snapshot(idx_to_remove = 1)

    def test_remove_3rdlatest_incr_snapshot(self):
        """Remove incr. snapshot which is the base of other incr. snapshot
        """
        self._remove_incr_snapshot(idx_to_remove = 2)

    def test_remove_2_snapshots(self):
        """Removes two incremental snapshots in a sequence.
        """
        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[1]
        self.assertFalse(snp.isfull())
        self.snpman.removeSnapshot(snapshot = snp)

        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[1]
        self.assertFalse(snp.isfull())
        self.snpman.removeSnapshot(snapshot = snp)


class TestSnapshotRemoveV2(_TestSnapshotRemoveBase):
    """Test case for testing the removal of snapshots (version 2).
    """
    _path_class = _TestSnapshotRemoveV2Paths

    def test_remove_full_snapshot(self):
        """
        """
        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[2]

        self.assertTrue(snp.isfull())

        self.snpman.removeSnapshot(snapshot = snp)

    def test_remove_latest_incr_snapshot(self):
        """Remove latest incr. snapshot which is not base of other snapshots
        """
        self._remove_incr_snapshot(idx_to_remove = 0)

    def test_remove_2ndlatest_incr_snapshot(self):
        """Remove incr. snapshot which is the base of other incr. snapshot
        """
        self._remove_incr_snapshot(idx_to_remove = 1)

    def test_remove_2_snapshots(self):
        """
        """
        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[1]
        self.assertFalse(snp.isfull())
        self.snpman.removeSnapshot(snapshot = snp)

        snp_list = self.snpman.get_snapshots_allformats(forceReload = True)
        snp = snp_list[1]
        self.assertTrue(snp.isfull())
        self.snpman.removeSnapshot(snapshot = snp)


def suite():
    """Returns a test suite containing all test cases from this module.
    """
    _loader = unittest.TestLoader().loadTestsFromTestCase
    _suite = unittest.TestSuite()
    _suite.addTests(
        [
         _loader(TestSnapshotManager),
         _loader(TestSnapshotManagerFromDisk),
         _loader(TestSnapshotRemoveV1),
         _loader(TestSnapshotRemoveV2)
        ])
    return _suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity = 2).run(suite())
