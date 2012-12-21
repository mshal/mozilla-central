#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
from optparse import OptionParser

if len(sys.argv) < 4:
    sys.exit('usage: %s [-m Makefile] EXPORTS MOZ_ROOT sub/dir1 [sub/dir2...]' % sys.argv[0])

p = OptionParser()
p.add_option('-m', dest='makefile', default='Makefile.in',
        help='Optional: Name of the Makefile (defaults to Makefile.in)')

(options, args) = p.parse_args()

export_var = args[0]
tupmk = tup_makefile.TupMakefile(args[1], options.makefile)

for subdir in args[2:]:
    tupmk.parse(subdir)

    # TODO: If --exports is set? only should happen in dist/include
    exports = tupmk.get_var(export_var)
    vpath = tupmk.get_var('VPATH')
    if exports:
        # Create a tup :-rule for each symlink to an .idl file that we need.
        print ": foreach ",
        for filename in exports:
            fullpath = tupmk.vpath_resolve(subdir, vpath, filename)
            if fullpath:
                print fullpath,

        print " |> !ln |> %b $(MOZ_ROOT)/dist/include/<installed-headers>"
