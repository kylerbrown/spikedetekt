#!/usr/bin/env python
'''
Main script file for SpikeDetekt
'''
import sys

usage = '''
SpikeDetekt should be called as:

python detektspikes.py filename.params

All options must be specified in the parameters file.
'''

if __name__ == '__main__':
    if len(sys.argv) <= 1:  # or len(sys.argv)>2:
        print usage.strip()
        exit()

    # Read parameters file
    parameters_file = sys.argv[1]
    extrafields = sys.argv[2:]
