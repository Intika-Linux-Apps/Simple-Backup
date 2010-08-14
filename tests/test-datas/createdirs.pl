#!/usr/bin/perl

#
# This script creates a huge directory structure with many directories and files.
#

use strict;
use warnings;


my $baseDir = './sbackup-test';

# Number of created lowest-level dirs is $breadth ^ $depth
# depth = 0 means: only files will be created.
my $maxDepth = 2;
my $maxBreadth = 10;
my $filesPerDir = 7;

# good values:
# 2 / 20 / 700 ^= 420d / 280000f


my $numFiles = 0;
my $numDirs = 0;

sub makeDirs
{
    my $curDepth = shift;
    my $parentDir = shift;

    if ($curDepth <= 0)
    {
        # Create files and thats it:
        my $i;
        for ($i = 0; $i < $filesPerDir; $i++)
        {
            my $fileName = "$parentDir/f$i.txt";
            if (open(OUT, ">$fileName"))
            {
                print OUT "sbackup-test\n";
                close(OUT);
                $numFiles++;
            }
        }
    }
    else
    {
        my $i;
        $curDepth--;
        for ($i = 0; $i < $maxBreadth; $i++)
        {
            # Create directory:
            my $dirName = "$parentDir/d$i";
            mkdir($dirName);
            $numDirs++;

            # Recursion:
            &makeDirs($curDepth, $dirName);
        }
    }

    return;
}


print "creating directories\n";
&makeDirs($maxDepth, $baseDir);
print "created $numDirs directories, with $numFiles files\n";
