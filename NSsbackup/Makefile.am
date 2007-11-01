SUBDIRS = po

intltool_extra = intltool-extract.in intltool-merge.in intltool-update.in

CLEANFILES = \
	configure.in

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update		\
	po/.intltool-merge-cache

install-exec-local:
	$(PYTHON) setup.py install --prefix=$(prefix)
	chmod +x $(bindir)/nssbackup* $(bindir)/upgrade-backups
	
uninstall-local: uninstall-local-bin uninstall-local-data

uninstall-local-bin:
	rm -f $(bindir)/nssbackupd
	rm -f $(bindir)/nssbackup-config-gui
	rm -f $(bindir)/nssbackup-restore-gui
	rm -f $(bindir)/upgrade-backups

uninstall-local-data:
	rm -f $(prefix)/share/pixmaps/nssbackup-restore.png
	rm -f $(prefix)/share/pixmaps/nssbackup-conf.png
	rm -f $(prefix)/share/applications/nssbackup-config.desktop
	rm -f $(prefix)/share/applications/nssbackup-restore.desktop
	rm -f $(prefix)/share/applications/nssbackup-config-su.desktop
	rm -f $(prefix)/share/applications/nssbackup-restore-su.desktop
	rm -f $(prefix)/share/nssbackup/nssbackup-config.glade
	rm -f $(prefix)/share/nssbackup/nssbackup-restore.glade
	rm -f $(prefix)/share/nssbackup/nssbackup
	rm -rf $(pythondir)/nssbackup $(pythondir)/NSsbackup*

ACLOCAL_AMFLAGS = -I m4

doc_DATA = NEWS ChangeLog README AUTHORS TODO
