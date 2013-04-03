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
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, makefile_name='Makefile',
                                 always_enabled=True)

libffi_path = os.path.join(moz_root, moz_objdir, 'js', 'src', 'ctypes', 'libffi')
tupmk.parse(libffi_path)

srcs = tupmk.get_var('SOURCES')

# This srcdir goes through js/src/ctypes/libffi, and we use it so we can grep
# out full paths which mess with tup's dependency detection.
srcdir = tupmk.get_var('abs_srcdir')[0]

all_flags = []
for flag in tupmk.get_var('COMPILE'):
    # Trim down full paths so that they are local to libffi
    if flag.startswith('-I' + srcdir):
        all_flags.append('-I' + flag[len('-I') + len(srcdir) + 1:])
    else:
        all_flags.append(flag)

all_flags.append('-I' + libffi_path)

# OS-specific? This seems to magically appear from libtool
all_flags.append('-fPIC')
all_flags.append('-DPIC')

if srcs:
    # Compile each src file
    print ": foreach",
    print ' '.join(srcs),
    print "|> ^ CC %f^",
    print ' '.join(all_flags),
    print "-c %f -o %o",
    print "|> %B.o"

    # Link them into libffi.a
    print ": *.o |> ^ AR %o^ ar crs %o %f |> libffi.a"
