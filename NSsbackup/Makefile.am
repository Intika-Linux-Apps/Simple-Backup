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
	
uninstall-local:
	$(PYTHON) setup.py uninstall --prefix=$(prefix)

ACLOCAL_AMFLAGS = -I m4

doc_DATA = NEWS ChangeLog README AUTHORS TODO