
Snapshot format versions
========================

Overview over existing snapshot format versions:

* 1.0 --- the original version that was used by sbackup up to 0.10.x ??? Is that right?
* 1.1 --- was it ever used?
* 1.2 --- used by Simple Backup version xxx?
		  - data stored in file `tree` was split and stored in `flist`
		    containing the list of files and `fprops` containing the
		    file properties
* 1.3 --- used by Simple Backup version xxx?
		  - internal format of `flist` and `fprops` changed, instead of newline
		    (\n) now ASCII Nul (\000) was used to separate entries
* 1.4 --- no changes but the version numbering
* 1.5 --- the latest snapshot format
		  - files containing the include and exclude lists were introduced
		  - the archive was renamed into *.tar.gz
		  - a file containing format informations was introduced (`format`)
		  - SNAR files were used instead of
		  
		  
		  
		  
		  
		  
common functionality for SNAR files:

* creation of empty snar files
* setting of header with a certain snapshot date
  