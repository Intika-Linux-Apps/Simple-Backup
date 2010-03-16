# makefile for NSsbackup

PKGNAME=nssbackup
VERSION=0.2-0~rc8.1

PYTHON=`which python`

# available languages UI
PO=ar bg ca cs de en_GB es fr gl he hu id it lv ms nb nl pl pt pt_BR ru sv tr uk zh_CN zh_TW

# available languages Help/Manual
HELPLANG=C

# installation into /usr/local to be compliant to GNU standards
PREFIX=/usr/local
DESTDIR=/usr/local
DATADIR=$(DESTDIR)/share
HELPDIR=$(DATADIR)/gnome/help/$(PKGNAME)
LANGDIR=$(DATADIR)/locale
BIN=$(DESTDIR)/bin
SBIN=$(DESTDIR)/sbin

SETUP.PY_OPTS=--root=/

UbuntuVersion=$(shell lsb_release -rs)
# if we use jaunty or karmic
ifneq (,$(findstring 9.04,$(UbuntuVersion)))
    LAYOUT="--install-layout=deb"
endif
ifneq (,$(findstring 9.10,$(UbuntuVersion)))
    LAYOUT="--install-layout=deb"
endif


all: po-data fill-templates

default:

install: install-po install-help install-bin install-sbin install-package
	chmod +x $(BIN)/nssbackup*
	chmod +x $(SBIN)/nssbackup*
	chmod +x $(DESTDIR)/share/nssbackup/multipleTarScript
	chmod +x $(DESTDIR)/share/nssbackup/nssbackup

fill-templates:
	set -e; sed s+@prefix@+$(PREFIX)+ src/nssbackup/ressources.in > src/nssbackup/ressources
	sed s+@version@+2.0+ setup.py.in > setup.py

# application's binaries
install-bin:
	mkdir -p $(BIN)
	cp -a scripts/nssbackupd.py $(BIN)/nssbackupd
	cp -a scripts/nssbackup-config-gui.py $(BIN)/nssbackup-config-gui
	cp -a scripts/nssbackup-restore-gui.py $(BIN)/nssbackup-restore-gui
	cp -a scripts/nssbackup-upgrade-backups.py $(BIN)/nssbackup-upgrade-backups

# Configuration and setup tools
install-sbin:
	mkdir -p $(SBIN)
	cp -a scripts/nssbackupconfig.py $(SBIN)/nssbackupconfig
	
install-package:
	$(PYTHON) setup.py install ${SETUP.PY_OPTS} --prefix=$(PREFIX) $(LAYOUT)

install-po:
	set -e; for lang in $(PO); do install -d $(LANGDIR)/$$lang/LC_MESSAGES/ ; done
	set -e; for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(LANGDIR)/$$lang/LC_MESSAGES/ ; done

install-help:
	install -d $(HELPDIR)
	set -e; for lang in $(HELPLANG); do \
	install -d $(HELPDIR)/$$lang/; \
	install -d $(HELPDIR)/$$lang/figures; \
	install -m 644 help/$$lang/*.page $(HELPDIR)/$$lang/; \
	install -m 644 help/$$lang/*.xml $(HELPDIR)/$$lang/; \
	install -m 644 help/$$lang/figures/*.png $(HELPDIR)/$$lang/figures; \
	done

# targets for un-installation
uninstall: uninstall-bin uninstall-sbin uninstall-package uninstall-data uninstall-help

uninstall-bin:
	rm -f $(BIN)/nssbackupd
	rm -f $(BIN)/nssbackup-config-gui
	rm -f $(BIN)/nssbackup-restore-gui
	rm -f $(BIN)/nssbackup-upgrade-backups

uninstall-sbin:
	rm -f $(SBIN)/nssbackupconfig

uninstall-package:
	rm -rf $(DESTDIR)/lib/python*/*/nssbackup*

uninstall-data:
	rm -f $(DATADIR)/pixmaps/nssbackup-restore.png
	rm -f $(DATADIR)/pixmaps/nssbackup-conf.png
	rm -f $(DATADIR)/pixmaps/nssbackup.png
	rm -f $(DATADIR)/pixmaps/nssbackup32x32.png
	rm -f $(DATADIR)/applications/nssbackup-config.desktop
	rm -f $(DATADIR)/applications/nssbackup-restore.desktop
	rm -f $(DATADIR)/applications/nssbackup-config-su.desktop
	rm -f $(DATADIR)/applications/nssbackup-restore-su.desktop
	rm -rf $(DATADIR)/nssbackup
	rm -rf $(DATADIR)/doc/nssbackup
	set -e; find $(LANGDIR) -name nssbackup.mo -exec rm -f '{}' \;
	
uninstall-help:
	rm -rf $(HELPDIR)
	
reinstall: uninstall install

clean:
	set -e; find . -name '*.pyc' -exec rm -f '{}' \;
	set -e; find . -name '*~' -exec rm -f '{}' \;
	set -e; find . -name '*.bak' -exec rm -f '{}' \;
	rm -rf build dist setup.py
	rm -f src/nssbackup/ressources
	rm -rf src/nssbackup.egg-info
	set -e; for lang in $(PO); do rm -rf po/$$lang ; done
	
po-dir:
	set -e; for lang in $(PO); do mkdir -p po/$$lang/LC_MESSAGES/ ; done

po-data: po-dir
	set -e; for lang in $(PO); do msgfmt po/nssbackup-$$lang.po -o po/$$lang/LC_MESSAGES/nssbackup.mo ; done
	
po-gen:
	set -e; xgettext -o po/nssbackup.pot src/nssbackup/*.py src/nssbackup/*/*.py datas/*.glade datas/*.desktop scripts/*.py
	set -e; for lang in $(PO); do msgmerge -U po/nssbackup-$$lang.po po/nssbackup.pot; done

