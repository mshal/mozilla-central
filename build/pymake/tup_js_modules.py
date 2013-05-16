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

for subdir in args[2:]:
    tupmk.parse(subdir)

    pp_js_modules = tupmk.get_var('EXTRA_PP_JS_MODULES')
    vpath = tupmk.get_var('VPATH')
    defines = tupmk.get_var_string('DEFINES')
    acdefines = tupmk.get_var_string('ACDEFINES')
    if pp_js_modules:
        # Create a tup :-rule for each symlink to an .idl file that we need.
        print ": foreach ",
        for filename in pp_js_modules:
            fullpath = tupmk.vpath_resolve(subdir, vpath, filename)
            if fullpath:
                print fullpath,

        print " |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %s %%f > %%o |> %%b" % (defines, acdefines)
