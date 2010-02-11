#!/usr/bin/env python
'''
This script giving a fasta file with sequences perform and all against all blast
alignment. It preprares the sequences, format them and do the actual alignment
'''
from optparse import OptionParser
import os
from franklin.contig_io import contig_to_fasta
from franklin.biolib_cmd_utils import call

def main():
    '''main section '''
    parser = OptionParser('usage: %prog -i infile [-t]...', version='%prog 1.0')
    parser.add_option('-i', '--infile', dest='infile', help='Input file')
    parser.add_option('-d', '--directory', dest='directory', help='directory')
    options = parser.parse_args()[0]

    if options.infile is None:
        parser.error('Script at least needs an input file (caf|ace)')
    else:
        infile = options.infile
    if options.directory is None:
        parser.error('Script needs the working directory')
    else:
        directory = options.directory

    if not os.path.exists(directory):
        os.mkdir(directory)

    print "Extracting consensus fastas from contig"
    fasta   = contig_to_fasta(infile)
    fasta_path = os.path.join(directory,
                              os.path.basename(infile)[:-3] + 'fasta')
    fasta_name = os.path.basename(fasta_path)
    fasta_fhand = open(fasta_path, 'w')
    fasta_fhand.write(fasta)
    fasta_fhand.close()

    os.chdir(directory)
    print "Formatdb: formating blast database"
    cmd = ['formatdb', '-i', fasta_name, '-V', '-p', 'F', '-o']
    stdout, stderr, retcode = call(cmd)
    print retcode

    print "Performing blast search"
    cmd = ['blastall', '-p', 'blastn', '-d', fasta_name, '-i', fasta_name ,
           '-e' , '0.0001', '-n', '-b', '30', '-v', '30', '-m', '7', '-o',
           fasta_name[:-5] + 'blastout.xml' ]
    stdout, stderr, retcode = call(cmd)
    print retcode



if __name__ == '__main__':
    main()
