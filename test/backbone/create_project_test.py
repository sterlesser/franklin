'''
Created on 26/01/2010

@author: jose
'''

# Copyright 2009 Jose Blanca, Peio Ziarsolo, COMAV-Univ. Politecnica Valencia
# This file is part of project.
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

import unittest, os.path
from os.path import join, exists

from franklin.utils.misc_utils import NamedTemporaryDir, DATA_DIR
from franklin.backbone.create_project import (create_project,
                                              create_configuration)
from franklin.backbone.analysis import BACKBONE_DIRECTORIES
from franklin.backbone.backbone_runner import do_analysis
from franklin.seq.readers import seqs_in_file
from tempfile import NamedTemporaryFile


READS_NOQUAL = '''>FM195262.1
TACGGCCGGGGTNNCNNANNNNGCATTCTCGCAGGGTCTTTCTACACTATTAGATAAGAT
GGATCCTTCTCAGAGAGTGAAGTTTGTTCAGGAAGTCAAGAAGGTTCTTGGATGATGATA
TGATACCAACACATCCAACACAATATGCGCATGCTACATGTTATTTTTCAAGTACATACA
TAGAAGGATATTGCTTGGCCTTGATTGATCATGTCTGATCTAAGTCGATCATTATTTTCT
TGAAACTTCCTTTCGGACGTGGTGCTATGGTTGATGAATTTGGATGTGTGCGTTCTGCCA
GGTGTAAGCCCAAAGGTTTATACAGACCGAGTTAAGGTTAGGAAGAGCACGAGTGAACTT
>FM187038.1
GCACGAGGGCCGTCGCAGAGGCGGTGCTGAGGTCGAGGGCCGGTCTTGGCAGGCCACAAC
AGCCCACTGGCTCGTTCCTCTTCCTGGGTCCGACTGGCGTGGGGAAAACTGAGCTGGCCA
AGGCCCTAGCCGAACAGCTGTTCGACGACGAGAACCTTCTTGTCCGCATCGACATGTCGG
AGGTCGCTCGCGATCTGGTCATGCAGGAGGTGAGGAGGCACTTCCGCCCTGAGCTGCTGA
ACCGTCTCGACGAGATCGTGATCTTCGATCCTCTGTCCCACGAGCAGCTGAGGAAGGTCG
CTCGCCTTCAGATGAAGGATGTGGCCGTCCGTCTTGCCGAANNNNNCATCGCTCTGGCTG
TGACCGANNNNNCATTGGACATCATCTTGTCTCTCTCTNNNNNNTCNNNNT
'''

READS_454 = '''@FKU4KFK07H6D2L
GGTTCAAGGTTTGAGAAAGGATGGGAAGAAGCCAAATGCCTACATTGCTGATACCACTACGGCAAATGCTCAAGTTCGGACGCTTGCTGAGACGGTGAGACTGGATGCAAGAACTAAGTTATTGAATAGTCAGCATGCATGATTAGGCTAAGCCGTAAGCATAGCATGACCCCATTGGCAAAGCTAGCATGATACGACATCATTATAGCGAGAGACGCATATCGAGAATGAGCGATCAGCACATGTCAGCGAGCTACTGACTATCATATATAGCGCAGAGACGACTAGCATCGAT
+
CCFFFFFCC;;;FFF99;HHIHECCHHIIIFHHEEEHHHHHHIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGGGGFFGGBCCGFFFGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
@FKU4KFK07IJEB9
AATTCCCTTTCCGGTGATCGCCTCTCCTAGCAATGATGCAGCAAAGCCGATCATAGCAACACGGCCGACGAAGAGTTCATTCTGCTTGGTAAAACCAATGCCACCAGAAGTCCCAAAAATTCCATCTTCAACCTTCTGCTTCGGCTTCTCAACCTTCTTGGGCGGGGCTTTAGTTCTGGATTTGAACACAGCAAGAGGGTGAAACCA
+
FFFFFFFFFFFFFFFFFFIIIIIIIIIIIIIIIIIIIIIIIIIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGGGGFFFFGGGGGGFFFFFFGAA@5557>55577G
@FKU4KFK07IMD9G
ACCCTTCTAGCAGTAGGAATGACTTGACCACCTCCTCTGTGGATTGTAGTAGTAGATGATGGCATCAGCGTGAAGCACCACATCACAAACTTCAAAACAGATGCCT
+
B>>>GGFFFFFFFFFGGGGHHHHHHHHHIIIIIIIIIIIIIIIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGCB;;;;BGFFFFFFF
@FKU4KFK07IE66H
ATGAACCGCAAAAGCTTGTATGCTGTATTGCCTTGATTTGGTTTCCAAGATTCTTCCCACATATATGATGATGATGATGATGTTAGGAGAGAGTGTAGCTGGAAACCGAGACTTTGGCTGGAGAAGCATGCGTATGATCATGACAGATAGC
+
FFFFFFFFG7777CGFFFFHHHHHHIHHHHHHHHHHHHHHH==?CCFFFFFFFGGCCCGFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGGGFFFFFFFFFFFFFGGGFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
'''
READS_ILL = '''@HWI-EAS59:3:1:5:1186#0/1
TGATACCACTGCTTANTCTGCGTTGNTACCA
+
BBBBCBAAABA=BB<%<C@?BBA@9%<B;A@
@HWI-EAS59:3:1:5:169#0/1
GTTGATACCACTGCTNACTCTGCG
+
BBA@ABBBBBBBAA9%;BBBBCAA
@HWI-EAS59:3:1:5:1467#0/1
AAGCAGTGGTATCAANGCAGAGTTCNGCTTC
+
B?@CBCBCBAACBB:%>BBBAC@B<%9>BBB
@HWI-EAS59:3:1:5:651#0/1
CATACCCAATTGCTTNAGATGGAT
+
AAAABBA@@B?7=@<%=<ABBA:A
@HWI-EAS59:3:1:5:1609#0/1
AGAGCATTGCTTTGANTTTAAAAACNCGGTT
+
?BA@B>CCCBCBB:<%>BCA@;A?<%?BBAB
@HWI-EAS59:3:1:5:247#0/1
GATGGATCCCAAGTTNTTGAGGAACNAGAGG
+
BBA?;BBBBBA3AB=%=BBB@A=A=%<><@?
'''
THREADS = False

class TestBackbone(unittest.TestCase):
    'It tests the backbone'

    @staticmethod
    def test_create_project():
        'We can create a project'
        test_dir = NamedTemporaryDir()
        settings_path = create_project(directory=test_dir.name,
                                       name='backbone')

        assert settings_path == join(test_dir.name,
                                'backbone', BACKBONE_DIRECTORIES['config_file'])
        settings = create_configuration(settings_path)
        assert settings['General_settings']['project_name'] == 'backbone'
        project_path = join(test_dir.name, 'backbone')
        assert settings['General_settings']['project_path'] == project_path
        os.chdir('/tmp')
        test_dir.close()

    @staticmethod
    def test_cleaning_analysis_lucy():
        'We can clean the reads'
        test_dir = NamedTemporaryDir()
        project_name = 'backbone'
        univec = os.path.join(DATA_DIR, 'blast', 'univec')
        configuration = {'Cleaning':{'vector_database':univec}}
        settings_path = create_project(directory=test_dir.name,
                                       name=project_name,
                                       configuration=configuration)

        project_dir = join(test_dir.name, project_name)
        #setup the original reads
        reads_dir = join(project_dir, 'reads')
        original_reads_dir = join(reads_dir, 'raw')
        os.mkdir(reads_dir)
        os.mkdir(original_reads_dir)

        os.makedirs(join(project_dir, 'config_data', 'lucy'))
        lucy_settings = join(project_dir, 'config_data', 'lucy', 'lucy.conf')
        luc_c = open(lucy_settings, 'w')
        luc_c.write(repr({'ps':{'vector_file':'tmp' , 'splice_file':'tmp'}}))
        luc_c.flush()

        #print original_reads_dir
        fpath_noqual = join(original_reads_dir, 'pl_sanger.lb_ps.fasta')
        fpath_454 = join(original_reads_dir, 'pl_454.lb_ps.sfastq')
        fpath_ill = join(original_reads_dir, 'pl_illumina.lb_psi.sfastq')
        open(fpath_noqual, 'w').write(READS_NOQUAL)
        open(fpath_454, 'w').write(READS_454)
        open(fpath_ill, 'w').write(READS_ILL)
        do_analysis(project_settings=settings_path, kind='clean_reads')
        cleaned_dir = join(project_dir, 'reads', 'cleaned')
        assert exists(cleaned_dir)

        cleaned_454 = join(cleaned_dir, os.path.basename(fpath_454))
        assert exists(cleaned_454)

        cleaned_noqual = join(cleaned_dir, os.path.basename(fpath_noqual))
        clean_seqs =  open(cleaned_noqual).read()
        assert clean_seqs.startswith('>FM195262.1\nGCATTCTCG')

    @staticmethod
    def test_cleaning_analysis():
        'We can clean the reads'
        test_dir = NamedTemporaryDir()
        project_name = 'backbone'
        project_dir = join(test_dir.name, project_name)
        adaptors_dir = join(project_dir, 'config_data', 'adaptors')
        adaptors_path_454 = join(adaptors_dir, '454_adaptors')
        words = ['^ATGAAC']
        univec = os.path.join(DATA_DIR, 'blast', 'univec')
        configuration = {'Cleaning':{'vector_database':univec,
                                     'adaptors_file_454':adaptors_path_454,
                                     'short_adaptors_454':words,
                                     'edge_removal':{'454_left':3,
                                                     '454_right':3}},
                         'General_settings':{'threads':THREADS}}

        settings_path = create_project(directory=test_dir.name,
                                       name=project_name,
                                       configuration=configuration)

        #setup the original reads
        reads_dir = join(project_dir, 'reads')
        original_reads_dir = join(reads_dir, 'raw')
        os.mkdir(reads_dir)
        os.mkdir(original_reads_dir)

        os.makedirs(adaptors_dir)
        adap_fhand = open(adaptors_path_454, 'w')
        adap_fhand.write('''>smart_5_cds_primer_1
GGTTCAAGGTTTGAGAAAGGATGGGAAG\n>a_short_adaptor\nTTGATTTGGT\n''')
        adap_fhand.close()

        #print original_reads_dir
        fpath_454 = join(original_reads_dir, 'pl_454.lb_a.sfastq')
        fpath_ill = join(original_reads_dir, 'pl_illumina.lb_b.sfastq')
        open(fpath_454, 'w').write(READS_454)
        open(fpath_ill, 'w').write(READS_ILL)

        do_analysis(project_settings=settings_path, kind='clean_reads')
        cleaned_dir = join(project_dir, 'reads', 'cleaned')
        assert exists(cleaned_dir)
        cleaned_454 = join(cleaned_dir, os.path.basename(fpath_454))
        assert exists(cleaned_454)
        seqs = list(seqs_in_file(open(cleaned_454)))
        seq = seqs[0].seq
        # It means thar the adaptor has been removed
        assert 'GGTTCAAGGTTTGAGAAAGGATGGGAAG' not in seq
        seq = seqs[2].seq
        # It means that the starting word has been removed
        assert  seq.startswith('CAAGATTCTTCCCACAT')

        do_analysis(project_settings=settings_path, kind='read_stats')
        clean_stats_dir = join(cleaned_dir, 'stats')
        original_stats_dir = join(original_reads_dir, 'stats')
        assert exists(clean_stats_dir)
        assert exists(original_stats_dir)
        assert exists(join(clean_stats_dir, 'all.diff_qual_distrib.png'))
        assert exists(join(clean_stats_dir, 'pl_454.lb_a.general_stats.txt'))

        do_analysis(project_settings=settings_path,
                    kind='prepare_mira_assembly')
        assembly_input = join(project_dir, 'assembly', 'input')
        assert exists(assembly_input)
        mira_in_454 = join(assembly_input, 'backbone_in.454.fasta')
        mira_in_qul = join(assembly_input, 'backbone_in.454.fasta.qual')
        assert exists(mira_in_454)
        assert exists(mira_in_qul)

        do_analysis(project_settings=settings_path, kind='mira_assembly')
        assembly_dir = join(project_dir, 'assembly')
        singular_assembly_dir = sorted(os.listdir(assembly_dir))[0]
        assert exists(join(assembly_dir, singular_assembly_dir,
                                           'stderr.txt'))
        assem_result_dir = join(assembly_dir, 'result')
        assert exists(assem_result_dir)
        assert exists(join(assem_result_dir, 'info'))

        #mira does not do any contig
        result_dir = join(assembly_dir, 'result')
        open(join(result_dir, 'contigs.fasta'), 'w')
        open(join(result_dir, 'contigs.qual'), 'w')
        do_analysis(project_settings=settings_path,
                    kind='set_assembly_as_reference')
        os.chdir('/tmp')
        test_dir.close()


class ConfigurationTest(unittest.TestCase):
    'Tests for configirations'
    @staticmethod
    def test_create_configuration():
        'Test default config'
        fhand = NamedTemporaryFile()
        fhand.write('[Snvs]\nmin_num_alleles = 2\n[[edge_removal]]\n454_left=None')
        fhand.flush()
        config_fpath = fhand.name
        config = create_configuration(config_fpath)
        assert config['Snvs']['min_quality'] == 45

        #malformed
        fhand = NamedTemporaryFile()
        fhand.write('[blast]\n[[nr]]\nkind="nucl"\npath="path"\nspecies="all"')
        fhand.flush()
        config_fpath = fhand.name
        config = create_configuration(config_fpath)
        assert config['Snvs']['min_quality'] == 45

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'ConfigurationTest.test_create_configuration']
    unittest.main()
