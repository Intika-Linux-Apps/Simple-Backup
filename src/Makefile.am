
nssbackupdir = $(pythondir)/$(PACKAGE)
nssbackupuidir = $(nssbackupdir)/ui
nssbackupmanagersdir = $(nssbackupdir)/managers
nssbackuputildir = $(nssbackupdir)/util
nssbackuppluginsdir = $(nssbackupdir)/plugins

nssbackup_PYTHON = nssbackup/__init__.py   nssbackup/nssbackupd.py
nssbackupui_PYTHON = nssbackup/ui/SBConfigGTK.py nssbackup/ui/__init__.py nssbackup/ui/GladeWindow.py nssbackup/ui/SBRestoreGTK.py
nssbackuputil_PYTHON = nssbackup/util/log.py nssbackup/util/__init__.py nssbackup/util/Snapshot.py nssbackup/util/exceptions.py nssbackup/util/structs.py
nssbackupmanagers_PYTHON = nssbackup/managers/UpgradeManager.py nssbackup/managers/__init__.py nssbackup/managers/ConfigManager.py nssbackup/managers/FileAccessManager.py nssbackup/managers/BackupManager.py nssbackup/managers/SnapshotManager.py nssbackup/managers/FuseFAM.py nssbackup/managers/RestoreManager.py
nssbackupplugins_PYTHON = nssbackup/plugins/localFuseFAM.py nssbackup/plugins/__init__.py

nssbackup_ressources_DATA = nssbackup/ressources
nssbackup_ressourcesdir = $(nssbackupdir)

bin_SCRIPTS = nssbackupd nssbackup-config-gui nssbackup-restore-gui upgrade-backups
