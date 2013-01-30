#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR [TUP_EXTRA_INCLUDES...]' % sys.argv[0])

moz_root = sys.argv[1]
moz_objdir = sys.argv[2]
tup_extra_includes = sys.argv[3:]
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True,
                                 need_config_mk=True)

tupmk.parse('.')

cppsrcs = tupmk.get_var('CPPSRCS')
vpath = tupmk.get_var('VPATH')

cmdline_flags = ['STL_FLAGS', 'VISIBILITY_FLAGS', 'DEFINES', 'INCLUDES', 'DSO_CFLAGS', 'DSO_PIC_CFLAGS', 'CXXFLAGS', 'RTL_FLAGS', 'OS_CPPFLAGS', 'OS_COMPILE_CXXFLAGS']

#for i in cmdline_flags:
#    print >> sys.stderr, "[33m%s[0m: %s" % (i, tupmk.get_var(i))

all_flags = []
for flag_group in cmdline_flags:
    value = tupmk.get_var(flag_group)
    for flag in value:
        # Skip the make-specific dependency flags.
        if not flag in ['-MD', '-MF', '/.pp']:
            if '@tupjob' in flag:
                print >> sys.stderr, "Error: @tupjob in flag:", flag
                sys.exit(1)
            # TODO: Also error if /home/foo is in flags? Or run in chroot?

            if 'ipc/ipdl/_ipdlheaders' in flag:
                # Make stores the ipdl headers in the objdir, but we generate
                # them from tup so they are relative to the srcdir.
                all_flags.append('-I' + os.path.join(moz_root, 'ipc/ipdl/_ipdlheaders'))
            elif flag.startswith('-I/'):

                # Search for the objdir in a -I/full/path flag to see if we need
                # to strip out the build directory. Passing in a full directory
                # like this circumvents the dependency detection in tup, unless
                # we run everything in a chroot environment.
                index = flag.find(moz_objdir)
                if index == -1:
                    # Flags with a full path like -I/usr/include/gtk go through
                    # without modification
                    all_flags.append(flag)
                else:
                    # Flags that reference our build directory, like
                    # -I/home/user/mozilla/objdir/foo get converted to
                    # -I$(MOZ_ROOT)/foo
                    all_flags.append('-I$(MOZ_ROOT)' + flag[index + len(moz_objdir):])
            else:
                all_flags.append(flag)

all_flags.extend(tup_extra_includes)

all_flags_string = " ".join(all_flags)

if cppsrcs:
    # Create a tup :-rule for each cpp file to compile it
    print ": foreach ",
    for filename in cppsrcs:
        fullpath = tupmk.vpath_resolve('.', vpath, filename)
        if fullpath:
            print fullpath,

    # TODO: PrototypeList.h is generated along with .cpp srcs, so it can't be
    # used in <installed-headers> ?
    print " | $(MOZ_ROOT)/dist/include/<installed-headers> $(MOZ_ROOT)/dom/bindings/PrototypeList.h |> ^ C++ %f^ $(CXX) -o %o -c %f ", all_flags_string, "|> %B.o"
