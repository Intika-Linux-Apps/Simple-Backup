ifndef DESTDIR
	DESTDIR = /usr/local
endif 

PO = `ls datas/po/*.po | sed s/"datas\/po\/"// | sed s/".po"//`
PREFIX = /usr/local
BIN = $(DESTDIR)/bin/
SUPPORT = $(DESTDIR)/share/nssbackup/
DOC = $(DESTDIR)/share/doc/nssbackup/
PIXDIR = $(DESTDIR)/share/pixmaps/
# classes dir
SUBCLSDIR = lib/python2.5/site-packages/nssbackup
CLSDIR = $(DESTDIR)/$(SUBCLSDIR)

all:

default:

install: po-data install-po 
	install -d $(CLSDIR) $(BIN) $(SUPPORT) $(DOC) $(PIXDIR) $(DESTDIR)/share/applications
ifeq ($(INSTALL),deb)
	@echo "/usr/share/applications/" >>  nssbackup/ressources
	@echo "/usr/share/nssbackup/" >>  nssbackup/ressources
	@echo "/usr/share/doc/nssbackup/" >>  nssbackup/ressources
	@echo "/usr/share/pixmaps/" >>  nssbackup/ressources
else
	@echo "$(SUPPORT)" >>  nssbackup/ressources
	@echo "$(PIXDIR)" >>  nssbackup/ressources
	@echo "$(DOC)" >>  nssbackup/ressources
	@echo "$(DESTDIR)/share/applications/" >>  nssbackup/ressources
endif
	cp -rf nssbackup/* $(CLSDIR)
	@echo "" > nssbackup/ressources
	chmod +x  $(CLSDIR)/managers/UpgradeManager.py $(CLSDIR)/nssbackupd.py $(CLSDIR)/ui/SBConfigGTK.py $(CLSDIR)/ui/SBRestoreGTK.py
	ln -s ../$(SUBCLSDIR)/nssbackupd.py $(BIN)/nssbackupd
	ln -s ../$(SUBCLSDIR)/ui/SBConfigGTK.py $(BIN)/nssbackup-config-gui
	ln -s ../$(SUBCLSDIR)/ui/SBRestoreGTK.py $(BIN)/nssbackup-restore-gui
	ln -s ../$(SUBCLSDIR)/managers/UpgradeManager.py $(BIN)/upgrade-backups
	install -m644 -D ./datas/nssbackup-config.glade $(SUPPORT)
	install -m644 -D ./datas/nssbackup-conf.png $(PIXDIR)
	install -m644 -D ./datas/nssbackup-restore.png $(PIXDIR)
	install -m644 -D ./datas/nssbackup-config.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/nssbackup-restore.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/nssbackup-config-su.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/nssbackup-restore-su.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/nssbackup-restore.glade $(SUPPORT)
	install ./datas/nssbackup $(SUPPORT)
#ifeq ($(DESTDIR),/usr/local)
#	install -b -m600 datas/nssbackup.conf.example /etc/nssbackup.conf
#endif

uninstall:
	rm -f $(BIN)/nssbackupd
	rm -f $(BIN)/nssbackup-config-gui
	rm -f $(BIN)/nssbackup-restore-gui
	rm -f $(BIN)/upgrade-backups
	rm -rf $(SUPPORT)
	rm -rf $(DOC)
	rm -f $(DESTDIR)/share/applications/nssbackup-config.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-config-su.desktop
	rm -f $(DESTDIR)/share/applications/nssbackup-restore-su.desktop
	rm -rf $(CLSDIR)
	rm -f $(PIXDIR)/nssbackup-conf.png
	rm -f $(PIXDIR)/nssbackup-restore.png
	find $(DESTDIR)/share/locale/ -name nssbackup.mo -exec rm -rf '{}' \;

clean:
	@echo "" > nssbackup/ressources
	for lang in $(PO); do rm -rf datas/po/$$lang ; done
	find ./ -name *.pyc -exec rm -f '{}' \;
	-rm -f datas/po/*~
	-rm -f datas/*.gladep
	-rm -f datas/*~ datas/*.bak *~

install-po:
	for lang in $(PO); do install -d $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	for lang in $(PO); do install -m 644 datas/po/$$lang/LC_MESSAGES/* $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done

po-dir:
	for lang in $(PO); do mkdir -p datas/po/$$lang/LC_MESSAGES/ ; done

po-data: po-dir
	for lang in $(PO); do msgfmt datas/po/$$lang.po -o datas/po/$$lang/LC_MESSAGES/nssbackup.mo ; done

po-gen:
	xgettext -k_ -kN_ -o datas/po/messages.pot -L Python nssbackup/*.py nssbackup/managers/*.py nssbackup/ui/*.py nssbackup/util/*.py nssbackup/plugins/*.py
	xgettext -k_ -kN_ -o datas/po/messages.pot -j -L Glade datas/*.glade
	for lang in $(PO); do msgmerge -U datas/po/$$lang.po datas/po/messages.pot; done
