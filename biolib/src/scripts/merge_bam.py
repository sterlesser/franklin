#!/usr/bin/env python
'''
Thi sscript takes all the bam files from a directory and merges them using
and optional new header.

It adds to each of the alignment on a bam file the reaf group tag, taking it
from the file name. It can be disabled from options

Created on 07/01/2010

@author: peio
'''

from optparse import OptionParser
import os, re
from tempfile import NamedTemporaryFile
from biolib.utils.misc_utils import NamedTemporaryDir
from biolib.utils.cmd_utils import call
from biolib.sam import (add_readgroup_to_sam, merge_sam, sort_bam_sam, bam2sam,
                        sam2bam)

def parse_options():
    'It parses the command line arguments'
    parser = OptionParser()
    parser.add_option('-d', '--work_dir', dest='work_dir',
                    help='input sequence dir')
    parser.add_option('-o', '--outbam', dest='output', help='Output bam')
    parser.add_option('-r', '--reference', dest='reference',
                      help='fasta reference file')
    return parser

def set_parameters():
    '''It sets the parameters for the script.'''

    parser  = parse_options()
    options = parser.parse_args()[0]

    if options.work_dir is None:
        parser.error('work_dirwith bams is mandatory')
    else:
        work_dir = options.work_dir

    if options.output is None:
        output = 'out.bam'
    else:
        output = options.output
    if options.reference is None:
        parser.error('Reference is needed')
    else:
        reference = open(options.reference)

    return work_dir, output, reference

def create_header_from_readgroup(readgroups):
    'It creates a bam header from readgroup list'
    header = []
    for readgroup in readgroups:
        head_line = '@RG    ID:%s LB:%s SM:%s' % (readgroup, readgroup,
                                                  readgroup)
        header.append(head_line)
    return  "\n".join(header)

def add_readgroup_to_bams(work_dir, output_dir):
    'it adds readgroupto bams and return added reaadgroups'
    #add to each of the bams the readgroup_tag
    for bam in os.listdir(work_dir):
        if bam.endswith('.bam'):
            #get the readgroup from the name:
            prefix = bam.split('.')[0]
            readgroup = re.sub('lib_*', '', prefix)

            sam = open(os.path.join(output_dir, prefix + '.sam'), 'w')
            temp_sam = NamedTemporaryFile(suffix='.sam')

            bam2sam(os.path.join(work_dir, bam), temp_sam.name)
#            bamsam_converter(os.path.join(work_dir, bam), temp_sam.name)

            add_readgroup_to_sam(temp_sam, readgroup, sam)

            # close and remove temporal stuff
            sam.close()
            temp_sam.close()

def get_opened_sams_from_dir(dir_):
    'It gets all sams from dir'
    sams = []
    for file_ in os.listdir(dir_):
        if file_.endswith('.sam'):
            sams.append(open(os.path.join(dir_, file_)))
    return sams

def main():
    'The script itself'
    #set parameters
    work_dir, output, reference = set_parameters()

    # make a working tempfir
    temp_dir = NamedTemporaryDir().name
    temp_dir = "%s/tmp" % work_dir

    # add readgroup tag to each alignment in bam
    add_readgroup_to_bams(work_dir, temp_dir)

    # Prepare files to merge
    sams = get_opened_sams_from_dir(temp_dir)
    temp_sam = NamedTemporaryFile()

    # merge all the sam in one
    merge_sam(sams, temp_sam, reference)

    # Convert sam into a bam,(Temporary)
    temp_bam = NamedTemporaryFile(suffix='.bam')
    sam2bam(temp_sam.name, temp_bam.name)

    # finally we need to order the bam
    sort_bam_sam(temp_bam.name, output)

    # and make and index of the bam
    call(['samtools', 'index', output], raise_on_error=True)

    #temp_dir.close()

if __name__ == '__main__':
    main()
