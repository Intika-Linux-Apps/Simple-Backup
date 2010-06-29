#! /usr/bin/python
#
#    NSsbackup - helper script for automated creation of test data
#
#   Copyright (c)2008-2009: Jean-Peer Lorenz <peer.loz@gmx.net>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""
:mod:`test_createdata` --- automated creation of test data
===========================================================

.. module:: test_createdata
   :synopsis: helper script for automated creation of test data
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

import random
import sys
import os
import os.path
import subprocess

random.seed()


class TestdataOptions(object):

    def __init__(self, mode):
        self.__wdir = "./nssbackup-test-py"
        self.__mode = mode
        #mode = "medium"
        #mode = "large"

        self.__min_depth = 1
        self.__max_depth = 3
        self.__min_dir = 1
        self.__max_dir = 3
        self.__min_file = 2
        self.__max_file = 10
        self.__min_length = 10
        self.__max_length = 1000


#    if mode == "small":
#        min_depth = 1
#        max_depth = 3
#        min_dir = 1
#        max_dir = 3
#        min_file = 2
#        max_file = 10
#        min_length = 10
#        max_length = 1000
#    elif mode == "medium":
#        min_depth = 2
#        max_depth = 4
#        min_dir = 2
#        max_dir = 4
#        min_file = 4
#        max_file = 7
#        min_length = 10
#        max_length = 10000
#    elif mode == "large":
#        min_depth = 2
#        max_depth = 4
#        min_dir = 2
#        max_dir = 4
#        min_file = 5
#        max_file = 10
#        min_length = 100
#        max_length = 100000

    def get_working_dir(self):
        return self.__wdir

    def get_min_depth(self):
        return self.__min_depth

    def get_max_depth(self):
        return self.__max_depth

    def get_min_contentlength(self):
        return self.__min_length

    def get_max_contentlength(self):
        return self.__max_length

    def get_min_number_of_files(self):
        return self.__min_file

    def get_max_number_of_files(self):
        return self.__max_file

    def get_min_number_of_dirs(self):
        return self.__min_dir

    def get_max_number_of_dirs(self):
        return self.__max_dir


class TestdataCreator(object):

    def __init__(self, creatoroptions):
        self.__options = creatoroptions
        self.list_of_files = []
        self.cum_dirs = 0
        self.cum_files = 0

    def generate_content(self):
        length = random.randint(self.__options.get_min_contentlength(),
                                self.__options.get_max_contentlength())
        txt = ""
        cchar = 0
        while cchar < length:
            char = chr(random.randint(0, 255))
            txt = "%s%s" % (txt, char)
            cchar += 1
        return txt

    def make_files(self, args, dirname, filenames):
        print "MAKE_FILES - args: %s; dirname: %s" % (args, dirname)
        maxfilenum = random.randint(self.__options.get_min_number_of_files(),
                                    self.__options.get_max_number_of_files())
        for cnum in range(0, maxfilenum):
            fname = os.path.join(dirname, "f%s" % cnum)
    #        print "create '%s'" % fname
            fobj = file(fname, "wb")
            fobj.write(self.generate_content())
            fobj.close()
            self.cum_files += 1

    def make_dirs(self):
        mdepth = random.randint(self.__options.get_min_depth(),
                                self.__options.get_max_depth())
        self.make_dirs_recurs(self.__options.get_working_dir(), 0, mdepth)

    def make_dirs_recurs(self, curpath, curdepth, maxdepth):
    #    print "MAKE_DIRS: curpath: %s; curdepth: %s; maxdepth: %s" % (curpath, curdepth, maxdepth)
        maxdirnum = random.randint(self.__options.get_min_number_of_dirs(),
                                   self.__options.get_max_number_of_dirs())
        for cdirnum in range(0, maxdirnum):
            createdpath = os.path.join(curpath, "d%s" % cdirnum)
            os.mkdir(createdpath)
            self.cum_dirs += 1
            if curdepth < maxdepth:
                self.make_dirs_recurs(createdpath, curdepth + 1, maxdepth)

    def make_files_in_dirs(self):
        os.path.walk(self.__options.get_working_dir(), self.make_files, None)


def calc_sums(arg, dirname, filenames):
    for fname in filenames:
#        print fname
        fpath = os.path.join(dirname, fname)
        cmd = ["md5sum", fpath]
        output = subprocess.Popen(cmd, stdout = subprocess.PIPE).communicate()[0]
        print output
        cmd = ["cksum", fpath]
        output = subprocess.Popen(cmd, stdout = subprocess.PIPE).communicate()[0]
        print output


def main():
    options = TestdataOptions(mode = "small")
    creator = TestdataCreator(creatoroptions = options)

    wdir = options.get_working_dir()
    if os.path.exists(wdir):
        print "Target directory '%s' already exists!" % wdir
        sys.exit(1)
    else:
        os.mkdir(wdir)

    creator.make_dirs()
    creator.make_files_in_dirs()

    print "created: %s files in %s directories" % (creator.cum_files,
                                                   creator.cum_dirs)
#    os.path.walk(wdir, calc_sums, None)


if __name__ == "__main__":
    main()
