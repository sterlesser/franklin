'''
Created on 2009 mar 25

@author: peio
'''
import unittest
from biolib.SeqVariation import CONFIG, SeqVariation, seqvariations_in_alignment
from biolib.contig import Contig
from test.test_utils import SeqRecord

class SeqVariationConfig(unittest.TestCase):
    '''Here we will check if the SeqVariation module can be configured.
    '''
    @staticmethod
    def test_config():
        '''It checks that we can configure the module.'''
        assert isinstance(CONFIG.min_num_of_reads, int)
        assert isinstance(CONFIG.only_snp, bool)
        indel_char = CONFIG.indel_char
        assert isinstance(indel_char, str)
        assert len(indel_char) == 1

class SeqVariationTest(unittest.TestCase):
    '''Here we will check if the SeqVariation module works as it should.

    Is the support for snps and indels.
    '''
    @staticmethod
    def test_init():
        '''It tests the init'''
        snp = SeqVariation(name='a snp', location=20,
                           alignment='some_contig_instance',
                           alleles={'A':2, 'T':3})
        assert snp.name == 'a snp'
        assert snp.location == 20
        assert snp.alignment == 'some_contig_instance'
        assert len(snp.alleles) == 2

        #a simple init
        snp = SeqVariation(alleles={'A':2, 'T':3})
        assert len(snp.alleles) == 2

        #some alleles are removed due to the min_number_of_reads
        CONFIG.min_num_of_reads = 3
        snp = SeqVariation(alleles={'A':2, 'T':3})
        assert len(snp.alleles) == 1

        #some alleles are removed due to only_snps
        CONFIG.only_snp = True
        indel = CONFIG.indel_char
        snp = SeqVariation(alleles={'A':3, indel:3})
        assert len(snp.alleles) == 1
        CONFIG.only_snp = False

    @staticmethod
    def test_kind():
        '''it checks that we can get the kind of variation.'''
        inchar = CONFIG.indel_char
        
        seq_var = SeqVariation(alleles={'A':3, inchar:3})
        assert seq_var.is_indel()
        
        seq_var = SeqVariation(alleles={'AA':3, inchar * 2:3})
        assert seq_var.is_indel()
        
        seq_var = SeqVariation(alleles={'AA' + inchar :3, inchar * 3:3})
        assert seq_var.is_complex()
        
        seq_var = SeqVariation(alleles={'A':3, 'T':4})
        assert seq_var.is_snp()
        
        seq_var = SeqVariation(alleles={'A':3, 'T':4, inchar:3})
        assert seq_var.is_complex()
        
        seq_var = SeqVariation(alleles={'A' + inchar + 'A':3,
                                        'A' + inchar * 2 :4})
        assert seq_var.is_complex()

class VariationGeneratorTest(unittest.TestCase):
    '''It test if we can get the variations'''
    @staticmethod
    def test_seq_variation_generator():
        '''It checks if we can get the variations.''' 
        seqs = [SeqRecord('aga'), SeqRecord('ctc')]
        contig = Contig(sequences = seqs)

        for seqvar in seqvariations_in_alignment(contig):
            if CONFIG.indel_char in seqvar:
                print seqvar
                


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_SeqVariation_init']
    unittest.main()
