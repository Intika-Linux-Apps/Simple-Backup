Questions that might appear

Q:
Where are the log files stored by default?

A:
If you run NSsbackup as super-user the log is stored in '/var/log/nssbackup.log'. If you run NSsbackup as user the log is stored in '~/.local/share/nssbackup/nssbackup.log'.



About backups and snapshots:

One can distinguish between full backup snapshots and incremental backup snapshots. Full backups contain all files and directories at a certain time. Full backups does not have a base backup snapshot.

Incremental backups only contain files and directories that have change since the base backup was made. For each incremental snapshot a base backup snapshot must be specified. It is not possible to define more than one base snapshot.


