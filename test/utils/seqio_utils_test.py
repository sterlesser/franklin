'''
Created on 2009 uzt 28

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


import unittest
import StringIO, tempfile

from franklin.seq.seqs import SeqWithQuality, Seq
from franklin.seq.readers import seqs_in_file
from franklin.seq.writers import  write_seqs_in_file
from franklin.utils.seqio_utils import cat, seqio

from Bio.SeqFeature import FeatureLocation
from franklin.seq.seqs import SeqFeature



class TestSeqio(unittest.TestCase):
    'It test the converter'
    @staticmethod
    def test_fastq_to_fasta_qual():
        'It tests the conversion from fastq to fasta'
        fcontent  = '@seq1\n'
        fcontent += 'CCCT\n'
        fcontent += '+\n'
        fcontent += ';;3;\n'
        fcontent += '@SRR001666.1\n'
        fcontent += 'GTTGC\n'
        fcontent += '+\n'
        fcontent += ';;;;;\n'
        fhand = StringIO.StringIO(fcontent)

        out_seq_fhand = tempfile.NamedTemporaryFile(suffix='.fasta')
        out_qual_fhand = tempfile.NamedTemporaryFile(suffix='.qual')
        seqio(in_seq_fhand=fhand, in_format='fastq',
              out_seq_fhand=out_seq_fhand, out_qual_fhand=out_qual_fhand,
              out_format='fasta')
        result = '>seq1\nCCCT\n>SRR001666.1\nGTTGC\n'
        assert open(out_seq_fhand.name).read() == result

        qual = '>seq1\n26 26 18 26\n>SRR001666.1\n26 26 26 26 26\n'
        assert open(out_qual_fhand.name).read() == qual

    @staticmethod
    def test_fastq_to_fastq_solexa():
        'It tests the conversion using the Biopython convert function'
        fcontent  = '@seq1\n'
        fcontent += 'CCCT\n'
        fcontent += '+\n'
        fcontent += ';;3;\n'
        fcontent += '@SRR001666.1\n'
        fcontent += 'GTTGC\n'
        fcontent += '+\n'
        fcontent += ';;;;;\n'
        fhand = StringIO.StringIO(fcontent)

        out_seq_fhand = StringIO.StringIO()
        seqio(in_seq_fhand=fhand, in_format='fastq',
              out_seq_fhand=out_seq_fhand, out_format='fastq-solexa')
        result = '@seq1\nCCCT\n+\nZZRZ\n@SRR001666.1\nGTTGC\n+\nZZZZZ\n'
        assert out_seq_fhand.getvalue() == result


class TestCat(unittest.TestCase):
    'It tests the sequence converter'
    @staticmethod
    def test_cat():
        'It tests the cat function'
        inh1 = StringIO.StringIO('>seq1\nACTG\n')
        inh2 = StringIO.StringIO('>seq2\nGTCA\n')
        outh = StringIO.StringIO()
        cat(infiles=[inh1, inh2], outfile=outh)
        assert outh.getvalue() == '>seq1\nACTG\n>seq2\nGTCA\n'

        #it works also with None Values
        outh = StringIO.StringIO()
        cat(infiles=[None, None], outfile=outh)
        assert outh.getvalue() == ''

class TestReprIn_Out(unittest.TestCase):
    'Tests repr write and read functions'
    @staticmethod
    def test_repr():
        'It test seqs in file read and write with repr'
        fhand = tempfile.NamedTemporaryFile(suffix='.repr')
        seq1 = SeqWithQuality(id='seqid', name='seqname',
                         description='seqdescription', seq=Seq('ATGAT'))
        seq1.letter_annotations["phred_quality"] = [40, 40, 38, 30, 30]
        seq1.annotations['source'] = 'ara1'

        seqfeature = SeqFeature(location=FeatureLocation(5, 8),
                                type='orthologs',
                                qualifiers={'arabidposys':['arab1', 'arab2']})
        seq1.features.append(seqfeature)
        write_seqs_in_file(seqs=[seq1], seq_fhand=fhand, format='repr')
        seqs = seqs_in_file(fhand)
        seq0 = seqs.next()
        assert repr(seq0) == repr(seq1)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
