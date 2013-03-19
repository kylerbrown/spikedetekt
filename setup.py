from __future__ import with_statement
import os, sys, numpy

scripts = ["scripts/cluster_from_raw_data.py",
           "scripts/spikedetekt_spikeviewer.py",
           ]

from distutils.core import setup, Extension
    
setup(name="spikedetekt",
      scripts=scripts,
      version="0.1 beta",
      author="John Schulman, Dan Goodman, Shabnam Kadir, Michael Okun, Kenneth Harris",
      author_email="kenneth@cortexlab.net",
      description="Spike sorting for multi-site probes",
      license="GPL3",
      url="http://klustakwik.sourceforge.net",
      packages=["spikedetekt"],
      )
