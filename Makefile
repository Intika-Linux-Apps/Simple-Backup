#PO=`for file in \`ls po/*.po\`; do f1=${file##*/}; echo ${f1%%.*}; done`
PO=ca cs de en_GB es fr gl hu id it lv ms nb nl pl pt_BR pt sv tr uk zh_CN zh_TW
PREFIX=/usr/local
DESTDIR=/usr/local
BIN=$(DESTDIR)/bin
# classes dir
PYDIR=$(DESTDIR)/lib/python2.5/site-packages
CLSDIR=$(PYDIR)/nssbackup

all: po-data fill-templates

default:

install: install-po install-bin install-classes install-data
	chmod +x $(BIN)/nssbackup* $(BIN)/upgrade-backups $(DESTDIR)/share/nssbackup/multipleTarScript  $(DESTDIR)/share/nssbackup/nssbackup

fill-templates:
	sed s+@prefix@+$(PREFIX)+ src/nssbackup/ressources.in > src/nssbackup/ressources

install-bin:
	mkdir -p $(BIN)
	cp -a src/nssbackupd $(BIN)/nssbackupd
	cp -a src/nssbackup-config-gui $(BIN)/nssbackup-config-gui
	cp -a src/nssbackup-restore-gui $(BIN)/nssbackup-restore-gui
	cp -a src/upgrade-backups $(BIN)/upgrade-backups

install-classes:
	mkdir -p $(CLSDIR)
	cp -a src/nssbackup/* $(CLSDIR)
	rm -f $(CLSDIR)/ressources.in  

install-data:
	mkdir -p $(DESTDIR)/share/pixmaps
	cp -a datas/*.png $(DESTDIR)/share/pixmaps/
	mkdir -p $(DESTDIR)/share/applications
	cp -a datas/*.desktop $(DESTDIR)/share/applications/
	mkdir -p $(DESTDIR)/share/nssbackup
	cp -a datas/*.glade $(DESTDIR)/share/nssbackup/
	cp -a datas/nssbackup $(DESTDIR)/share/nssbackup/
	cp -a datas/multipleTarScript $(DESTDIR)/share/nssbackup/

uninstall: uninstall-bin uninstall-data

uninstall-bin:
	rm -f $(BIN)/nssbackupd
	rm -f $(BIN)/nssbackup-config-gui
	rm -f $(BIN)/nssbackup-restore-gui
	rm -f $(BIN)/upgrade-backups

uninstall-data:
	rm -f $(DESTDIR)/share/pixmaps/nssbackup-restore.png
	rm -f $(DESTDIR)/share/pixmaps/nssbackup-conf.png
	rm -f $(DESTDIR)/share/applications/nssbackup-config.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-config-su.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore-su.desktop
	rm -f $(DESTDIR)/share/nssbackup/nssbackup-config.glade
	rm -f $(DESTDIR)/share/nssbackup/nssbackup-restore.glade
	rm -f $(DESTDIR)/share/nssbackup/nssbackup
	rm -rf $(PYDIR)/nssbackup $(PYDIR)/NSsbackup*
	
reinstall: uninstall install

clean:
	find . -name '*.pyc' -exec rm -f '{}' \;
	find . -name '*~' -exec rm -f '{}' \;
	find . -name '*.bak' -exec rm -f '{}' \;
	rm -rf build
	rm -f src/nssbackup/ressources
	for lang in $(PO); do rm -rf po/$$lang ; done

install-po:
	for lang in $(PO); do install -d $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	
po-dir:
	for lang in $(PO); do mkdir -p po/$$lang/LC_MESSAGES/ ; done

po-data: po-dir
	for lang in $(PO); do msgfmt po/$$lang.po -o po/$$lang/LC_MESSAGES/nssbackup.mo ; done
	
po-gen:
	xgettext -o po/messages.pot src/nssbackup/*.py src/nssbackup/*/*.py datas/*.glade datas/*.desktop src/upgrade-backups
	for lang in $(PO); do msgmerge -U po/$$lang.po po/messages.pot; done
