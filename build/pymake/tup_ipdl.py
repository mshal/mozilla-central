#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT sub/dir1 [sub/dir2...]' % sys.argv[0])

tupmk = tup_makefile.TupMakefile(sys.argv[1], makefile_name='ipdl.mk', always_enabled=True)

inputs = []
incdirs = []
outputs = ['IPCMessageStart.h', 'ipdl_lextab.py', 'ipdl_yacctab.py']

for subdir in sys.argv[2:]:
    tupmk.parse(subdir)

    incdirs.append('-I%s' % subdir)

    ipdlsrcs = tupmk.get_var('IPDLSRCS')
    if ipdlsrcs:
        for ipdl in ipdlsrcs:
            inputs.append(os.path.join(subdir, ipdl))
            (basename, ext) = os.path.splitext(ipdl)

            if ext == '.ipdl':
                extensions = ['Child.cpp', 'Parent.cpp', '.cpp',
                              'Child.h', 'Parent.h', '.h']
            elif ext == '.ipdlh':
                extensions = ['.cpp', '.h']
            else:
                print >> sys.stderr, "Error: Unknown extension for IPDLSRCS: ", ipdl
                sys.exit(1)
            for extension in extensions:
                outputs.append("%s%s" % (basename, extension))

# Create a single rule to process all of the .ipdl/.ipdlh files in one go.
# Although we could theoretically process these individually, the inter-.ipdl
# dependencies are such that all .ipdl files are dependent on all others.
print ": ",
print ' '.join(inputs),
print "|> ^ tup-ipdl.py %f^ $(PYTHON) $(PYTHONPATH) $(MOZ_ROOT)/ipc/ipdl/tup-ipdl.py ",
print ' '.join(incdirs),
print "%f |>",
print ' '.join(outputs)
