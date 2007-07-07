ifndef DESTDIR
	DESTDIR = /usr/local
endif 

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
	cp -rf nssbackup/* $(CLSDIR)
	chmod +x  $(CLSDIR)/managers/UpgradeManager.py $(CLSDIR)/sbackupd.py $(CLSDIR)/ui/SBConfigGTK.py $(CLSDIR)/ui/simple-restore-gnome.py $(CLSDIR)/srestore.py
	ln -s ../$(SUBCLSDIR)/sbackupd.py $(BIN)/nssbackupd
	ln -s ../$(SUBCLSDIR)/ui/SBConfigGTK.py $(BIN)/simple-backup-config
	ln -s ../$(SUBCLSDIR)/ui/simple-restore-gnome.py $(BIN)/simple-restore-gnome
	ln -s ../$(SUBCLSDIR)/srestore.py $(BIN)/srestore
	ln -s ../$(SUBCLSDIR)/managers/UpgradeManager.py $(BIN)/upgrade-backups
#	install ./simple-backup-tocd $(BIN)
	install -m644 -D ./datas/simple-backup-config.glade $(SUPPORT)
	install -m644 -D ./datas/sbackup-conf.png $(PIXDIR)
	install -m644 -D ./datas/sbackup-restore.png $(PIXDIR)
	install -m644 -D ./datas/nssbackup.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/srestore.desktop $(DESTDIR)/share/applications/
	install -m644 -D ./datas/simple-restore.glade $(SUPPORT)
	install ./datas/nssbackup $(SUPPORT)
#	install -m644 -D simple-backup-tocd.glade $(SUPPORT)
ifeq ($(DESTDIR),/usr/local)
	install -b -m600 datas/nssbackup.conf.example /etc/nssbackup.conf
	@echo "[places]" >> /etc/nssbackup.conf
	@echo "prefix=$(PREFIX)" >> /etc/nssbackup.conf
endif

uninstall:
	rm -f $(BIN)/nssbackupd
	rm -f $(BIN)/simple-backup-config
	rm -f $(BIN)/simple-restore-gnome
	rm -f $(BIN)/srestore
	rm -f $(BIN)/upgrade-backups
	rm -rf $(SUPPORT)
	rm -rf $(DOC)
	rm -f $(DESTDIR)/share/applications/nssbackup.desktop
	rm -f $(DESTDIR)/share/applications/srestore.desktop
	rm -rf $(CLSDIR)

clean:
	for lang in $(PO); do rm -rf po/$$lang ; done
	-rm -f *.pyc
	-rm -f po/*~
	-rm -f *.gladep
	-rm -f *~ *.bak

install-po:
	for lang in $(PO); do install -d $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done
	for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(DESTDIR)/share/locale/$$lang/LC_MESSAGES/ ; done

po-dir:
	for lang in $(PO); do mkdir -p po/$$lang/LC_MESSAGES/ ; done

po-data: po-dir
	for lang in $(PO); do msgfmt po/$$lang.po -o po/$$lang/LC_MESSAGES/sbackup.mo ; done

po-gen:
	xgettext -k_ -kN_ -o po/messages.pot -L Python simple-backup-config.py simple-restore-gnome.py srestore.py upgrade_backups.py 
	xgettext -k_ -kN_ -o po/messages.pot -j -L Glade simple-backup-config.glade simple-restore.glade
	for lang in $(PO); do msgmerge -U po/$$lang.po po/messages.pot; done
