#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT(nssbackup, 0.1-2, https://bugs.launchpad.net/nssbackup/)
AM_INIT_AUTOMAKE([-Wall -Werror gnu])

dnl check for python
dnl AM_PATH_PYTHON
AM_PATH_PYTHON

PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= 2.6)
AC_SUBST(PYGTK_CFLAGS)
AC_SUBST(PYGTK_LIBS)

AC_PATH_PROG( PKGCONFIG, pkg-config, no, $PATH:/usr/bin:/usr/local/bin)
  if test "$PKGCONFIG" != "no" ; then
    AC_MSG_CHECKING([PYTHONPATH env variable for PyGTK])
    PYTHONPATH=$($PKGCONFIG --variable=pyexecdir pygtk-2.0)
    AC_SUBST([PYTHONPATH])
    AC_MSG_RESULT($PYTHONPATH)
  fi

export PYTHONPATH=$PYGTK_DIR:$PYTHONPATH
dnl check for libglade
AC_MSG_CHECKING(for gtk.glade)
prog="
import sys
try:
  import gtk.glade
except RuntimeError:
  sys.exit(0)
except ImportError:
  sys.exit(1)
sys.exit(0)
"

if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need to have python libglade bindings installed])
fi
AC_PATH_PROG(CRONTAB_CONFIG, crontab, no)
if test x$CRONTAB_CONFIG = xno; then
  AC_MSG_ERROR(Please install the application crontab)
fi

AC_PATH_PROG(PYTHON_CONFIG, python, no)
if test x$PYTHON_CONFIG = xno; then
  AC_MSG_ERROR(Please install the application python)
fi

AC_PATH_PROG(SU_CONFIG, su, no)
if test x$BATCH_CONFIG = xno; then
  AC_MSG_ERROR(Please install the application su)
fi

AC_PATH_PROG(tar_CONFIG, tar, no)
if test x$CRONTAB_CONFIG = xno; then
  AC_MSG_ERROR(Please install the application tar)
fi

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
datas/Makefile
src/Makefile
src/nssbackup/ressources
tests/Makefile
])
