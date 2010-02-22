'''This module represents the reduce part of our pipelines.

All writes share the same interface. The write method takes a SeqRecord and
appends the part that correspond to that sequence (It can be an annotation or a
feature) to the file.
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
import tempfile

from Bio import SeqIO
from franklin.seq.seqs import get_seq_name
from franklin.seq.readers import BIOPYTHON_FORMATS

class SequenceWriter(object):
    'It writes sequences one by one'
    def __init__(self, fhand, file_format, qual_fhand=None):
        'It inits the class'
        open(fhand.name, 'w')
        self._fhand = open(fhand.name, 'a')

        if qual_fhand is not None:
            open(qual_fhand.name, 'w')
            qual_fhand = open(qual_fhand.name, 'a')
        self._qual_fhand = qual_fhand

        self._format = file_format

    def write(self, sequence):
        'It writes one sequence to the given file'
        if sequence is None:
            return
        format_ = self._format
        if format_ == 'repr':
            self._fhand.write(repr(sequence) + '\n')
        else:
            SeqIO.write([sequence], self._fhand, BIOPYTHON_FORMATS[format_])
            if self._qual_fhand and format_ == 'fasta':
                SeqIO.write([sequence], self._qual_fhand, 'qual')

def write_seqs_in_file(seqs, seq_fhand, qual_fhand=None, format='fasta',
                       default_quality=25):
    '''It writes the given sequences in the given files.

    The seqs can be an iterartor or a list of Biopython SeqRecords or
    SeqWithQualities'''
    if format == 'fasta':
        _write_fasta_file(seqs, seq_fhand, default_quality,
                          fhand_qual=qual_fhand)
    else:
        writer = SequenceWriter(fhand=seq_fhand, qual_fhand=qual_fhand,
                                file_format=format)
        for seq in seqs:
            writer.write(seq)

def _write_fasta_file(seqs, fhand_seq, default_quality=None, fhand_qual=None):
    '''Given a Seq and its default name it returns a fasta file in a
    temporary file. If the seq is a SeqWithQuality you can ask a qual fasta
    file'''
    try:
        # Is seqs an seq or an iter??
        #pylint:disable-msg=W0104
        seqs.name
        seqs = [seqs]
        #pylint:disable-msg=W0704
    except AttributeError:
        pass

    for seq in seqs:
        name = get_seq_name(seq)

        if fhand_qual is not None:
            try:
                quality = seq.letter_annotations["phred_quality"]
            except (AttributeError, KeyError):
                if default_quality:
                    quality = [default_quality] * len(seq)
                else:
                    msg = 'Sequence must have a phred_quality letter annotation'
                    raise AttributeError(msg)


            if quality is not None:
                quality = [str(qual) for qual in quality]
                fhand_qual.write(fasta_str(' '.join(quality), name))
            else:
                raise AttributeError('Quality can not be empty')
        try:
            desc = seq.description
        except AttributeError:
            desc = None
        if desc == "<unknown description>":
            desc = None
        fhand_seq.write(fasta_str(seq, name, desc))

    fhand_seq.flush()
    fhand_seq.seek(0)

    if fhand_qual is not None:
        fhand_qual.flush()
        fhand_qual.seek(0)

def fasta_str(seq, name, description=None):
    'Given a sequence it returns a string with the fasta'
    fasta_str_ = ['>']
    fasta_str_.append(name)
    if description:
        fasta_str_.append(' %s' % description)
    fasta_str_.append('\n')
    try:
        fasta_str_.append(str(seq.seq).strip())
    except AttributeError:
        fasta_str_.append(str(seq).strip())
    fasta_str_.append('\n')
    return ''.join(fasta_str_)

def temp_qual_file(seqs):
    'Given a qual seq it return a temporary qual fasta file'
    fhand_qual = tempfile.NamedTemporaryFile(suffix='.qual')
    for seq in seqs:
        name    = get_seq_name(seq)
        quality = seq.letter_annotations["phred_quality"]

        quality = [str(qual) for qual in quality]
        fhand_qual.write('>%s\n%s\n' % (name , ' '.join(quality)))

    fhand_qual.flush()
    fhand_qual.seek(0)
    return fhand_qual

def temp_fasta_file(seqs, write_qual=False):
    '''Given a Seq and its default name it returns a fasta file in a
    temporary file. If the seq is a SeqWithQuality you can ask a qual fasta
    file'''
    fhand_seq = tempfile.NamedTemporaryFile(suffix='.fasta')
    if write_qual:
        fhand_qual = tempfile.NamedTemporaryFile(suffix='.fasta')
    else:
        fhand_qual = None
    _write_fasta_file(seqs, fhand_seq, fhand_qual=fhand_qual)

    if write_qual:
        return fhand_seq, fhand_qual
    else:
        return fhand_seq

def create_temp_fasta_files(seq1, seq2):
    'It returns two temporal fasta files.'
    #we create two temp files
    fileh1 = temp_fasta_file(seq1)
    fileh2 = temp_fasta_file(seq2)
    return fileh1, fileh2
