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

for subdir in sys.argv[2:]:
    tupmk.parse(subdir)

    ipdlsrcs = tupmk.get_var('IPDLSRCS')
    if ipdlsrcs:
        for ipdl in ipdlsrcs:
            (basename, ext) = os.path.splitext(ipdl)

            if ext == '.ipdl':
                extensions = ['Child.h', 'Parent.h', '.h']
            elif ext == '.ipdlh':
                extensions = ['.h']
            else:
                print >> sys.stderr, "Error: Unknown extension for IPDLSRCS: ", ipdl
                sys.exit(1)
            for extension in extensions:
                filename = "%s%s" % (basename, extension)
                print ": %s |> !ln |> %s" % (os.path.join(sys.argv[1], 'ipc/ipdl/_ipdlheaders', filename), filename)
