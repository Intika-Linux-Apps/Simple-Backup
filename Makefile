################################################################################
#
#   Simple Backup - GNU Makefile
#
#   Copyright (c)2008-2011,2013: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2010: Ouattara Oumar Aziz <wattazoum@gmail.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
################################################################################

# grab name and current version
METAFILE="METAINFO"
VERSION=$(shell grep "^VERSION=" $(METAFILE)|cut -d "=" -f 2 -)
PKGNAME=$(shell grep "^PKGNAME=" $(METAFILE)|cut -d "=" -f 2 -)

# retrieve/determine used applications (version of Python interpreter...)
PYTHON=$(shell which python)
servicetool=$(shell which service)
gconftool=$(shell which gconftool-2)

export GCONF_CONFIG_SOURCE=$(shell if test -x "$(gconftool)"; then $(gconftool) --get-default-source; fi)

# available languages UI
PO=ar bg ca cs de en_AU en_CA en_GB es fi fo fr gl he hu id it lv ms nb nl oc pl pt pt_BR ru sv tr uk zh_CN zh_TW da el fa is ja kk ko kw ro sr sw

# available languages Help/Manual
HELPLANG=C


# definition of paths and filenames
# installation into /usr/local to be compliant to GNU standards
PREFIX=/usr/local
DESTDIR=/usr/local

datadir=$(DESTDIR)/share
bindir=$(DESTDIR)/bin
sbindir=$(DESTDIR)/sbin

libdir=$(datadir)/$(PKGNAME)
helpdir=$(datadir)/gnome/help/$(PKGNAME)
langdir=$(datadir)/locale
icondir=$(datadir)/icons
gconf_schema_file_dir=$(datadir)/gconf/schemas

sysconf_dir=/etc
dbus_system_conf_dir=$(sysconf_dir)/dbus-1/system.d

gconf_schema_file=apps_sbackup_global-preferences.schemas
dbus_system_conf_file=org.sbackupteam.SimpleBackup.conf

iconslst=sbackup-panel.png sbackup-attention.png sbackup-success.png

gtk_update_icon_cache=if test "$(DISABLE_MAKEFILE_GTK_UPDATE_ICON_CACHE)" = ""; then \
						gtk-update-icon-cache -f -t $(icondir)/hicolor; \
						gtk-update-icon-cache -f -t $(icondir)/ubuntu-mono-light; \
						gtk-update-icon-cache -f -t $(icondir)/ubuntu-mono-dark; fi

# distutils options
SETUP.PY_OPTS=--root=/ --install-lib $(libdir) -O0


default: build-po fill-templates
	$(PYTHON) setup.py build

build-po:
	set -e; for lang in $(PO); do install -d po/$$lang/LC_MESSAGES/ ; done
	set -e; for lang in $(PO); do msgfmt po/$$lang.po -o po/$$lang/LC_MESSAGES/sbackup.mo ; done

#TODO: use intltool and scan *.desktop...
po-gen:
	set -e; xgettext -o po/sbackup.pot src/sbackup/*.py src/sbackup/*/*.py data/ui/*.glade scripts/*.py
	set -e; for lang in $(PO); do msgmerge -U po/$$lang.po po/sbackup.pot; done

fill-templates:
	set -e; sed s+@prefix@+$(PREFIX)+ src/sbackup/resources.in > src/sbackup/resources
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-config.desktop.in > data/desktop/sbackup-config.desktop
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-config-su.desktop.in > data/desktop/sbackup-config-su.desktop.tmp
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-config-su.desktop.tmp > data/desktop/sbackup-config-su.desktop
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-restore.desktop.in > data/desktop/sbackup-restore.desktop
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-restore-su.desktop.in > data/desktop/sbackup-restore-su.desktop.tmp
	set -e; sed s+@prefix@+$(PREFIX)+ data/desktop/sbackup-restore-su.desktop.tmp > data/desktop/sbackup-restore-su.desktop
	set -e; sed s+@version@+$(VERSION)+ setup.py.in > setup.py.tmp
	set -e; sed s+@pkgname@+$(PKGNAME)+ setup.py.tmp > setup.py
	set -e; sed s+@version@+$(VERSION)+ src/sbackup/metainfo.in > src/sbackup/metainfo.tmp
	set -e; sed s+@pkgname@+$(PKGNAME)+ src/sbackup/metainfo.tmp > src/sbackup/metainfo
	rm -f data/desktop/*.tmp src/sbackup/*.tmp *.tmp

check:
	@echo "Check for another installation of sbackup"
	@set -e; for lang in $(DESTDIR)/sbin/sbackupd $(DESTDIR)/bin/sbackup $(DESTDIR)/../sbin/sbackupd $(DESTDIR)/../bin/sbackup; do echo "	checking: $$lang"; if [ -e $$lang ]; then echo "Another installation of sbackup is present. Please uninstall first."; exit 1; fi ; done
	@set -e; for lang in $(DESTDIR)/bin/nssbackupd $(DESTDIR)/../bin/nssbackupd; do echo "	checking: $$lang"; if [ -e $$lang ]; then echo "Another installation of nssbackup is present. Please uninstall first."; exit 1; fi ; done

install: check install-package install-po install-help install-bin install-data
	chmod +x $(libdir)/multipleTarScript
	chmod +x $(libdir)/sbackup-launch
	chmod +x $(libdir)/sbackup-dbusservice
	chmod +x $(libdir)/sbackup-indicator
	chmod +x $(libdir)/sbackup-progress
	chmod +x $(libdir)/sbackup-terminate
	chmod +x $(libdir)/sbackup-run
	chmod +x $(libdir)/sbackup-config-gtk
	chmod +x $(libdir)/sbackup-restore-gtk
	chmod +x $(libdir)/sbackupconfig.py

# application's binaries
install-bin:
	install -d $(bindir) $(sbindir)
	ln -sf ../share/sbackup/sbackup-run $(bindir)/sbackup
	ln -sf ../share/sbackup/sbackup-config-gtk $(bindir)/sbackup-config-gtk
	ln -sf ../share/sbackup/sbackup-restore-gtk $(bindir)/sbackup-restore-gtk
	ln -sf ../share/sbackup/sbackupconfig.py $(sbindir)/sbackupconfig

# python package
install-package:
	$(PYTHON) setup.py install ${SETUP.PY_OPTS} --prefix=$(PREFIX)

# localization
install-po:
	set -e; for lang in $(PO); do install -d $(langdir)/$$lang/LC_MESSAGES/ ; done
	set -e; for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/* $(langdir)/$$lang/LC_MESSAGES/ ; done

# help/manual
install-help:
	install -d $(helpdir)
	set -e; for lang in $(HELPLANG); do \
	install -d $(helpdir)/$$lang/; \
	install -d $(helpdir)/$$lang/figures; \
	install -m 644 help/$$lang/*.page $(helpdir)/$$lang/; \
	install -m 644 help/$$lang/*.xml $(helpdir)/$$lang/; \
	install -m 644 help/$$lang/figures/*.png $(helpdir)/$$lang/figures; \
	done

# additional data/configuration
install-data: install-icons install-dbus install-gconf
	@if test "$(DISABLE_MAKEFILE_DESKTOP_DATABASE_RELOAD)" = ""; then \
	update-desktop-database; fi

install-icons:
	install -d $(icondir)/hicolor/24x24/apps/ $(icondir)/ubuntu-mono-light/apps/24/ $(icondir)/ubuntu-mono-dark/apps/24/
	set -e; for icon in $(iconslst); do install -m 644 data/icons/hicolor/24x24/$$icon $(icondir)/hicolor/24x24/apps/ ; done
	set -e; for icon in $(iconslst); do install -m 644 data/icons/ubuntu-mono-light/24/$$icon $(icondir)/ubuntu-mono-light/apps/24/ ; done
	set -e; for icon in $(iconslst); do install -m 644 data/icons/ubuntu-mono-dark/24/$$icon $(icondir)/ubuntu-mono-dark/apps/24/ ; done
	$(gtk_update_icon_cache)

install-dbus:
	install -d $(dbus_system_conf_dir)
	install -m 644 data/$(dbus_system_conf_file) $(dbus_system_conf_dir)
	@if test "$(DISABLE_MAKEFILE_DBUS_RELOAD)" = ""; then \
	if [ -x $(servicetool) ]; then \
	$(servicetool) dbus force-reload; \
	else if [ -r /etc/init.d/dbus ]; then \
	invoke-rc.d dbus force-reload; fi; fi; \
	fi

install-gconf:
	install -d $(gconf_schema_file_dir)
	install -m 644 data/$(gconf_schema_file) $(gconf_schema_file_dir)
	@if test "$(GCONF_DISABLE_MAKEFILE_SCHEMA_INSTALL)" = ""; then \
	gconf-schemas --register $(gconf_schema_file_dir)/$(gconf_schema_file); \
	fi


# targets for un-installation
uninstall: uninstall-package uninstall-bin uninstall-data uninstall-help clean-data

uninstall-bin:
	rm -f $(bindir)/sbackup
	rm -f $(bindir)/sbackup-config-gtk
	rm -f $(bindir)/sbackup-restore-gtk
	rm -f $(sbindir)/sbackupconfig

uninstall-package:
	rm -rf $(libdir)

uninstall-data: uninstall-icons uninstall-dbus uninstall-gconf
	rm -f $(datadir)/pixmaps/sbackup-restore.png
	rm -f $(datadir)/pixmaps/sbackup-conf.png
	rm -f $(datadir)/pixmaps/sbackup.png
	rm -f $(datadir)/pixmaps/sbackup32x32.png
	rm -f $(datadir)/applications/sbackup-config*.desktop
	rm -f $(datadir)/applications/sbackup-restore*.desktop
	rm -rf $(datadir)/doc/sbackup
	set -e; find $(langdir) -name sbackup.mo -exec rm -f '{}' \;

uninstall-icons:
	set -e; for icon in $(iconslst); do rm -f $(icondir)/hicolor/24x24/apps/$$icon ; done
	set -e; for icon in $(iconslst); do rm -f $(icondir)/ubuntu-mono-light/apps/24/$$icon ; done
	set -e; for icon in $(iconslst); do rm -f $(icondir)/ubuntu-mono-dark/apps/24/$$icon ; done
	$(gtk_update_icon_cache)

uninstall-dbus:
	rm -f $(dbus_system_conf_dir)/$(dbus_system_conf_file)

#FIXME: treat gconf schema file as proper conffile?
uninstall-gconf:
	@if test "$(GCONF_DISABLE_MAKEFILE_SCHEMA_INSTALL)" = ""; then \
	if test -r "$(gconf_schema_file_dir)/$(gconf_schema_file)"; then \
	gconf-schemas --unregister $(gconf_schema_file_dir)/$(gconf_schema_file); fi; \
	fi
	rm -f $(gconf_schema_file_dir)/$(gconf_schema_file)


uninstall-help:
	rm -rf $(helpdir)

clean-data: clean-crondata clean-tmpdata

# remove script/symlinks from cron directory
clean-crondata:
	@if test "$(DISABLE_MAKEFILE_CLEAN_DATA)" = ""; then \
	rm -f /etc/cron.d/sbackup; \
	rm -f /etc/cron.hourly/sbackup; \
	rm -f /etc/cron.daily/sbackup; \
	rm -f /etc/cron.weekly/sbackup; \
	rm -f /etc/cron.monthly/sbackup; fi

clean-tmpdata:
	@if test "$(DISABLE_MAKEFILE_CLEAN_DATA)" = ""; then \
	rm -rf /var/log/sbackup; \
	rm -f /var/log/sbackup-*.log; \
	rm -f /var/log/sbackup-*.log.*.gz; \
	rm -rf /tmp/sbackup; fi

purge-user-config:
	rm -f /etc/sbackup.conf
	rm -rf /etc/sbackup.d


reinstall: uninstall install


# clean source code directory
clean:
	set -e; find . -name '*.py[co]' -exec rm -f '{}' \;
	set -e; find . -name '*~' -exec rm -f '{}' \;
	set -e; find . -name '*.bak' -exec rm -f '{}' \;
	rm -rf build dist setup.py
	rm -f data/desktop/sbackup-config*.desktop
	rm -f data/desktop/sbackup-restore*.desktop
	rm -f src/sbackup/resources
	rm -f src/sbackup/metainfo
	rm -rf src/sbackup.egg-info
	set -e; for lang in $(PO); do rm -rf po/$$lang ; done

# Purpose of this target is to print some informational data
show-infos:
	@echo "Summary of parameters"
	@echo "  Metafile     : "$(METAFILE)
	@echo "  Version      : "$(VERSION)
	@echo "  Package name : "$(PKGNAME)
	@echo "  Python       : "$(PYTHON)
	@echo "  setup.py opts: "$(SETUP.PY_OPTS)
	@echo
	@echo "Directories"
	@echo "  PREFIX      : "$(PREFIX)
	@echo "  DESTDIR     : "$(DESTDIR)
	@echo "  datadir     : "$(datadir)
	@echo "  helpdir     : "$(helpdir)
	@echo "  langdir     : "$(langdir)
	@echo "  bindir      : "$(bindir)
	@echo "  sbindir     : "$(sbindir)

