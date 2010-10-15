'''
Created on 16/02/2010

@author: jose
'''
# Copyright 2009 Jose Blanca, Peio Ziarsolo, COMAV-Univ. Politecnica Valencia
# This file is part of franklin.
# franklin is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# franklin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR  PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with franklin. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

from collections import defaultdict
from copy import copy
import math

try:
    import pysam
except ImportError:
    pass

from Bio.SeqFeature import FeatureLocation
from Bio.Restriction import Analysis, CommOnly, RestrictionBatch
from franklin.seq.seqs import SeqFeature, get_seq_name
from franklin.utils.misc_utils import get_fhand
from franklin.sam import create_bam_index, get_read_group_info

DELETION_ALLELE = '-'
N_ALLLELES = ('n', '?')

SNP = 0
INSERTION = 1
DELETION = 2
INVARIANT = 3
INDEL = 4
COMPLEX = 5
TRANSITION = 6
TRANSVERSION = 7
UNKNOWN = 8

SNV_TYPES = {SNP:'SNP', INSERTION:'insertion', DELETION:'deletion',
             INVARIANT:'invariant', INDEL:'indel', COMPLEX:'complex',
             TRANSITION:'transition', TRANSVERSION:'transversion',
             UNKNOWN:'unknown'}

COMMON_ENZYMES = ['EcoRI', 'SmaI', 'BamHI', 'AluI', 'BglII',
                  'SalI', 'BglI', 'ClaI', 'TaqI',
                  'PstI', 'PvuII', 'HindIII', 'EcoRV',
                  'HaeIII', 'KpnI', 'ScaI',
                  'HinfI', 'DraI', 'ApaI', 'BstEII', 'ZraI', 'BanI', 'Asp718I']

def _qualities_to_phred(quality):
    'It transforms a qual chrs into a phred quality'
    if quality is None:
        return None
    phred_qual = []
    for char in quality:
        phred_qual.append(ord(char) - 33)
    if quality[0] == 93:  #the character used for unknown qualities
        phred_qual = None
    else:
        phred_qual = sum(phred_qual) / len(phred_qual)
    return phred_qual

def _get_allele_from_read(aligned_read, index):
    'It returns allele, quality, is_reverse'
    allele = aligned_read.seq[index].upper()
    if aligned_read.qual:
        qual = _qualities_to_phred(aligned_read.qual[index])
    else:
        qual = None
    return allele, qual, bool(aligned_read.is_reverse)

def _add_allele(alleles, allele, kind, read_name, read_group, is_reverse, qual,
                mapping_quality, readgroup_info):
    'It adds one allele to the alleles dict'
    key = (allele, kind)
    if key not in alleles:
        alleles[key] = {'read_groups':[], 'orientations':[],
                        'qualities':[], 'mapping_qualities':[]}
    allele_info = alleles[key]
    allele_info['read_groups'].append(read_group)
    allele_info['orientations'].append(not(is_reverse))
    allele_info['qualities'].append(qual)
    allele_info['mapping_qualities'].append(mapping_quality)

def _normalize_read_edge_conf(read_edge_conf):
    'It returns a dict with all valid keys'
    platforms = ('454', 'sanger', 'illumina')
    if read_edge_conf is None:
        read_edge_conf = {}
    for platform in platforms:
        if platform not in read_edge_conf:
            read_edge_conf[platform] = (None, None)
    return read_edge_conf

def _snvs_in_bam(bam, reference, min_quality, default_sanger_quality,
                 min_mapq, min_num_alleles, read_edge_conf=None):
    'It yields the snv information for every snv in the given reference'

    min_num_alleles = int(min_num_alleles)

    read_groups_info = get_read_group_info(bam)

    current_deletions = {}
    reference_id = get_seq_name(reference)
    reference_seq = reference.seq
    reference_len = len(reference_seq)
    for column in bam.pileup(reference=reference_id):
        alleles = {}
        ref_pos = column.pos

        if ref_pos >= reference_len:
            continue
        ref_id = bam.getrname(column.tid)
        ref_allele = reference_seq[ref_pos].upper()
        for pileup_read in column.pileups:
            #for each read in the column we add its allele to the alleles dict
            aligned_read = pileup_read.alignment

            read_mapping_qual = aligned_read.mapq
            #We ignore the reads that are likely to be missaligned
            if read_mapping_qual < min_mapq:
                continue

            read_group = aligned_read.opt('RG')
            read_name = aligned_read.qname
            platform = read_groups_info[read_group]['PL']

            read_pos = pileup_read.qpos
            edge_left, edge_right = read_edge_conf[platform]

            #if we're in the edge region to be ignored we continue to the next
            #read, because there's no allele to add for this one.
            if ((edge_left  is not None and edge_left >= read_pos) or
                (edge_right is not None and edge_right <= read_pos)):
                continue

            allele = None
            qual = None
            is_reverse = None
            kind = None
            start = None
            end = None
            #which is the allele for this read in this position?
            if read_name in current_deletions:
                current_deletion = current_deletions[read_name]
                if current_deletion[1]:
                    allele = DELETION_ALLELE * current_deletion[0]
                    #in the deletion case the quality is the lowest of the
                    #bases that embrace the deletion
                    if aligned_read.qual:
                        qual0 = aligned_read.qual[read_pos - 1]
                        qual0 = _qualities_to_phred(qual0)
                        qual1 = aligned_read.qual[read_pos]
                        qual1 = _qualities_to_phred(qual1)
                        qual = min((qual0, qual1))
                    else:
                        qual = None
                    is_reverse = bool(aligned_read.is_reverse)
                    kind = DELETION
                    current_deletion[1] = False #we have returned it already
                #we count how many positions should be skip until this read
                #has now deletion again
                current_deletion[0] -= 1
                if current_deletion[0] == 0:
                    del current_deletions[read_name]
            else:
                allele, qual, is_reverse = _get_allele_from_read(aligned_read,
                                                                 read_pos)
                if allele != ref_allele:
                    kind = SNP
                else:
                    kind = INVARIANT

            #is there a deletion in the next column?
            indel_length = pileup_read.indel
            if indel_length < 0:
                #deletion length, return this at the first opportunity
                current_deletions[read_name] = [-indel_length, True]

            if allele is not None:
                _add_allele(alleles, allele, kind, read_name, read_group,
                            is_reverse, qual, read_mapping_qual,
                            read_groups_info)

            #is there an insertion after this column
            if indel_length > 0:
                start = read_pos + 1
                end = start + indel_length

                allele, qual, is_reverse = _get_allele_from_read(aligned_read,
                                                              slice(start, end))
                kind = INSERTION
                _add_allele(alleles, allele, kind, read_name, read_group,
                            is_reverse, qual, read_mapping_qual,
                            read_groups_info)

        #remove N
        _remove_alleles_n(alleles)

        #add default sanger qualities to the sanger reads with no quality
        _add_default_sanger_quality(alleles, default_sanger_quality,
                                    read_groups_info)

        #remove bad quality alleles
        _remove_bad_quality_alleles(alleles, min_quality)

        #if there are a min_num number of alleles requested and there are more
        #alleles than that
        #OR
        #there is some allele different than invariant
        #a variation is yield
        if not alleles:
            continue
        if (len(alleles) > min_num_alleles or
            (min_num_alleles == 1 and alleles.keys()[0][1] != INVARIANT) or
            (min_num_alleles > 1 and len(alleles) >= min_num_alleles)):
            yield {'ref_name':ref_id,
                   'ref_position':ref_pos,
                   'reference_allele':ref_allele,
                   'alleles':alleles,
                   'read_groups':read_groups_info}

def _add_default_sanger_quality(alleles, default_sanger_quality,
                                read_groups_info):
    'It adds default sanger qualities to the sanger reads with no quality'

    for allele_info in alleles.values():
        for index, (qual, rg) in enumerate(zip(allele_info['qualities'],
                                             allele_info['read_groups'])):
            try:
                if qual is None and read_groups_info[rg]['PL'] == 'sanger':
                    allele_info['qualities'][index] = default_sanger_quality
            except KeyError:
                if 'PL' not in read_groups_info[rg]:
                    msg = 'The bam file has no platforms for the read groups'
                    raise KeyError(msg)
                else:
                    raise

def _remove_alleles_n(alleles):
    'It deletes the aleles that are N'
    for allele in alleles:
        if allele[0] in N_ALLLELES:
            del alleles[allele]

def _remove_bad_quality_alleles(alleles, min_quality):
    'It adds the quality to the alleles dict and it removes the bad alleles'

    orientations_independent = False
    if orientations_independent:
        qual_calculator = _calculate_allele_quality_oriented
    else:
        qual_calculator = _calculate_allele_quality
    for allele, allele_info in alleles.items():
        qual = qual_calculator(allele_info)
        allele_info['quality'] = qual
        if qual < min_quality:
            del alleles[allele]

def _calculate_allele_quality(allele_info):
    'It returns the quality for the given allele'

    #we sort all qualities
    quals = allele_info['qualities'][:]
    quals.sort(lambda x, y: int(y - x))

    total_qual = 0
    if quals:
        total_qual += quals[0]
        if len(quals) > 1:
            total_qual += quals[1] / 4.0
            if len(quals) > 2:
                total_qual += quals[2] / 4.0
    return total_qual

def _calculate_allele_quality_oriented(allele_info):
    '''It returns the quality for the given allele
    It assumes that reads with different orientations are independent'''
    #we gather all qualities for independent groups
    quals = defaultdict(list)
    for qual, orientation in zip(allele_info['qualities'],
                                 allele_info['orientations']):
        quals[orientation].append(qual)

    #we sort all qualities
    for independent_quals in quals.values():
        independent_quals.sort(lambda x, y: int(y - x))

    total_qual = 0
    for independent_quals in quals.values():
        if independent_quals:
            total_qual += independent_quals[0]
            if len(independent_quals) > 1:
                total_qual += independent_quals[1] / 4.0
                if len(independent_quals) > 2:
                    total_qual += independent_quals[2] / 4.0
    return total_qual

def _root_mean_square(numbers):
    'It returns the root mean square for the given numbers'
    power2 = lambda x: math.pow(x, 2)
    return math.sqrt(sum(map(power2, numbers)) / len(numbers))

def _summarize_snv(snv):
    'It returns an snv with an smaller memory footprint'
    used_read_groups = set()
    for allele_info in snv['alleles'].values():
        #the read_groups list to a count dict
        rg_count = {}
        for read_group in allele_info['read_groups']:
            if read_group not in rg_count:
                rg_count[read_group] = 0
            rg_count[read_group] += 1
            used_read_groups.add(read_group)
        allele_info['read_groups'] = rg_count

    #we calculate a couple of parameters that summarize the quality
    for kind in ('mapping_qualities', 'qualities'):
        quals = []
        for allele_info in snv['alleles'].values():
            quals.extend(allele_info[kind])
        if kind == 'mapping_qualities':
            kind = 'mapping_quality'
        if kind == 'qualities':
            kind = 'quality'
        snv[kind] = _root_mean_square(quals) if quals else None

    for allele_info in snv['alleles'].values():
        #we remove some extra quality info
        del allele_info['mapping_qualities']
        del allele_info['qualities']
        del allele_info['orientations']

    #we remove from the read_groups the ones not used in this snv
    new_read_groups = {}
    for read_group, info in snv['read_groups'].items():
        if read_group in used_read_groups:
            new_read_groups[read_group] = info

    snv['read_groups'] = new_read_groups

    return snv

def create_snv_annotator(bam_fhand, min_quality=45, default_sanger_quality=25,
                         min_mapq=15, min_num_alleles=1, read_edge_conf=None):
    'It creates an annotator capable of annotating the snvs in a SeqRecord'

    #the bam should have an index, does the index exists?
    bam_fhand = get_fhand(bam_fhand)
    create_bam_index(bam_fpath=bam_fhand.name)
    read_edge_conf = _normalize_read_edge_conf(read_edge_conf)

    bam = pysam.Samfile(bam_fhand.name, 'rb')

    def annotate_snps(sequence):
        'It annotates the snvs found in the sequence'
        for snv in _snvs_in_bam(bam, reference=sequence,
                                min_quality=min_quality,
                                default_sanger_quality=default_sanger_quality,
                                min_mapq=min_mapq,
                                min_num_alleles=min_num_alleles,
                                read_edge_conf=read_edge_conf):
            snv = _summarize_snv(snv)
            location = snv['ref_position']
            type_ = 'snv'
            qualifiers = {'alleles':snv['alleles'],
                          'reference_allele':snv['reference_allele'],
                          'read_groups':snv['read_groups'],
                          'mapping_quality': snv['mapping_quality'],
                          'quality': snv['quality']}
            feat = SeqFeature(location=FeatureLocation(location, location),
                              type=type_,
                              qualifiers=qualifiers)
            sequence.features.append(feat)
        return sequence
    return annotate_snps

def calculate_snv_kind(feature, detailed=False):
    'It returns the snv kind for the given feature'
    snv_kind = INVARIANT
    alleles = feature.qualifiers['alleles']
    for allele in alleles.keys():
        allele_kind = allele[1]
        snv_kind = _calculate_kind(allele_kind, snv_kind)

    if snv_kind == SNP and detailed:
        snv_kind = _guess_snp_kind(alleles)

    return snv_kind

def _al_type(allele):
    'I guesses the type of the allele'
    allele = allele.upper()
    if allele in ('A', 'G'):
        return 'purine'
    elif allele in ('T', 'C'):
        return 'pirimidine'
    return UNKNOWN

def _guess_snp_kind(alleles):
    'It guesses the type of the snp'
    alleles = alleles.keys()
    # if we take into account the reference to decide if there is a variation
    if len(alleles) < 2:
        return UNKNOWN
    al0 = _al_type(alleles[0][0])
    al1 = _al_type(alleles[1][0])
    if al0 == UNKNOWN or al1 == UNKNOWN:
        snv_kind = UNKNOWN
    elif al0 == al1:
        snv_kind = TRANSITION
    else:
        snv_kind = TRANSVERSION
    return snv_kind

def _calculate_kind(kind1, kind2):
    'It calculates the result of the union of two kinds'
    if kind1 == kind2:
        return kind1
    else:
        if kind1 is INVARIANT:
            return kind2
        elif kind2 is INVARIANT:
            return kind1
        elif kind1 in [SNP, COMPLEX] or kind2 in [SNP, COMPLEX]:
            return COMPLEX
        else:
            return INDEL

def _cmp_by_read_num(allele1, allele2):
    'cmp by the number of reads for each allele'
    return len(allele2['read_names']) - len(allele1['read_names'])

def sorted_alleles(feature):
    'It returns the alleles sorted by number of reads'
    #from dict to list
    alleles = feature.qualifiers['alleles']
    alleles_list = []
    for allele, allele_info in alleles.items():
        allele_info = copy(allele_info)
        allele_info['seq'] = allele[0]
        allele_info['kind'] = allele[1]
        alleles_list.append(allele_info)
    return sorted(alleles_list, _cmp_by_read_num)

def snvs_in_window(snv, snvs, window):
    'it gets all the snvs  in a window taking a snv as reference'
    num_of_snvs = 0
    location = int(str(snv.location.start))
    left_margin = location - (window / 2)
    rigth_margin = location + (window / 2)
    for snv in snvs:
        location = int(str(snv.location.start))
        if location > left_margin and location < rigth_margin:
            num_of_snvs += 1
    return num_of_snvs

def _get_group(read_group, group_kind, read_groups):
    'It returns the group (lb, rg, sm) for the given rg and group_kind'
    if group_kind:
        if group_kind == 'read_groups':
            return read_group
        else:
            group_kind = group_kind.lower()
            if group_kind in ('lb', 'library', 'libraries'):
                group_kind = 'LB'
            elif group_kind in ('sm', 'sample', 'samples'):
                group_kind = 'SM'
            elif group_kind in ('pl', 'platform', 'platforms'):
                group_kind = 'PL'
            return read_groups[read_group][group_kind]

def _allele_count(allele, alleles, read_groups=None,
                  groups=None, group_kind=None):
    'It returns the number of reads for the given allele'

    counts = []
    for read_group, count in alleles[allele]['read_groups'].items():
        #do we have to count this read_group?
        group = _get_group(read_group, group_kind, read_groups)
        if not groups or groups and group in groups:
            counts.append(count)
    return sum(counts)

def calculate_maf_frequency(feature, groups=None, group_kind=None):
    'It returns the most frequent allele frequency'

    alleles = feature.qualifiers['alleles']
    read_groups = feature.qualifiers['read_groups']

    major_number_reads = None
    total_number_reads = 0
    for allele in alleles:
        number_reads = _allele_count(allele, alleles, read_groups, groups,
                                     group_kind)
        if major_number_reads is None or major_number_reads < number_reads:
            major_number_reads = number_reads
        total_number_reads += number_reads
    if not total_number_reads:
        return None
    return major_number_reads / total_number_reads

def calculate_snv_variability(sequence):
    'It returns the number of snv for every 100 pb'
    n_snvs = sum(1 for snv in sequence.get_features(kind='snv'))
    return n_snvs / len(sequence)

def calculate_cap_enzymes(feature, sequence, all_enzymes=False):
    '''Given an snv feature and a sequence it returns the list of restriction
    enzymes that distinguish between their alleles.'''

    if 'cap_enzymes' in feature.qualifiers:
        return feature.qualifiers['cap_enzymes']

    #which alleles do we have?
    alleles = set()
    for allele in feature.qualifiers['alleles'].keys():
        alleles.add(repr((allele[0], allele[1])))
    #for every pair of different alleles we have to look for differences in
    #their restriction maps
    enzymes = set()
    alleles = list(alleles)
    reference = sequence
    location = int(str(feature.location.start))
    for i_index in range(len(alleles)):
        for j_index in range(i_index, len(alleles)):
            if i_index == j_index:
                continue
            allelei = eval(alleles[i_index])
            allelei = {'allele':allelei[0], 'kind':allelei[1]}
            allelej = eval(alleles[j_index])
            allelej = {'allele':allelej[0], 'kind':allelej[1]}
            i_j_enzymes = _cap_enzymes_between_alleles(allelei, allelej,
                                                       reference, location,
                                                       all_enzymes)
            enzymes = enzymes.union(i_j_enzymes)

    enzymes = [str(enzyme) for enzyme in enzymes]
    feature.qualifiers['cap_enzymes'] = enzymes
    return enzymes

def _cap_enzymes_between_alleles(allele1, allele2, reference, location,
                                 all_enzymes=False):
    '''It looks in the enzymes that differenciate the given alleles.

    It returns a set.
    '''
    kind1 = allele1['kind']
    kind2 = allele2['kind']
    allele1 = allele1['allele']
    allele2 = allele2['allele']

    #we have to build the two sequences
    if all_enzymes:
        restriction_batch = CommOnly
    else:
        restriction_batch = RestrictionBatch(COMMON_ENZYMES)

    seq1 = create_alleles('seq1', allele1, kind1, reference, location)
    seq2 = create_alleles('seq2', allele2, kind2, reference, location)

    anal1 = Analysis(restriction_batch, seq1, linear=True)
    enzymes1 = set(anal1.with_sites().keys())
    anal1 = Analysis(restriction_batch, seq2, linear=True)
    enzymes2 = set(anal1.with_sites().keys())

    enzymes = set(enzymes1).symmetric_difference(set(enzymes2))

    return enzymes

def create_alleles(name, allele, kind, ref, loc):
    'The returns the sequence for the given allele'
    sseq = ref.seq
    if kind == INVARIANT:
        seq = sseq
    elif kind == SNP:
        seq = sseq[0:loc] + allele + sseq[loc + 1:]
    elif kind == DELETION:
        seq = sseq[0:loc + 1] + sseq[loc + len(allele) + 1:]
    elif kind == INSERTION:
        seq = sseq[0:loc] + allele + sseq[loc:]
    return seq


def variable_in_groupping(group_kind, feature, groups, in_union=False,
                           in_all_groups=True):
    'It looks if the given snv is variable for the given groups'

    alleles = _get_alleles_for_group(feature.qualifiers['alleles'],
                                     groups, group_kind,
                                     feature.qualifiers['read_groups'])
    if in_union:
        alleles = _aggregate_alleles(alleles)

    variable_in_read_groups_ = []
    for allele_list in alleles.values():
        variable_in_read_groups_.append(True if len(allele_list) > 1 else False)

    #For the case in which there are no alleles
    if not variable_in_read_groups_:
        return False

    if in_all_groups:
        return all(variable_in_read_groups_)
    else:
        return any(variable_in_read_groups_)

def _aggregate_alleles(alleles):
    'It joins all alleles for the read groups into one'
    aggregate = set()
    for allele_list in alleles.values():
        aggregate = aggregate.union(allele_list)
    return {None: aggregate}

def _get_alleles_for_group(alleles, groups, group_kind='read_groups',
                           read_groups=None):
    '''It gets the alleles from the given items of type:key, separated by items.
    For example, if you give key rg and items rg1, rg2, it will return
    alleles separated in rg1 and rg2 '''

    alleles_for_groups = {}
    for allele, alleles_info in alleles.items():
        for read_group in alleles_info['read_groups']:
            group = _get_group(read_group, group_kind, read_groups)
            if group not in groups:
                continue
            if not group in alleles_for_groups:
                alleles_for_groups[group] = set()
            alleles_for_groups[group].add(allele)
    return alleles_for_groups
