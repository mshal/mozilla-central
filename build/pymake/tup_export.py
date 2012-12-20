#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 3:
    sys.exit('usage: %s path/to/autoconf.mk sub/dir1 [sub/dir2...]' % sys.argv[0])

tupmk = tup_makefile.TupMakefile(sys.argv[1])

for subdir in sys.argv[2:]:
    tupmk.parse(subdir)

    # TODO: If --exports is set? only should happen in dist/include
    exports = tupmk.get_var('EXPORTS')
    if exports is not None:
        # Create a tup :-rule for each symlink to an .idl file that we need.
        print ": foreach ",
        for i in exports:
            print os.path.join(subdir, i),
        print " |> !ln |> %b <installed-headers>"
