#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
from optparse import OptionParser

def get_all_flags(flags):
    all_flags = []
    for flag_group in flags:
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
    return all_flags

def generate_compile_rules(srcs, print_string, cc_string, vpath, flags, test_includes=[],
                           host_prefix=False):
    all_flags = get_all_flags(flags)

    for inc in options.tup_extra_includes:
        all_flags.append('-I' + inc)
    all_flags.extend(test_includes)

    all_flags_string = " ".join(all_flags)

    dist_include_dependency = False
    if host_prefix:
        obj_prefix_string = "host_"

        # Some host programs (eg: those in js/src) can't depend on
        # <installed-headers>, because they are used to create headers that are
        # installed. If we specify <installed-headers> as an input, it would
        # cause a circular dependency. However, some host programs *do* use
        # headers from dist/include, so we can't just remove the input for all
        # host programs.
        if host_dist_include_dependency:
            dist_include_dependency = True
    else:
        obj_prefix_string = ""
        dist_include_dependency = True

    if dist_include_dependency:
        extra_deps = " | $(MOZ_ROOT)/dist/include/<installed-headers>"
    else:
        extra_deps = ""

    if srcs:
        # Create a tup :-rule for each cpp file to compile it
        print ": foreach ",
        for filename in srcs:
            fullpath = tupmk.vpath_resolve('.', vpath, filename)
            if fullpath:
                print fullpath,

        print " %s |> ^ %s %%f^ %s -o %%o -c %%f %s |> %s%%B.o" % (extra_deps, print_string, cc_string, all_flags_string, obj_prefix_string)

def generate_simple_link_rules(srcs, print_string, ld_string, flags):
    all_flags = get_all_flags(flags)
    if srcs:
        for filename in srcs:
            print ": %s |> ^ %s %%o^ %s -o %%o %%f %s |> %s " % (filename + ".o", print_string, ld_string, " ".join(all_flags), filename)


if len(sys.argv) < 3:
    sys.exit('usage: %s [--host-srcs] [--target-srcs] MOZ_ROOT MOZ_OBJDIR [TUP_EXTRA_INCLUDES...]' % sys.argv[0])

p = OptionParser()
p.add_option('--host-srcs', action='store_true', dest='host_srcs', default=False,
             help='Compile only the HOST sources.')
p.add_option('--target-srcs', action='store_true', dest='target_srcs', default=False,
             help='Compile only the non-HOST (target) sources.')
p.add_option('--js-src', action='store_true', dest='js_src', default=False,
             help='Enable special treatment of js/src/*')
p.add_option('-I', dest='tup_extra_includes', default=[], type=str, action='append',
             help='Extra include directories to pass to the compiler that are not in the Makefile')

(options, args) = p.parse_args()

# If unspecified, build host and target srcs. This is normally the case unless a
# host program needs to generate a file that is needed by the target sources.
if not options.host_srcs and not options.target_srcs:
    options.host_srcs = True
    options.target_srcs = True

moz_root = args[0]
moz_objdir = args[1]
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True,
                                 need_config_mk=True,
                                 js_src=options.js_src)
if options.js_src:
    host_dist_include_dependency = False
else:
    host_dist_include_dependency = True

tupmk.parse('.')

cppsrcs = tupmk.get_var('CPPSRCS')
cpp_unit_tests = tupmk.get_var('CPP_UNIT_TESTS')
csrcs = tupmk.get_var('CSRCS')
host_cppsrcs = tupmk.get_var('HOST_CPPSRCS')
host_csrcs = tupmk.get_var('HOST_CSRCS')
vpath = tupmk.get_var('VPATH')

test_includes = []
if cpp_unit_tests:
    cppsrcs.extend(cpp_unit_tests)
    test_includes = ["-I" + os.path.join(moz_root, "dist/include/testing")]

cpp_flags = ['STL_FLAGS',
             'VISIBILITY_FLAGS',
             'DEFINES',
             'INCLUDES',
             'DSO_CFLAGS',
             'DSO_PIC_CFLAGS',
             'CXXFLAGS',
             'RTL_FLAGS',
             'OS_CPPFLAGS',
             'OS_COMPILE_CXXFLAGS',
             ]

c_flags = ['VISIBILITY_FLAGS',
           'DEFINES',
           'INCLUDES',
           'DSO_CFLAGS',
           'DSO_PIC_CFLAGS',
           'CFLAGS',
           'RTL_FLAGS',
           'OS_CPPFLAGS',
           'OS_COMPILE_CFLAGS',
           ]

host_cpp_flags = ['HOST_CXXFLAGS',
                  'INCLUDES',
                  'NSPR_CFLAGS',
                  ]

host_c_flags = ['HOST_CFLAGS',
                'INCLUDES',
                'NSPR_CFLAGS',
                ]

host_link_flags = ['HOST_CXXFLAGS',
                   'INCLUDES',
                   'HOST_LIBS'
                   'HOST_EXTRA_LIBS'
                   ]

#for i in cpp_flags:
#    print >> sys.stderr, "[33m%s[0m: %s" % (i, tupmk.get_var(i))

if options.target_srcs:
    generate_compile_rules(cppsrcs, 'C++', '$(CXX)', vpath, cpp_flags, test_includes)
    generate_compile_rules(csrcs, 'CC', '$(CC)', vpath, c_flags)

if options.host_srcs:
    generate_compile_rules(host_cppsrcs, 'C++ [host]', '$(HOST_CXX)', vpath,
                           host_cpp_flags, host_prefix=True)
    generate_compile_rules(host_csrcs, 'CC [host]', '$(HOST_CC)', vpath,
                           host_c_flags, host_prefix=True)

    host_simple_programs = tupmk.get_var('HOST_SIMPLE_PROGRAMS')
    if host_simple_programs:
        generate_simple_link_rules(host_simple_programs, 'LD [host]', '$(HOST_CXX)',
                                   host_link_flags)
