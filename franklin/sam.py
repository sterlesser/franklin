'''
This library is used to manipulate the sam and bam files. You can merge bams and
add some xtra information to sams

Created on 05/01/2010

@author: peio
'''
import os, re

from franklin.utils.cmd_utils import call
from franklin.utils.seqio_utils import seqs_in_file

def guess_picard_path():
    'It returns the picard path using locate'
    a_picard_jar = 'SortSam.jar'
    cmd = ['locate', a_picard_jar]
    stdout = call(cmd, raise_on_error=True)[0]
    picard_path = None
    for line in stdout.splitlines():
        if a_picard_jar in line:
            picard_path = line.replace(a_picard_jar, '')
            picard_path = picard_path.strip()
            break
    if not picard_path:
        msg =  'Picard was not found in your system and it is required to '
        msg += 'process sam files'
        raise RuntimeError(msg)
    return picard_path

def bam2sam(bam_path, sam_path=None):
    '''It converts between bam and sam. It sampath is not given, it return
    sam content'''
    cmd = ['samtools', 'view', '-h', bam_path]
    if sam_path:
        cmd.extend(['-o', sam_path])
    sam = call(cmd, raise_on_error=True)
    return sam

def sam2bam(sam_path, bam_path):
    'It converts between bam and sam.'
    cmd = ['samtools', 'view', '-bth', '-o', bam_path, sam_path]
    call(cmd, raise_on_error=True)

def bamsam_converter(input_fhand, output_fhand, picard_path=None):
    'Converts between sam and bam'
    if picard_path is None:
        picard_path = guess_picard_path()
    picard_jar = os.path.join(picard_path, 'SamFormatConverter.jar')
    cmd = ['java', '-Xmx2g', '-jar', picard_jar, 'INPUT=' + input_fhand,
           'OUTPUT=' + output_fhand]
    call(cmd, raise_on_error=True)

def add_header_and_tags_to_sam(sam_fhand, new_sam_fhand):
    '''It adds tags to each of the reads of the alignments on the bam.
    It creates a new bam in other to avoid errors'''

    # first we write the headers
    sam_fhand.seek(0)
    for line in sam_fhand:
        line = line.strip()
        if not line:
            continue
        if line.startswith('@'):
            new_sam_fhand.write(line + '\n')

    # we add a new header. We take this information from the name of the file
    prefix = os.path.basename(sam_fhand.name)
    prefix = prefix.split('.')[:-1]

    rgid_ = []
    append_to_header = []
    for item in prefix:
        try:
            key, value = item.split('_', 1)
            if key.upper() not in ['LB', 'PL']:
                continue
        except ValueError:
            continue
        append_to_header.append('%s:%s' % (key.upper(), value))
        rgid_.append(value)
    rgid = "_".join(rgid_)

    # a proper sam with RG needs a SM key
    if not _check_tag_in_RG('SM', append_to_header):
        append_to_header.append('SM:%s' % rgid)


    new_sam_fhand.write('@RG\tID:%s\t' % rgid)
    new_sam_fhand.write("\t".join(append_to_header) + " \n")

    # now the alignments
    sam_fhand.seek(0)
    for line in sam_fhand:
        line = line.strip()
        if not line:
            continue
        if not line.startswith('@'):
            line = line + "\t" + 'RG:Z:%s' % rgid
            new_sam_fhand.write(line + '\n')
    new_sam_fhand.flush()

def _check_tag_in_RG(tag, tags_to_append):
    'It check if the given tag is in the tags to append'
    for tag_to_append in tags_to_append:
        key = tag_to_append.split()[0]
        if key.upper() == tag.upper():
            return True
    return False

def merge_sam(infiles, outfile, reference):
    'It merges a list of sam files'

    #first the reference part of the header
    ref_header = []
    for seq in seqs_in_file(reference):
        name   = seq.name
        length = len(seq)
        ref_header.append(['@SQ', 'SN:%s' % name, 'LN:%d' % length])

    #now the read groups
    headers = set()

    for input_ in infiles:
        input_.seek(0)
        for line in input_:
            line = line.strip()
            if line.startswith('@SQ'):
                continue
            elif line.startswith('@'):
                headers.add(tuple(line.split()))
            else:
                break

    #join and write both header parts
    ref_header.extend(headers)
    for header in ref_header:
        outfile.write('\t'.join(header))
        outfile.write('\n')

    #the non header parts
    for input_ in infiles:
        input_.seek(0)
        for line in input_:
            if line.startswith('@'):
                continue
            outfile.write(line)
    outfile.flush()

def sort_bam_sam(in_fhand, out_fhand, picard_path= None,
                 sort_method='coordinate'):
    'It sorts a bam file using picard'
    if picard_path is None:
        picard_path = guess_picard_path()
    picard_sort_jar = os.path.join(picard_path, 'SortSam.jar')
    cmd = ['java', '-Xmx2g', '-jar', picard_sort_jar, 'INPUT=' +  in_fhand,
           'OUTPUT=' + out_fhand, 'SORT_ORDER=' + sort_method]
    call(cmd, raise_on_error=True)

def _fix_non_mapped_reads(items):
    'Given a list with sam line it removes MAPQ from non-mapped reads'
    #is the read mapped?
    flag = int(items[1])
    if flag == 0:
        mapped = True
    elif flag in (20, 4):  #just a sohortcut
        mapped = False
    else:
        if bin(flag)[-3] == '1':
            mapped = False
        else:
            mapped = True
    if not mapped:
        #RNAME = *
        items[2] = '*'
        #POS = 0
        items[3] = '0'
        #MAPQ = 0
        items[4] = '0'
        #CIGAR = *
        items[5] = '*'

def _add_default_quality(items, sanger_read_groups, default_qual):
    'It adds the quality to the sanger reads that do not have it'
    rg_id = filter(lambda x: x.startswith('RG:Z:'), items)
    if rg_id:
        rg_id = rg_id[0].strip().replace('RG:Z:', '')
    else:
        msg = 'Read group is required to add default qualities'
        raise RuntimeError(msg)
    if rg_id not in sanger_read_groups:
        msg = 'Platform for read group %s is not sanger' % rg_id
        raise RuntimeError(msg)
    #here we set the default qual
    items[10] = default_qual * len(items[9])

def standardize_sam(in_fhand, out_fhand, default_sanger_quality,
                   add_def_qual=False, only_std_char=True,
                   fix_non_mapped=True):
    '''It adds the default qualities to the reads that do not have one and
    it makes sure that only ACTGN are used in the sam file reads.

    The quality should be given as a phred integer
    '''
    in_fhand.seek(0)
    sep = '\t'

    sanger_read_groups = set()
    default_qual = chr(int(default_sanger_quality) + 33)
    regex = re.compile(r'[^ACTGN]')
    for line in in_fhand:
        #it we're adding qualities we have to keep the read group info
        if add_def_qual and line[:3] == '@RG':
            items = line.split(sep)
            rg_id = None
            platform = None
            for item in items:
                if item.startswith('PL:'):
                    platform = item[3:].strip().lower()
                elif item.startswith('ID:'):
                    rg_id = item[3:].strip()
            if platform == 'sanger':
                sanger_read_groups.add(rg_id)
        elif line[0] == '@':
            pass
        else:
            items = line.split(sep)
            #quality replaced
            do_qual = add_def_qual and items[10] == '*'
            if do_qual or only_std_char:
                #we add default qualities to the reads with no quality
                if do_qual: #empty quality
                    _add_default_quality(items, sanger_read_groups,
                                         default_qual)
                #we change all seq characters to ACTGN
                if only_std_char:
                    text = items[9].upper()
                    items[9] = regex.sub('N', text)
                #we remove MAPQ from the non-mapped reads
                if fix_non_mapped:
                    _fix_non_mapped_reads(items)
                line = sep.join(items)
        out_fhand.write(line)

def create_bam_index(bam_fpath):
    'It creates an index of the bam if it does not exist'
    index_fpath = bam_fpath + '.bai'

    if os.path.exists(index_fpath):
        return
    cmd = ['samtools', 'index', bam_fpath]
    call(cmd, raise_on_error=True)





