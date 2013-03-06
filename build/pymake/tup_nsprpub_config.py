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
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True,
                                 nsprpub=True)
cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True, nsprpub=True)

tupmk.parse('.')

cpp.generate_cpp_rules()

cc = tupmk.get_var_string('CC')
flags = tupmk.get_var_string('XCFLAGS') + \
        tupmk.get_var_string('LDFLAGS') + \
        tupmk.get_var_string('XLDOPTS')
outoption = tupmk.get_var_string('OUTOPTION')
prog_suffix = tupmk.get_var_string('PROG_SUFFIX')
obj_suffix = tupmk.get_var_string('OBJ_SUFFIX')

# For some reason the space at the end of '-o ' doesn't seem to carry through.
if outoption == '-o':
    outoption = '-o '

for prog in tupmk.get_var('PROGS'):
    prog = prog.replace('./', '')
    print ": %s |> %s %s %%f %s%%o |> %s" % (prog + '.' + obj_suffix, cc, flags, outoption, prog + prog_suffix)
