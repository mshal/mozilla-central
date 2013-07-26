#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

class TupCpp(object):
    def __init__(self, sandbox, host_srcs_flag=False, target_srcs_flag=False,
                 extra_includes="", js_src=False, nsprpub=False,
                 security=False, extra_deps=[], filter_out=[],
                 dist_include_dep=True):
        self.sandbox = sandbox
        self.host_srcs_flag = host_srcs_flag
        self.target_srcs_flag = target_srcs_flag
        self.extra_includes = extra_includes
        self.js_src = js_src
        self.extra_deps = extra_deps
        self.extra_flags = ""
        self.filter_out = filter_out
        self.dist_include_dep = dist_include_dep
        self.objs = []
        self.security = security

        self.cpp_flags = ['COMPILE_CXXFLAGS']

        if nsprpub or security:
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

# TODO: Target specific vars
#        targets = self.tupmk.subdir_makefile._targets
#        if filename in targets:
#            variables = targets[filename].variables
#        else:
#            variables = self.tupmk.subdir_makefile.variables

        for flag_group in flags:
            value = self.sandbox[flag_group]
            for flag in value:
                # Skip the make-specific dependency flags.
                if not flag in ['-MD', '-MF', '-MP', '.deps/.pp'] and not flag in self.filter_out:
                    if '@tupjob' in flag:
                        print >> sys.stderr, "Error: @tupjob in flag:", flag
                        sys.exit(1)
                    # TODO: Also error if /home/foo is in flags? Or run in chroot?

                    # No need to have two copies of these.
                    flag = flag.replace('system_wrappers_js', 'system_wrappers')

                    if 'ipc/ipdl/_ipdlheaders' in flag:
                        # Make stores the ipdl headers in the objdir, but we
                        # generate them from tup so they are relative to the
                        # srcdir.
                        all_flags.append('-I' + os.path.join(self.sandbox.moz_root, 'ipc/ipdl/_ipdlheaders'))
                    elif flag.startswith('-I/') or flag.startswith('-Wl,-rpath-link,/'):

                        # Search for the objdir in a -I/full/path flag to see if
                        # we need to strip out the build directory. Passing in a
                        # full directory like this circumvents the dependency
                        # detection in tup, unless we run everything in a chroot
                        # environment.
                        index = flag.find(self.sandbox.moz_objdir)
                        if index == -1:
                            # Flags with a full path like -I/usr/include/gtk go
                            # through without modification
                            all_flags.append(flag)
                        else:
                            # Flags that reference our build directory, like
                            # -I/home/user/mozilla/objdir/foo get converted to
                            # -I$(MOZ_ROOT)/objdir/foo
                            if flag.startswith('-I'):
                                prefix = '-I'
                            else:
                                prefix = '-Wl,-rpath-link,'
                            all_flags.append('%s$(MOZ_ROOT)%s' % (prefix, flag[index-1:]))
                    else:
                        all_flags.append(flag)
        return all_flags

    def generate_compile_rules(self, srcs, print_string, cc_var, flags,
                               test_includes=[], host_prefix=False,
                               compile_flag='-c', obj_suffix=None):
        if not obj_suffix:
            obj_suffix = self.sandbox.get_string('OBJ_SUFFIX')

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
                dist_include_dependency = self.dist_include_dep
        else:
            obj_prefix_string = ""
            dist_include_dependency = self.dist_include_dep

        deps = list(self.extra_deps)
        if dist_include_dependency:
            deps.append("$(MOZ_ROOT)/<installed-headers>")

        if deps:
            extra_deps_string = " | " + (' '.join(deps))
        else:
            extra_deps_string = ""

        # This is only used by widget/xremoteclient/ - we need to make sure
        # that only the LIBCPPSRCS go into the library, not the PROGCPPSRCS
        # (though we compile all CPP_SOURCES == LIBCPPSRCS + PROGCPPSRCS)
        libcppsrcs = self.sandbox['LIBCPPSRCS']

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

                fullpath = self.sandbox.vpath_resolve(filename)

                # Create a tup :-rule for each cpp file to compile it
                print ": %s %s |> ^ %s %%f^ %s -o %%o %s %%f %s |> %s/%s%%B.%s" % (fullpath, extra_deps_string, print_string, self.sandbox.get_string(cc_var), compile_flag, all_flags_string, self.sandbox.outputdir, obj_prefix_string, obj_suffix)
                basename, ext = os.path.splitext(os.path.basename(fullpath))

                # Put all objects into self.objs, except for host srcs since
                # they don't end up in libraries.
                if not host_prefix:
                    # libcppsrcs is specific to widget/xremoteclient/
                    if not libcppsrcs or filename in libcppsrcs:
                        self.objs.append("%s%s.%s" % (obj_prefix_string, basename, obj_suffix))

    def generate_asm_rules(self):
        srcs = self.sandbox['ASFILES']
        asm = self.sandbox.get_string('AS')
        asflags = self.sandbox.get_string('ASFLAGS')
        as_dash_c_flag = self.sandbox.get_string('AS_DASH_C_FLAG')
        obj_suffix = self.sandbox.get_string('OBJ_SUFFIX')
        if asm.startswith('ml'):
            asoutoption = '-Fo'
        else:
            asoutoption = '-o '

        if self.extra_deps:
            extra_deps_string = " | " + (' '.join(self.extra_deps))
        else:
            extra_deps_string = ""

        for filename in srcs:
            fullpath = self.sandbox.vpath_resolve(filename)
            print ": %s %s |> ^ ASM %%f^ %s %s%%o %s %s %%f |> %%B.%s" % (fullpath, extra_deps_string, asm, asoutoption, asflags, as_dash_c_flag, obj_suffix)
            basename, ext = os.path.splitext(os.path.basename(fullpath))
            self.objs.append("%s.%s" % (basename, obj_suffix))

    def generate_simple_link_rules(self, srcs, print_string, ld_var, flags):
        if srcs:
            for filename in srcs:
                all_flags = self.get_all_flags(flags, filename)
                print ": %s |> ^ %s %%o^ %s -o %%o %%f %s |> %s " % (filename + ".o", print_string, self.sandbox.get_string(ld_var), " ".join(all_flags), filename)

    def generate_cpp_rules(self, cppsrcs=[], csrcs=[], flags=""):
        # Some Tupfiles (eg: ipc/ipdl) pass in cppsrcs manually.
        if not cppsrcs:
            cppsrcs = self.sandbox['CPP_SOURCES']
        if not csrcs:
            csrcs = self.sandbox['CSRCS']
        cpp_unit_tests = self.sandbox['CPP_UNIT_TESTS']
        host_cppsrcs = self.sandbox['HOST_CPPSRCS']
        host_csrcs = self.sandbox['HOST_CSRCS']

        self.extra_flags = flags

        test_includes = []
        if cpp_unit_tests:
            cppsrcs.extend(cpp_unit_tests)
            test_includes = ["-I" + os.path.join(self.sandbox.moz_root, "dist/include/testing")]

        if self.target_srcs_flag:
            self.generate_compile_rules(cppsrcs, 'C++', 'CXX',
                                        self.cpp_flags, test_includes)
            self.generate_compile_rules(csrcs, 'CC', 'CC', self.c_flags)
            self.generate_asm_rules()

        if self.host_srcs_flag:
            self.generate_compile_rules(host_cppsrcs, 'C++ [host]', 'HOST_CXX',
                                        self.host_cpp_flags, host_prefix=True)
            self.generate_compile_rules(host_csrcs, 'CC [host]', 'HOST_CC',
                                        self.host_c_flags, host_prefix=True)

            host_simple_programs = self.sandbox['HOST_SIMPLE_PROGRAMS']
            if host_simple_programs:
                self.generate_simple_link_rules(host_simple_programs,
                                                'LD [host]', 'HOST_CXX',
                                                self.host_link_flags)

def generate_rules(sandbox):
    cpp = TupCpp(sandbox, target_srcs_flag=True)

    cpp.generate_cpp_rules()
