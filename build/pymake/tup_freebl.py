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
                                 makefile_name='Makefile', security=True)

# The security/nss/lib/freebl/Makefile ends up getting parsed twice - once with
# FREEBL_CHILD_BUILD=1 and once without. The freebl/config.mk file only sets
# CSRCS though and doesn't clear out ASFILES, so we need to delete that the
# first time so the .s files are only compiled once.
tupmk.parse('.')
del tupmk.subdir_makefile.variables._map['ASFILES']

cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True, security=True)
cpp.generate_cpp_rules()
cpp.generate_security_library()

# Now parse again with FREEBL_CHILD_BUILD set.
tupmk.subdir_makefile = None
tupmk.set_var('FREEBL_CHILD_BUILD', '1')
tupmk.parse('.')

cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True, security=True)
cpp.generate_cpp_rules()
cpp.generate_security_library()
