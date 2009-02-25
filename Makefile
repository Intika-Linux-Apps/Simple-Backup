# makefile for NSsbackup

# available languages
PO=ar bg ca cs de en_GB es fr gl he hu id it lv ms nb nl pl pt pt_BR sv tr uk zh_CN zh_TW

# installation into /usr/local to be compliant to GNU standards
PREFIX=/usr/local
DESTDIR=/usr/local

BIN=$(DESTDIR)/bin
SBIN=$(DESTDIR)/sbin

# definition of classes directory
PYDIR=$(DESTDIR)/lib/python2.5/site-packages
CLSDIR=$(PYDIR)/nssbackup

all: po-data fill-templates

default:

install: install-po install-bin install-sbin install-package install-data
	chmod +x $(BIN)/nssbackup*
	chmod +x $(SBIN)/nssbackup*
	chmod +x $(DESTDIR)/share/nssbackup/multipleTarScript
	chmod +x $(DESTDIR)/share/nssbackup/nssbackup

fill-templates:
	set -e; sed s+@prefix@+$(PREFIX)+ src/nssbackup/ressources.in > src/nssbackup/ressources

# application's binaries
install-bin:
	mkdir -p $(BIN)
	cp -a src/nssbackupd.py $(BIN)/nssbackupd
	cp -a src/nssbackup-config-gui.py $(BIN)/nssbackup-config-gui
	cp -a src/nssbackup-restore-gui.py $(BIN)/nssbackup-restore-gui
	cp -a src/nssbackup-upgrade-backups.py $(BIN)/nssbackup-upgrade-backups

# Configuration and setup tools
install-sbin:
	mkdir -p $(SBIN)
	cp -a src/nssbackupconfig.py $(SBIN)/nssbackupconfig
	
install-package:
	mkdir -p $(CLSDIR)
	cp -a src/nssbackup/* $(CLSDIR)
	rm -f $(CLSDIR)/ressources.in  

install-po:
	set -e; for lang in $(PO); do install -d $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	set -e; for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done

install-data:
	mkdir -p $(DESTDIR)/share/nssbackup
	cp -a datas/multipleTarScript $(DESTDIR)/share/nssbackup/
	cp -a datas/nssbackup $(DESTDIR)/share/nssbackup/
	cp -a datas/*.glade $(DESTDIR)/share/nssbackup/

	mkdir -p $(DESTDIR)/share/pixmaps
	cp -a datas/*.png $(DESTDIR)/share/pixmaps/

	mkdir -p $(DESTDIR)/share/applications
	cp -a datas/*.desktop $(DESTDIR)/share/applications/

uninstall: uninstall-bin uninstall-sbin uninstall-package uninstall-data

uninstall-bin:
	rm -f $(BIN)/nssbackupd
	rm -f $(BIN)/nssbackup-config-gui
	rm -f $(BIN)/nssbackup-restore-gui
	rm -f $(BIN)/nssbackup-upgrade-backups

uninstall-sbin:
	rm -f $(SBIN)/nssbackupconfig

uninstall-package:
	rm -rf $(CLSDIR)

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
	rm -rf build
	rm -f src/nssbackup/ressources
	set -e; for lang in $(PO); do rm -rf po/$$lang ; done
	
po-dir:
	set -e; for lang in $(PO); do mkdir -p po/$$lang/LC_MESSAGES/ ; done

po-data: po-dir
	set -e; for lang in $(PO); do msgfmt po/$$lang.po -o po/$$lang/LC_MESSAGES/nssbackup.mo ; done
	
po-gen:
	set -e; xgettext -o po/messages.pot src/nssbackup/*.py src/nssbackup/*/*.py datas/*.glade datas/*.desktop src/nssbackup-upgrade-backups.py src/nssbackupconfig.py
	set -e; for lang in $(PO); do msgmerge -U po/$$lang.po po/messages.pot; done
