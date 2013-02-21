#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
import tup_cpp

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

moz_root = sys.argv[1]
moz_objdir = sys.argv[2]

tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True)

inputs = []
incdirs = []
outputs = ['IPCMessageStart.h', 'ipdl_lextab.py', 'ipdl_yacctab.py']

tupmk.parse('.')
ipdldirs = tupmk.get_var('IPDLDIRS')

# Now that we have the list of IPDLDIRS, we will be parsing ipdl.mk files
# in each of those directories. Setup tupmk to do that.
tupmk.makefile_name = 'ipdl.mk'
tupmk.always_enabled = True

cppsrcs = []

for ipdldir in ipdldirs:
    subdir = os.path.join(moz_root, ipdldir)
    incdirs.append('-I%s' % subdir)

    ipdlsrcs = tupmk.one_time_parse(subdir, 'IPDLSRCS')
    if ipdlsrcs:
        for ipdl in ipdlsrcs:
            inputs.append(os.path.join(subdir, ipdl))
            (basename, ext) = os.path.splitext(ipdl)

            extensions = ['']
            if ext == '.ipdl':
                extensions.extend(['Child', 'Parent'])

            for extension in extensions:
                cppsrc = "%s%s.cpp" % (basename, extension)
                cppsrcs.append(cppsrc)
                outputs.append(cppsrc)
                outputs.append("%s%s.h" % (basename, extension))

# Create a single rule to process all of the .ipdl/.ipdlh files in one go.
# Although we could theoretically process these individually, the inter-.ipdl
# dependencies are such that all .ipdl files are dependent on all others.
print ": ",
print ' '.join(inputs),
print "|> ^ tup-ipdl.py %f^ $(PYTHON) $(PYTHONPATH) $(MOZ_ROOT)/ipc/ipdl/tup-ipdl.py ",
print ' '.join(incdirs),
print "%f |>",
print ' '.join(outputs),
print ' | $(MOZ_ROOT)/dist/include/<installed-headers>'

tupcpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True)
tupcpp.generate_cpp_rules(cppsrcs)
