# makefile for NSsbackup

PYTHON=`which python`
VERSION=0.2-0~rc7

# available languages
PO=ar bg ca cs de en_GB es fr gl he hu id it lv ms nb nl pl pt pt_BR ru sv tr uk zh_CN zh_TW

# installation into /usr/local to be compliant to GNU standards
PREFIX=/usr/local
DESTDIR=/usr/local

SETUP.PY_OPTS=--root=/

UbuntuVersion=$(shell lsb_release -rs)
# if we use jaunty or karmic
ifneq (,$(findstring 9.04,$(UbuntuVersion)))
    LAYOUT="--install-layout=deb"
endif
ifneq (,$(findstring 9.10,$(UbuntuVersion)))
    LAYOUT="--install-layout=deb"
endif


BIN=$(DESTDIR)/bin
SBIN=$(DESTDIR)/sbin

# definition of classes directory

all: po-data fill-templates

default:

install: install-po install-bin install-sbin install-package
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
	set -e; for lang in $(PO); do install -d $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	set -e; for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done

uninstall: uninstall-bin uninstall-sbin uninstall-package uninstall-data

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
	rm -f $(DESTDIR)/share/pixmaps/nssbackup-restore.png
	rm -f $(DESTDIR)/share/pixmaps/nssbackup-conf.png
	rm -f $(DESTDIR)/share/pixmaps/nssbackup.png
	rm -f $(DESTDIR)/share/pixmaps/nssbackup32x32.png
	rm -f $(DESTDIR)/share/applications/nssbackup-config.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-config-su.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore-su.desktop
	rm -rf $(DESTDIR)/share/nssbackup
	set -e; find $(DESTDIR)/share/locale -name nssbackup.mo -exec rm -f '{}' \;
	
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

