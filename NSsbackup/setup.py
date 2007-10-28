#!/usr/bin/env python

import os
from setuptools import setup, find_packages

def datas(path):
	"""
	prepends datas to the path
	"""
	return 'datas'+os.sep+path

def src(path):
	"""
	prepends src to the path
	"""
	return 'src'+os.sep+path

setup(name="NSsbackup",
      version="0.2dev",
      description="Not So Simple Backup Suit",
      author="Oumar Aziz OUATTARA",
      author_email="wattazoum@gmail.com",
      url="https://launchpad.net/nssbackup/",
      packages=['nssbackup',
			'nssbackup.ui',
			'nssbackup.util',
			'nssbackup.managers',
			'nssbackup.plugins'],
      package_dir = {'': 'src'},
      data_files=[('share/pixmaps', [datas('nssbackup-restore.png'),
									datas('nssbackup-conf.png')]),
                  ('share/applications', [datas('nssbackup-config.desktop'),
										datas('nssbackup-restore.desktop'),
										datas('nssbackup-config-su.desktop'),
										datas('nssbackup-restore-su.desktop')]),
                  ('share/nssbackup', [datas('nssbackup-config.glade'),
									datas('nssbackup-restore.glade'),
									datas('nssbackup')]),
				  ('bin',[src('nssbackupd'),
						src('nssbackup-config-gui'),
						src('nssbackup-restore-gui'),
						src('upgrade-backups')])
                  ]
     )