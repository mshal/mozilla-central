#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
from optparse import OptionParser

if len(sys.argv) < 4:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR sub/dir1 [sub/dir2...]' % sys.argv[0])

p = OptionParser()
(options, args) = p.parse_args()

tupmk = tup_makefile.TupMakefile(args[0], args[1])

all_xpts = []
for subdir in args[2:]:
    tupmk.parse(subdir)

    xpidl_module = tupmk.get_var_string('XPIDL_MODULE')
    if not xpidl_module:
        xpidl_module = tupmk.get_var_string('MODULE')
    if xpidl_module:
        print ": foreach %s/%s.xpt |> !ln |>" % (subdir, xpidl_module)
        if not tupmk.get_var('NO_INTERFACES_MANIFEST'):
            all_xpts.append('%s.xpt' % xpidl_module)

if all_xpts:
    print ": %s |> ^ Generate %%o^ for i in %%b; do echo \"interfaces $i\"; done > %%o |> interfaces.manifest" % (' '.join(all_xpts))
