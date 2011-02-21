'''
Created on 2009 uzt 30

@author: peio
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

import unittest, os
from tempfile import NamedTemporaryFile

from franklin.pipelines.pipelines import  (configure_pipeline,
                                         seq_pipeline_runner,
                                         _pipeline_builder)
from franklin.utils.seqio_utils import seqs_in_file
from franklin.utils.cmd_utils import BLAST_TOOL
from franklin.seq.writers import SequenceWriter

from franklin.utils.misc_utils import DATA_DIR

ADAPTORS = '''>adaptor1
atcgatcgatagcatacgat
>adaptor2
atgcatcagatcgataaaga'''

EXPECTED = '''>seq1
ATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGATGCATGAATCGCATCGATCATCGCAGATCGACTGATCGATATGCATCAGATCGCGATCGGGGGGGGGGGGGGGGGGGGGGGGGGGGGAATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGATGCATGAA
>seq2
ATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGATGCATGAAATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGATGCATGAAATCAGCATGACTCATCGCATCGATCATCGCAGATCGACTGATCGATCGATCAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>seq3
ATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGATGCATGAAATCGATCTGATCTAGTCGATGTCTAGCTGAGCTACATAGCTAACGATCTAGTCTAGTCTATGATGCATCAGCTACGATGATCATGTCATGTCGATGTCTAGTCTAGTCTAGTGAGTCACTGACTAGATCATGACATCGANNNNNNNNNNNNNNNNNNNNNNTACTAGTC
>seq4
ATCGATCAGTCAGACTGACAGACTCAGATCAGATCAGCATCAGCATACGATACGCATCAGACTTCAGCATCGATCGACTAACGATCGATCGATCGACAGATCATCGATCATCGACGACTAGACGATCATCGATACGCAGACTCCGACTACGACTACGATAAGCAGACTACGAGATCAGCAGCATCAGCAGCANNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN
>seq5
ATGCATCAGATGCATGCATGACTACGACTACGATCAGCATCAGCGATCAGCATCGATACGATCATCGACTGCATCGATGAATCGATCAGTCAGACTGACAGACTCAGATCAGATCAGCATCAGCATACGATACGCATCAGACTTCAGCATCGATCGACTAATCGATCAGTCAGACTGACAGACTCAGATCAGATCAGCATCAGCATACGATACGCATCAGACTTCAGCATCGATCGACTA
>seq6
AACCGTTTGACTTACGATATTTGCCCATTGTGATTCTAGTCGATTTGCATAACGTGTACGTATCGGTATTGTGACTGATTCGATGCTATTGCAAACAGTTTTGATTGTGTGATCGTGATGCATGCTAGTCTGATCGAGTCTGATCGTAGTCTAGTCGTAGTCGATGTCGATTTATCAGTAGTCGATGCTAGTCTAGTCTAGTCTACTAGTCTAGTCATGCTAGTCGAGTCGAT
'''

class PipelineTests(unittest.TestCase):
    'It test pipeline related functions'

    def test_configure_pipeline(self):
        'It tests configure pipeline'
        pipeline = 'sanger_with_qual'
        if BLAST_TOOL == 'blast+':
            Univec = 'Univec+'
        else:
            Univec = 'Univec'
        configuration = {'remove_vectors': {'vectors':Univec},
                         'remove_adaptors':{'vectors':'hola'}}
        pipeline = configure_pipeline(pipeline, configuration)

        assert pipeline[1]['arguments']['vectors'] == 'hola'
        assert pipeline[3]['arguments']['vectors'] == Univec

        # Now it should fail because one of the arguments is Not set
        configuration = {'remove_vectors': {'vectors':Univec}}
        try:
            pipeline = configure_pipeline(pipeline, configuration)
            self.fail()
            #pylint: disable-msg=W0704
        except Exception:
            pass

    @staticmethod
    def test_pipeline_run():
        'It tests that the pipeline runs ok'
        pipeline = 'sanger_with_qual'

        fhand_adaptors = NamedTemporaryFile()
        fhand_adaptors.write(ADAPTORS)
        fhand_adaptors.flush()

        if BLAST_TOOL == 'blast+':
            arabidopsis_genes = 'arabidopsis_genes+'
        else:
            arabidopsis_genes = 'arabidopsis_genes'

        univec = os.path.join(DATA_DIR, 'blast', arabidopsis_genes)
        configuration = {'remove_vectors': {'vectors':univec},
                         'remove_adaptors':{'vectors':fhand_adaptors.name}}

        seq_fhand = open(os.path.join(DATA_DIR, 'seq.fasta'), 'r')
        qual_fhand = open(os.path.join(DATA_DIR, 'qual.fasta'), 'r')

        seq_iter = seqs_in_file(seq_fhand, qual_fhand)

        filtered_seq_iter = _pipeline_builder(pipeline, seq_iter, configuration)

        seq_list = list(filtered_seq_iter)
        assert 'ATCGCGAtcgggggg' in str(seq_list[0].seq)
        assert len(seq_list) == 6

    @staticmethod
    def test_seq_pipeline_run():
        'It tests that the pipeline runs ok'
        pipeline = 'sanger_with_qual'

        fhand_adaptors = NamedTemporaryFile()
        fhand_adaptors.write(ADAPTORS)
        fhand_adaptors.flush()
        if BLAST_TOOL == 'blast+':
            arabidopsis_genes = 'arabidopsis_genes+'
        else:
            arabidopsis_genes = 'arabidopsis_genes'
        univec = os.path.join(DATA_DIR, 'blast', arabidopsis_genes)
        configuration = {'remove_vectors': {'vectors':univec},
                         'remove_adaptors':{'vectors':fhand_adaptors.name}}

        in_fhands = {}
        in_fhands['in_seq'] = open(os.path.join(DATA_DIR, 'seq.fasta'), 'r')
        in_fhands['in_qual'] = open(os.path.join(DATA_DIR, 'qual.fasta'), 'r')


        out_seq_fhand = NamedTemporaryFile()
        out_qual_fhand = NamedTemporaryFile()
        writer = SequenceWriter(out_seq_fhand, qual_fhand=out_qual_fhand,
                                file_format='fasta')
        seq_pipeline_runner(pipeline, configuration, in_fhands,
                            writers={'seq':writer})
        result_seq = open(out_seq_fhand.name).read()
        assert result_seq.count('>') == 6

        #are we keeping the description?
        assert 'mdust' in result_seq

    def test_seq_pipeline_parallel_run(self):
        'It tests that the pipeline runs ok'
        pipeline = 'sanger_without_qual'

        fhand_adaptors = NamedTemporaryFile()
        fhand_adaptors.write(ADAPTORS)
        fhand_adaptors.flush()
        if BLAST_TOOL == 'blast+':
            arabidopsis_genes = 'arabidopsis_genes+'
        else:
            arabidopsis_genes = 'arabidopsis_genes'
        univec = os.path.join(DATA_DIR, 'blast', arabidopsis_genes)
        configuration = {'remove_vectors': {'vectors':univec},
                         'remove_adaptors':{'vectors':fhand_adaptors.name}}

        in_fhands = {}
        in_fhands['in_seq'] = open(os.path.join(DATA_DIR, 'seq.fasta'), 'r')
        out_fhand = NamedTemporaryFile()
        writer = SequenceWriter(out_fhand, file_format='fasta')
        writers = {'seq': writer}

        seq_pipeline_runner(pipeline, configuration, in_fhands,
                            processes=4, writers=writers)
        out_fhand = open(out_fhand.name, 'r')

        result_seq = out_fhand.read()
        assert result_seq.count('>') == 6
        #are we keeping the description?
        assert 'mdust' in result_seq

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
