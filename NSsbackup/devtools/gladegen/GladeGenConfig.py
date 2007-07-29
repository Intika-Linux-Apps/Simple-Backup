#!/usr/bin/env python

#----------------------------------------------------------------------
# GladeGenConfig.py
# Dave Reed
# 02/03/2004
#----------------------------------------------------------------------

import sys

#----------------------------------------------------------------------

# program author for header of generated file
author = 'Ouattara Aziz'

# date format (this is mm/dd/yyyy)
# see time.strftime format documentation
date_format = '%m/%d/%Y'

# widget types the user wants included in widget list
include_widget_types = [
    'GtkWindow', 'GtkFileChooserButton', 'GtkTable',
    'GtkButton', 'GtkSpinButton', 'GtkCheckButton',
    'GtkEntry', 'GtkCombo', 'GtkTextView', 'GtkRadioButton',
    'GtkImageMenuItem','GtkHBox','GtkVBox','GtkScrolledWindow',
    'GtkNotebook','GtkComboBox','GtkTreeView'
    ]

#----------------------------------------------------------------------

# default text for class and its methods

class_header = 'class %s(GladeWindow):'

constructor = """
\t#----------------------------------------------------------------------

\tdef __init__(self):
\t\t''' '''
\t\tself.init()

\t#----------------------------------------------------------------------

\tdef init(self):
\t\t''' '''
\t\tprint("TODO: init")
\t\tpass

"""
        
#----------------------------------------------------------------------

def main(argv):
    pass

#----------------------------------------------------------------------

if __name__ == '__main__':
    main(sys.argv)
