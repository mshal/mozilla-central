#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

moz_root = sys.argv[1]
moz_objdir = sys.argv[2]
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True)

tupmk.parse('.')

flags = tupmk.get_var('DEFINES')
flags.extend(tupmk.get_var('ACDEFINES'))
flags_string = ' '.join(flags)

print ": $(MOZ_ROOT)/config/buildid |> ^ Preprocessor.py -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s application.ini > %%o |> application.ini.gen" % (flags_string)
