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
cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True, nsprpub=True,
                     extra_deps=['_pl_bld.h'])

tupmk.parse('.')

config_now = "%s/nsprpub/config/now" % (moz_root)

suffix = tupmk.get_var_string('SUF')
prod = "lib%s%s.%s" % (tupmk.get_var_string('LIBRARY_NAME'),
                       tupmk.get_var_string('LIBRARY_VERSION'),
                       tupmk.get_var_string('DLL_SUFFIX'))
gen_pl_bld = """shdate=`date "+%%Y-%%m-%%d %%T"`; """
gen_pl_bld += """shnow=`%s`; """ % (config_now)
gen_pl_bld += """(echo "#define _BUILD_STRING \\"$shdate\\""; """
gen_pl_bld += """if test ! -z "$shnow"; then echo "#define _BUILD_TIME ${shnow}%s"; fi; """ % (suffix)
gen_pl_bld += """echo "#define _PRODUCTION \\"%s\\"") > %%o""" % (prod)

print ": %s |> %s |> _pl_bld.h" % (config_now, gen_pl_bld)

cpp.generate_cpp_rules()
cpp.generate_nsprpub_library()
