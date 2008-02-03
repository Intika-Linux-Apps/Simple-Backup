#PO=`for file in \`ls po/*.po\`; do f1=${file##*/}; echo ${f1%%.*}; done`
PO=ca cs de en_GB es fr gl hu id it lv ms nb nl pl pt_BR pt sv tr uk zh_CN zh_TW
PREFIX=/usr/local
DESTDIR=/usr/local
BIN=$(DESTDIR)/bin
# classes dir
PYDIR=$(DESTDIR)/lib/python2.5/site-packages
CLSDIR=$(PYDIR)/nssbackup

all:

default:

install: po-data install-po fill-templates
	python setup.py install --prefix=$(DESTDIR)
	chmod +x $(BIN)/nssbackup* $(BIN)/upgrade-backups $(DESTDIR)/share/nssbackup/multipleTarScript  $(DESTDIR)/share/nssbackup/nssbackup

fill-templates:
	sed s+@prefix@+$(PREFIX)+ src/nssbackup/ressources.in > src/nssbackup/ressources

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
	rm -f src/*.pyc src/*/*.pyc
	rm -f po/*~
	rm -f *~ *.bak
	rm -rf build

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
