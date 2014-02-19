#!/usr/bin/env python
'''
Main script file for SpikeDetekt
'''
from spikedetekt.core import spike_detection_job
from spikedetekt.parameters import Parameters
from spikedetekt.utils import basename_noext
import os

usage = '''
SpikeDetekt should be called as:

python detektspikes.py filename.params

All options must be specified in the parameters file.
'''


def main(parameters_file, extrafields=None):
    try:
        if not extrafields:
            execfile(parameters_file, {}, Parameters)
        else:
            # Read the parameters file.
            with open(parameters_file) as f:
                parameters_text = f.read()
            # Do the replacements.
            for extrafield in extrafields:
                # fields[0] is a field name (e.g. %FILE%), fields[1] is the
                # value
                fields = extrafield.split('=')
                parameters_text = parameters_text.replace(
                    '%' + fields[0] + '%', fields[1])
            exec(parameters_text, {}, Parameters)
    except IOError:
        print('Parameters file %s does not exist or cannot be read.'
              % parameters_file)
        exit()
    print 'Read parameters from file', parameters_file

    # Make sure we have probe and raw data, and that the files exist
    try:
        probe_file = Parameters['PROBE_FILE']
    except KeyError:
        print 'Parameters file needs a PROBE_FILE option.'
        exit()
    if not os.path.exists(probe_file):
        print 'Probe file %s does not exist.' % probe_file

    try:
        raw_data_files = Parameters['RAW_DATA_FILES']
        # Convert a string into a list with one element.
        if isinstance(raw_data_files, basestring):
            raw_data_files = [raw_data_files]
    except KeyError:
        print 'Parameters file needs a RAW_DATA_FILES option.'
        exit()
    for file in raw_data_files:
        if not os.path.exists(file):
            print 'Raw data file %s does not exist.' % file
            exit()

    # Check other options are present in parameters file
    if not 'NCHANNELS' in Parameters or not 'SAMPLERATE' in Parameters:
        print 'Parameters file needs NCHANNELS and SAMPLERATE options.'
        exit()

    # Find output directory and name
    output_dir = Parameters['OUTPUT_DIR']
    output_name = Parameters['OUTPUT_NAME']

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(parameters_file))
    if output_name is None:
        output_name = basename_noext(parameters_file)

    spike_detection_job(raw_data_files, probe_file, output_dir, output_name)
