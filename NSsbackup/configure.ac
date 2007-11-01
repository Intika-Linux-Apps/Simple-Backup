#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT(nssbackup, 0.2-0, https://bugs.launchpad.net/nssbackup/)
AM_INIT_AUTOMAKE([-Wall -Werror gnu])

dnl check for python
dnl AM_PATH_PYTHON
AM_PATH_PYTHON


dnl *******************************
dnl Internationalization
dnl ******************************* 
GETTEXT_PACKAGE=nssbackup

AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE")
AC_SUBST(GETTEXT_PACKAGE)
dnl AC_CONFIG_MACRO_DIR([m4])
GNOME_DOC_INIT

dnl Add the languages which your application supports here.
ALL_LINGUAS="ca de es gl id lv nb pl pt tr zh_CN cs en_GB fr hu it ms nl pt_BR sv uk zh_TW"

AM_GLIB_GNU_GETTEXT
AC_PROG_INTLTOOL

AC_OUTPUT([ Makefile  
po/Makefile.in
src/nssbackup/ressources
])
