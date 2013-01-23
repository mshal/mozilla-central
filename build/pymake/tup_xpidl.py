#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 4:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR sub/dir1 [sub/dir2...]' % sys.argv[0])

tupmk = tup_makefile.TupMakefile(sys.argv[1], sys.argv[2])

for subdir in sys.argv[3:]:
    tupmk.parse(subdir)

    vpath = tupmk.get_var('VPATH')

    # TODO: If --xpidl is set? only should happen in dist/idl
    # TODO: Bug 698251 for SDK_XPIDLSRCS
    for varname in ['XPIDLSRCS', 'SDK_XPIDLSRCS']:
        xpidl = tupmk.get_var(varname)
        if xpidl:
            # Create a tup :-rule for each symlink to an .idl file that we need.
            print ": foreach ",
            for filename in xpidl:
                fullpath = tupmk.vpath_resolve(subdir, vpath, filename)
                if fullpath:
                    print fullpath,
            print " |> !ln |> %b <installed-idls>"
