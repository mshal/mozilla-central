#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
from optparse import OptionParser

class TupCpp(object):
    def __init__(self, tupmk, moz_objdir, host_srcs_flag=False,
                 target_srcs_flag=False, extra_includes="", js_src=False,
                 nsprpub=False, extra_deps=[], filter_out=[]):
        self.tupmk = tupmk
        self.moz_objdir = moz_objdir
        self.host_srcs_flag = host_srcs_flag
        self.target_srcs_flag = target_srcs_flag
        self.extra_includes = extra_includes
        self.js_src = js_src
        self.extra_deps = extra_deps
        self.extra_flags = ""
        self.filter_out = filter_out

        self.cpp_flags = ['COMPILE_CXXFLAGS']

        if nsprpub:
            self.c_flags = ['CFLAGS']
        else:
            self.c_flags = ['COMPILE_CFLAGS']

        self.host_cpp_flags = ['HOST_CXXFLAGS',
                               'INCLUDES',
                               'NSPR_CFLAGS',
                               ]

        self.host_c_flags = ['HOST_CFLAGS',
                             'INCLUDES',
                             'NSPR_CFLAGS',
                             ]

        self.host_link_flags = ['HOST_CXXFLAGS',
                                'INCLUDES',
                                'HOST_LIBS'
                                'HOST_EXTRA_LIBS'
                                ]

    def get_all_flags(self, flags, filename):
        all_flags = []

        targets = self.tupmk.subdir_makefile._targets
        if filename in targets:
            variables = targets[filename].variables
        else:
            variables = self.tupmk.subdir_makefile.variables

        for flag_group in flags:
            value = self.tupmk.get_var(flag_group, variables=variables)
            for flag in value:
                # Skip the make-specific dependency flags.
                if not flag in ['-MD', '-MF', '/.pp'] and not flag in self.filter_out:
                    if '@tupjob' in flag:
                        print >> sys.stderr, "Error: @tupjob in flag:", flag
                        sys.exit(1)
                    # TODO: Also error if /home/foo is in flags? Or run in chroot?

                    if 'ipc/ipdl/_ipdlheaders' in flag:
                        # Make stores the ipdl headers in the objdir, but we
                        # generate them from tup so they are relative to the
                        # srcdir.
                        all_flags.append('-I' + os.path.join(self.tupmk.moz_root, 'ipc/ipdl/_ipdlheaders'))
                    elif flag.startswith('-I/'):

                        # Search for the objdir in a -I/full/path flag to see if
                        # we need to strip out the build directory. Passing in a
                        # full directory like this circumvents the dependency
                        # detection in tup, unless we run everything in a chroot
                        # environment.
                        index = flag.find(self.moz_objdir)
                        if index == -1:
                            # Flags with a full path like -I/usr/include/gtk go
                            # through without modification
                            all_flags.append(flag)
                        else:
                            # Flags that reference our build directory, like
                            # -I/home/user/mozilla/objdir/foo get converted to
                            # -I$(MOZ_ROOT)/foo
                            all_flags.append('-I$(MOZ_ROOT)' + flag[index + len(self.moz_objdir):])
                    else:
                        all_flags.append(flag)
        return all_flags

    def generate_compile_rules(self, srcs, print_string, cc_string, vpath, flags,
                               test_includes=[], host_prefix=False,
                               compile_flag='-c', obj_suffix=None):
        if not obj_suffix:
            obj_suffix = self.tupmk.get_var_string('OBJ_SUFFIX')

        dist_include_dependency = False
        if host_prefix:
            obj_prefix_string = "host_"

            # Some host programs (eg: those in js/src) can't depend on
            # <installed-headers>, because they are used to create headers that are
            # installed. If we specify <installed-headers> as an input, it would
            # cause a circular dependency. However, some host programs *do* use
            # headers from dist/include, so we can't just remove the input for all
            # host programs.
            if not self.js_src:
                dist_include_dependency = True
        else:
            obj_prefix_string = ""
            dist_include_dependency = True

        deps = list(self.extra_deps)
        if dist_include_dependency:
            deps.append("$(MOZ_ROOT)/dist/include/<installed-headers>")

        if deps:
            extra_deps_string = " | " + (' '.join(deps))
        else:
            extra_deps_string = ""

        if srcs:
            for filename in srcs:

                base, extension = os.path.splitext(filename)
                object_file = "%s.%s" % (base, obj_suffix)
                all_flags = self.get_all_flags(flags, object_file)

                for inc in self.extra_includes:
                    all_flags.append('-I' + inc)
                all_flags.extend(test_includes)

                all_flags_string = " ".join(all_flags)
                if self.extra_flags:
                    all_flags_string += " " + self.extra_flags

                fullpath = self.tupmk.vpath_resolve('.', vpath, filename)

                # Create a tup :-rule for each cpp file to compile it
                print ": %s %s |> ^ %s %%f^ %s -o %%o %s %%f %s |> %s%%B.%s" % (fullpath, extra_deps_string, print_string, cc_string, compile_flag, all_flags_string, obj_prefix_string, obj_suffix)

    def generate_asm_rules(self):
        srcs = self.tupmk.get_var('ASFILES')
        asm = self.tupmk.get_var_string('AS')
        asflags = self.tupmk.get_var_string('ASFLAGS')
        as_dash_c_flag = self.tupmk.get_var_string('AS_DASH_C_FLAG')
        obj_suffix = self.tupmk.get_var_string('OBJ_SUFFIX')
        vpath = self.tupmk.get_var('VPATH')
        if asm.startswith('ml'):
            asoutoption = '-Fo'
        else:
            asoutoption = '-o '

        if self.extra_deps:
            extra_deps_string = " | " + (' '.join(self.extra_deps))
        else:
            extra_deps_string = ""

        for filename in srcs:
            fullpath = self.tupmk.vpath_resolve('.', vpath, filename)
            print ": %s %s |> ^ ASM %%f^ %s %s%%o %s %s %%f |> %%B.%s" % (fullpath, extra_deps_string, asm, asoutoption, asflags, as_dash_c_flag, obj_suffix)

    def generate_simple_link_rules(self, srcs, print_string, ld_string, flags):
        if srcs:
            for filename in srcs:
                all_flags = self.get_all_flags(flags, filename)
                print ": %s |> ^ %s %%o^ %s -o %%o %%f %s |> %s " % (filename + ".o", print_string, ld_string, " ".join(all_flags), filename)

    def generate_cpp_rules(self, cppsrcs=[], csrcs=[], flags=""):
        # Some Tupfiles (eg: ipc/ipdl) pass in cppsrcs manually.
        if not cppsrcs:
            cppsrcs = self.tupmk.get_var('CPPSRCS')
        if not csrcs:
            csrcs = self.tupmk.get_var('CSRCS')
        cpp_unit_tests = self.tupmk.get_var('CPP_UNIT_TESTS')
        host_cppsrcs = self.tupmk.get_var('HOST_CPPSRCS')
        host_csrcs = self.tupmk.get_var('HOST_CSRCS')
        vpath = self.tupmk.get_var('VPATH')

        self.extra_flags = flags

        test_includes = []
        if cpp_unit_tests:
            cppsrcs.extend(cpp_unit_tests)
            test_includes = ["-I" + os.path.join(moz_root, "dist/include/testing")]

        if self.target_srcs_flag:
            self.generate_compile_rules(cppsrcs, 'C++', '$(CXX)', vpath,
                                        self.cpp_flags, test_includes)
            self.generate_compile_rules(csrcs, 'CC', '$(CC)', vpath, self.c_flags)
            self.generate_asm_rules()

        if self.host_srcs_flag:
            self.generate_compile_rules(host_cppsrcs, 'C++ [host]', '$(HOST_CXX)',
                                        vpath, self.host_cpp_flags,
                                        host_prefix=True)
            self.generate_compile_rules(host_csrcs, 'CC [host]', '$(HOST_CC)',
                                        vpath, self.host_c_flags,
                                        host_prefix=True)

            host_simple_programs = self.tupmk.get_var('HOST_SIMPLE_PROGRAMS')
            if host_simple_programs:
                self.generate_simple_link_rules(host_simple_programs,
                                                'LD [host]', '$(HOST_CXX)',
                                                self.host_link_flags)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('usage: %s [--host-srcs] [--target-srcs] MOZ_ROOT MOZ_OBJDIR [TUP_EXTRA_INCLUDES...]' % sys.argv[0])

    p = OptionParser()
    p.add_option('--host-srcs', action='store_true', dest='host_srcs',
                 default=False,
                 help='Compile only the HOST sources.')
    p.add_option('--target-srcs', action='store_true', dest='target_srcs',
                 default=False,
                 help='Compile only the non-HOST (target) sources.')
    p.add_option('--js-src', action='store_true', dest='js_src', default=False,
                 help='Enable special treatment of js/src/*')
    p.add_option('--nsprpub', action='store_true', dest='nsprpub', default=False,
                 help='Enable special treatment of nsprpub/*')
    p.add_option('-I', dest='tup_extra_includes', default=[], type=str,
                 action='append',
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
                                     js_src=options.js_src,
                                     nsprpub=options.nsprpub)
    tupmk.parse('.')

    tupcpp = TupCpp(tupmk, moz_objdir,
                    host_srcs_flag=options.host_srcs,
                    target_srcs_flag=options.target_srcs,
                    extra_includes=options.tup_extra_includes,
                    js_src=options.js_src,
                    nsprpub=options.nsprpub)

    tupcpp.generate_cpp_rules()
