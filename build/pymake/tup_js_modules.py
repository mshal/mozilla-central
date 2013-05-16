#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
from optparse import OptionParser

if len(sys.argv) < 5:
    sys.exit('usage: %s EXTRA_PP_JS_MODULES MOZ_ROOT MOZ_OBJDIR sub/dir1 [sub/dir2...]' % sys.argv[0])

p = OptionParser()
p.add_option('--destdir', dest='destdir', default=None,
             help='Optional: Only files for this destination directory will be '
             'installed.')
(options, args) = p.parse_args()

pp_var = args[0]
tupmk = tup_makefile.TupMakefile(args[1], args[2])

for subdir in args[3:]:
    tupmk.parse(subdir)

    pp_js_modules = tupmk.get_var(pp_var)
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

    if options.destdir:
        install_targets = tupmk.get_var('INSTALL_TARGETS')
        for target in install_targets:
            dest = tupmk.get_var_string('%s_DEST' % (target))
            if dest == '/' + options.destdir:
                files = tupmk.get_var('%s_FILES' % (target))
                for f in files:
                    print ": foreach %s/%s |> !ln |> %%b" % (subdir, f)

        pp_targets = tupmk.get_var('PP_TARGETS')
        for target in pp_targets:
            dest = tupmk.get_var_string('%s_PATH' % (target))
            if dest == '/' + options.destdir:
                files = tupmk.get_var(target)
                flags = tupmk.get_var_string('%s_FLAGS' % target)
                for f in files:
                    print ": foreach %s/%s |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %s %s %%f > %%o |> %%b" % (subdir, f, flags, defines, acdefines)
