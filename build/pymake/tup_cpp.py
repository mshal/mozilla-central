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
                 nsprpub=False, security=False, extra_deps=[], filter_out=[],
                 dist_include_dep=True):
        self.tupmk = tupmk
        self.moz_objdir = moz_objdir
        self.host_srcs_flag = host_srcs_flag
        self.target_srcs_flag = target_srcs_flag
        self.extra_includes = extra_includes
        self.js_src = js_src
        self.extra_deps = extra_deps
        self.extra_flags = ""
        self.filter_out = filter_out
        self.dist_include_dep = dist_include_dep
        self.objs = []

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

                    # No need to have two copies of these.
                    flag = flag.replace('system_wrappers_js', 'system_wrappers')

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
                dist_include_dependency = self.dist_include_dep
        else:
            obj_prefix_string = ""
            dist_include_dependency = self.dist_include_dep

        deps = list(self.extra_deps)
        if dist_include_dependency:
            deps.append("$(MOZ_ROOT)/dist/include/<installed-headers>")

        if deps:
            extra_deps_string = " | " + (' '.join(deps))
        else:
            extra_deps_string = ""

        # This is only used by widget/xremoteclient/ - we need to make sure
        # that only the LIBCPPSRCS go into the library, not the PROGCPPSRCS
        # (though we compile all CPPSRCS == LIBCPPSRCS + PROGCPPSRCS)
        libcppsrcs = self.tupmk.get_var('LIBCPPSRCS')

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
                basename, ext = os.path.splitext(os.path.basename(fullpath))

                # Put all objects into self.objs, except for host srcs since
                # they don't end up in libraries.
                if not host_prefix:
                    # libcppsrcs is specific to widget/xremoteclient/
                    if not libcppsrcs or filename in libcppsrcs:
                        self.objs.append("%s%s.%s" % (obj_prefix_string, basename, obj_suffix))

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
            basename, ext = os.path.splitext(os.path.basename(fullpath))
            self.objs.append("%s.%s" % (basename, obj_suffix))

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

    def resolve_library(self, lib):
        system_libs = {"-lpthread", "-lc", "-ldl"}
        conversions = {
                       # Libraries that show up as '-lfoo'
                       "-lmozsqlite3": "db/sqlite3/src/libmozsqlite3.so",
                       "-lxpcom": "xpcom/stub/libxpcom.so",
                       "-lsoundtouch": "media/libsoundtouch/src/libsoundtouch.so",
                       "-lcrmf": "security/nss/lib/crmf/libcrmf.a",
                       "-lmozalloc": "memory/mozalloc/libmozalloc.so",
                       "-lxul": "toolkit/library/libxul.so",
                       "-lnspr4": "nsprpub/pr/src/libnspr4.so",
                       "-lnss3": "security/nss/lib/nss/libnss3.so",
                       "-lnssutil3": "security/nss/lib/util/libnssutil3.so",
                       "-lplc4": "nsprpub/lib/libc/src/libplc4.so",
                       "-lplds4": "nsprpub/lib/ds/libplds4.so",
                       "-lsmime3": "security/nss/lib/smime/libsmime3.so",
                       "-lssl3": "security/nss/lib/ssl/libssl3.so",
                       # Libraries that show up as '../dist/lib/libbaz.a' or
                       # have a '.libs' path element in them.
                       "libmozalloc.a": "memory/mozalloc/libmozalloc.so",
                       "libxpt.a": "xpcom/typelib/xpt/src/libxpt.a",
                       "libffi.a": "js/src/ctypes/libffi/libffi.a",
                       "libfreebl.a": "security/nss/lib/freebl/libfreebl.a",
                       "libjs_static.a": "js/src/libjs_static.a",
                       "libxpcomglue_s.a": "xpcom/glue/libxpcomglue_s.a",
                       "libunicharutil_external_s.a": "intl/unicharutil/util/libunicharutil_external_s.a",
                       "libmozz.a": "modules/zlib/src/libmozz.a",
                       "libxul.so": "toolkit/library/libxul.so",
                       "libxul.a": "toolkit/library/libxul.so",
                       "libdbm.a": "security/dbm/src/libdbm.a",
                       "libgkmedias.a": "layout/media/libgkmedias.a",
                       "libmtransport.a": "media/mtransport/build/libmtransport.a",
                       "libecc.a": "media/webrtc/signaling/libecc.a",
                       "libsipcc.a": "media/webrtc/signaling/libsipcc.a",
                       "libmozsqlite3.a": "db/sqlite3/src/libmozsqlite3.so",
                       # libraries for libxul normally in staticlib/
                       "libnecko.a": "netwerk/build/libnecko.a",
                       "libuconv.a": "intl/uconv/src/libuconv.a",
                       "libi18n.a": "intl/build/libi18n.a",
                       "libchardet.a": "intl/chardet/src/libchardet.a",
                       "libjar50.a": "modules/libjar/libjar50.a",
                       "libstartupcache.a": "startupcache/libstartupcache.a",
                       "libpref.a": "modules/libpref/src/libpref.a",
                       "libhtmlpars.a": "parser/htmlparser/src/libhtmlpars.a",
                       "libidentity.a": "toolkit/identity/libidentity.a",
                       "libimglib2.a": "image/build/libimglib2.a",
                       "libmediasniffer.a": "toolkit/components/mediasniffer/libmediasniffer.a",
                       "libgkgfx.a": "gfx/src/libgkgfx.a",
                       "libgklayout.a": "layout/build/libgklayout.a",
                       "libdocshell.a": "docshell/build/libdocshell.a",
                       "libembedcomponents.a": "embedding/components/build/libembedcomponents.a",
                       "libwebbrwsr.a": "embedding/browser/build/libwebbrwsr.a",
                       "libnsappshell.a": "xpfe/appshell/src/libnsappshell.a",
                       "libtxmgr.a": "editor/txmgr/src/libtxmgr.a",
                       "libcommandlines.a": "toolkit/components/commandlines/libcommandlines.a",
                       "libtoolkitcomps.a": "toolkit/components/build/libtoolkitcomps.a",
                       "libpipboot.a": "security/manager/boot/src/libpipboot.a",
                       "libpipnss.a": "security/manager/ssl/src/libpipnss.a",
                       "libappcomps.a": "xpfe/components/build/libappcomps.a",
                       "libjsreflect.a": "toolkit/components/reflect/libjsreflect.a",
                       "libcomposer.a": "editor/composer/src/libcomposer.a",
                       "libtelemetry.a": "toolkit/components/telemetry/libtelemetry.a",
                       "libjsinspector.a": "toolkit/devtools/debugger/libjsinspector.a",
                       "libjsdebugger.a": "js/ductwork/debugger/libjsdebugger.a",
                       "libstoragecomps.a": "storage/build/libstoragecomps.a",
                       "librdf.a": "rdf/build/librdf.a",
                       "libwindowds.a": "xpfe/components/windowds/libwindowds.a",
                       "libjsctypes.a": "toolkit/components/ctypes/libjsctypes.a",
                       "libjsperf.a": "toolkit/components/perf/libjsperf.a",
                       "libgkplugin.a": "dom/plugins/base/libgkplugin.a",
                       "libunixproxy.a": "toolkit/system/unixproxy/libunixproxy.a",
                       "libjsd.a": "js/jsd/libjsd.a",
                       "libautoconfig.a": "extensions/pref/autoconfig/src/libautoconfig.a",
                       "libauth.a": "extensions/auth/libauth.a",
                       "libcookie.a": "extensions/cookie/libcookie.a",
                       "libpermissions.a": "extensions/permissions/libpermissions.a",
                       "libuniversalchardet.a": "extensions/universalchardet/src/xpcom/libuniversalchardet.a",
                       "libfileview.a": "toolkit/components/filepicker/libfileview.a",
                       "libplaces.a": "toolkit/components/places/libplaces.a",
                       "libtkautocomplete.a": "toolkit/components/autocomplete/libtkautocomplete.a",
                       "libsatchel.a": "toolkit/components/satchel/libsatchel.a",
                       "libpippki.a": "security/manager/pki/src/libpippki.a",
                       "libwidget_gtk2.a": "widget/gtk2/libwidget_gtk2.a",
                       "libimgicon.a": "image/decoders/icon/libimgicon.a",
                       "libprofiler.a": "tools/profiler/libprofiler.a",
                       "libaccessibility.a": "accessible/build/libaccessibility.a",
                       "libremoteservice.a": "toolkit/components/remote/libremoteservice.a",
                       "libspellchecker.a": "extensions/spellcheck/src/libspellchecker.a",
                       "libzipwriter.a": "modules/libjar/zipwriter/src/libzipwriter.a",
                       "libservices-crypto.a": "services/crypto/component/libservices-crypto.a",
                       "libnkgio.a": "extensions/gio/libnkgio.a",
                       "libpeerconnection.a": "dom/media/bridge/libpeerconnection.a",
                       "libjsipc_s.a": "js/ipc/libjsipc_s.a",
                       "libdomipc_s.a": "dom/ipc/libdomipc_s.a",
                       "libdomplugins_s.a": "dom/plugins/ipc/libdomplugins_s.a",
                       "libmozipc_s.a": "ipc/glue/libmozipc_s.a",
                       "libmozipdlgen_s.a": "ipc/ipdl/libmozipdlgen_s.a",
                       "libipcshell_s.a": "ipc/testshell/libipcshell_s.a",
                       "libgfxipc_s.a": "gfx/ipc/libgfxipc_s.a",
                       "libhal_s.a": "hal/libhal_s.a",
                       "libdombindings_s.a": "dom/bindings/libdombindings_s.a",
                       "libxpcom_core.a": "xpcom/build/libxpcom_core.a",
                       "libucvutil_s.a": "intl/uconv/util/libucvutil_s.a",
                       "libchromium_s.a": "ipc/chromium/libchromium_s.a",
                       "libsnappy_s.a": "other-licenses/snappy/libsnappy_s.a",
                       "libgtkxtbin.a": "widget/gtkxtbin/libgtkxtbin.a",
                       "libthebes.a": "gfx/thebes/libthebes.a",
                       "libgl.a": "gfx/gl/libgl.a",
                       "libycbcr.a": "gfx/ycbcr/libycbcr.a",
                       }
        if lib.startswith('-L') or lib in system_libs:
            return lib, None
        basename = os.path.basename(lib)
        if basename in conversions:
            path = os.path.join('$(MOZ_ROOT)', conversions[basename])
            if path.endswith('.a'):
                # The actual file used by expandlibs_gen.py is either the .a
                # file, or the .a.desc file, depending on which exists. However,
                # on the command-line we have to specify just the .a file.
                dep = path + '*'
            else:
                dep = path
            return path, dep
        else:
            dep = lib + '*'
            return lib, dep

    def resolve_libraries(self, libraries):
        converted_libs = []
        deps = []
        for lib in libraries:
            arg, dep = self.resolve_library(lib)
            converted_libs.append(arg)
            if dep:
                deps.append(dep)
        return converted_libs, deps

    def generate_desc_file(self, static_library_name=None):
        lib_prefix = self.tupmk.get_var_string('LIB_PREFIX')
        lib_suffix = self.tupmk.get_var_string('LIB_SUFFIX')

        if self.tupmk.get_var('FORCE_SHARED_LIB'):
            library_name = '%s%s%s' % (self.tupmk.get_var_string('DLL_PREFIX'),
                                       self.tupmk.get_var_string('SHARED_LIBRARY_NAME'),
                                       self.tupmk.get_var_string('DLL_SUFFIX'))
            self.tupmk.set_var('@', library_name)
            inputs = ' '.join(self.objs)
            self.objs = []

            # In make, EXTRA_DSO_LIBS is converted by the EXPAND_MOZLIBNAME
            # macro called from rules.mk. We expand it here before evaluating
            # EXTRA_DSO_LDOPTS, where it is used.
            extra_dso_libs = self.tupmk.get_var_string('EXTRA_DSO_LIBS')
            if extra_dso_libs:
                extra_dso_libs = '$(MOZ_ROOT)/dist/lib/%s%s.%s' % (lib_prefix,
                                                                   extra_dso_libs,
                                                                   lib_suffix)
                self.tupmk.set_var('EXTRA_DSO_LIBS', extra_dso_libs)

            extra_dso_ldopts = self.tupmk.get_var('EXTRA_DSO_LDOPTS')

            actual_libs, lib_deps = self.resolve_libraries(extra_dso_ldopts)

            for lib in self.tupmk.get_var('SHARED_LIBRARY_LIBS'):
                # Our libraries are not in the autoconf objdir, so remove
                # that from the path.
                if self.moz_objdir in lib:
                    lib = lib.replace(self.moz_objdir + os.path.sep, '')
                lib, dep = self.resolve_library(lib)
                actual_libs.append(lib)
                if dep:
                    lib_deps.append(dep)

            lib_deps_string = ' '.join(lib_deps)

            expandlibs_exec = "$(PYTHON) $(PYTHONPATH)"
            expandlibs_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config"
            expandlibs_exec += " $(MOZ_ROOT)/config/expandlibs_exec.py"
            expandlibs_exec += " --relative-path $(MOZ_ROOT)"
            expandlibs_exec += " --target %o"
            expandlibs_exec += " " + self.tupmk.get_var_string('EXPAND_MKSHLIB_ARGS')
            expandlibs_exec += " --"
            expandlibs_exec += " " + self.tupmk.get_var_string('MKSHLIB')
            expandlibs_exec += " %f"
            expandlibs_exec += " " + self.tupmk.get_var_string('LDFLAGS')
            if self.tupmk.get_var('IS_COMPONENT'):
                expandlibs_exec += ' ' + self.tupmk.get_var_string('MOZ_COMPONENTS_VERSION_SCRIPT_LDFLAGS')
                expandlibs_exec += ' -Wl,-Bsymbolic'
            expandlibs_exec += " " + ' '.join(actual_libs)
            expandlibs_exec += " " + self.tupmk.get_var_string('OS_LIBS')

            print ": %s | %s |> ^ SHLIB %%o^ %s |> %s" % (inputs, lib_deps_string, expandlibs_exec, library_name)
        else:
            if not static_library_name:
                static_library_name = self.tupmk.get_var_string('STATIC_LIBRARY_NAME')

            if static_library_name:
                output = '%s%s.%s' % (self.tupmk.get_var_string('LIB_PREFIX'),
                                      static_library_name,
                                      self.tupmk.get_var_string('LIB_SUFFIX'))
                output_desc = '%s.%s' % (output,
                                         self.tupmk.get_var_string('LIBS_DESC_SUFFIX'))
                inputs = ' '.join(self.objs)
                cmd_inputs = ' '.join(self.objs)

                # Tup's gyp support creates files in the directory where the gyp
                # file is processed, rather than in some subdirectory like with
                # make. Therefore, we have to trim the library path to be the root
                # of the gyp directory.
                gyp_dirs = ["media/webrtc/trunk/src/modules/video_coding/codecs/vp8",
                            "media/webrtc/trunk/src/modules",
                            "media/webrtc/trunk/src/common_audio",
                            "media/webrtc/trunk/src/system_wrappers/source",
                            "media/webrtc/trunk/src/common_video",
                            "media/webrtc/trunk/src/video_engine",
                            "media/webrtc/trunk/src/voice_engine",
                            "media/webrtc/trunk/third_party/libyuv",
                            "media/mtransport/third_party/nICEr",
                            "media/mtransport/third_party/nrappkit",
                            ]

                for lib in self.tupmk.get_var('SHARED_LIBRARY_LIBS'):
                    # Our libraries are not in the autoconf objdir, so remove
                    # that from the path.
                    if self.moz_objdir in lib:
                        lib = lib.replace(self.moz_objdir + os.path.sep, '')

                    # For gyp modules, the library is in the root gyp directory.
                    for gyp_dir in gyp_dirs:
                        index = lib.find(gyp_dir)
                        if index != -1:
                            lib = os.path.join(lib[0:index + len(gyp_dir)], os.path.basename(lib))
                            break

                    # Some .a files have dist/lib, or strange paths - point them to
                    # their actual locations.
                    lib, dep = self.resolve_library(lib)

                    if dep:
                        inputs += ' %s' % (dep)
                    cmd_inputs += ' %s' % (lib)

                # Clear out the objects for any future libraries in the same
                # directory (eg: some gyp files have multiple libraries)
                self.objs = []
                print ": %s |> ^ expandlibs_gen.py %%o^ $(PYTHON) $(PYTHONPATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config $(MOZ_ROOT)/config/expandlibs_gen.py -o %%o %s --relative-path $(MOZ_ROOT) |> %s" % (inputs, cmd_inputs, output_desc)

                if self.tupmk.get_var('SDK_LIBRARY') or self.tupmk.get_var('DIST_INSTALL') or self.tupmk.get_var('NO_EXPAND_LIBS'):
                    print ": %s |> ^ expandlibs_exec.py %%o^ $(PYTHON) $(PYTHONPATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config $(MOZ_ROOT)/config/expandlibs_exec.py --relative-path $(MOZ_ROOT) --target %%o --extract -- %s %s %%o %s |> %s" % (inputs, self.tupmk.get_var_string('AR'), self.tupmk.get_var_string('AR_FLAGS'), cmd_inputs, output)

    def generate_security_library(self):
        targets = self.tupmk.get_var('TARGETS')
        objdir = self.tupmk.get_var_string('OBJDIR') + '/'

        inputs = ' '.join(self.objs)
        self.objs = []

        # See if we should build an archive (.a) file
        library = self.tupmk.get_var_string('LIBRARY')
        if library and library in targets:
            output = library.replace(objdir, '')
            ar = self.tupmk.get_var_string('AR')
            print ": %s |> ^ AR[nss] %%o^ %s %%o %%f |> %s" % (inputs, ar, output)

        # See if we should build a shared library
        shared_library = self.tupmk.get_var_string('SHARED_LIBRARY')
        if shared_library and shared_library in targets:
            output = shared_library.replace(objdir, '')

            # First process the map file into something the linker can use
            mapfile = tupmk.get_var_string('MAPFILE')
            mapfile = mapfile.replace(objdir, '')
            output_mapfile = mapfile + '.processed'
            self.tupmk.set_var('<', mapfile)
            self.tupmk.set_var('@', output_mapfile)

            process_map_file = self.tupmk.get_var_string('PROCESS_MAP_FILE')
            print ": |> ^ Generate %%o^ %s |> %s" % (process_map_file, output_mapfile)

            # Now that we have a proper map file, generate the linker rule
            self.tupmk.set_var('@', shared_library)
            self.tupmk.set_var('MAPFILE', output_mapfile)
            self.tupmk.set_var('DIST', os.path.join(self.tupmk.moz_root, 'dist'))

            extra_inputs = output_mapfile
            extra_flags = ""
            for i in ['LD_LIBS', 'EXTRA_LIBS', 'EXTRA_SHARED_LIBS', 'OS_LIBS']:
                values = self.tupmk.get_var(i)
                resolved_values, lib_deps = self.resolve_libraries(values)
                for lib in lib_deps:
                    extra_inputs += ' ' + lib
                extra_flags += ' ' + ' '.join(resolved_values)

            for i in self.tupmk.get_var('SHARED_LIBRARY_DIRS'):
                inputs += ' ' + os.path.join(i, '*.o')

            mkshlib = self.tupmk.get_var_string('MKSHLIB')
            print ": %s | %s $(MOZ_ROOT)/dist/lib/<installed-archives> |> ^ SHLIB %%o^ %s -o %%o %%f %s |> %s" % (inputs, extra_inputs, mkshlib, extra_flags, output)

    def generate_nsprpub_library(self, objs=None):
        if not objs:
            objs = self.objs
        self.objs = []

        library_name = self.tupmk.get_var_string('LIBRARY_NAME')
        library_version = self.tupmk.get_var_string('LIBRARY_VERSION')
        lib_suffix = self.tupmk.get_var_string('LIB_SUFFIX')
        dll_suffix = self.tupmk.get_var_string('DLL_SUFFIX')
        library = 'lib%s%s.%s' % (library_name, library_version, lib_suffix)
        shlib = 'lib%s%s.%s' % (library_name, library_version, dll_suffix)

        self.tupmk.set_var('@', library)
        lib_command = self.tupmk.get_var_string('AR')
        lib_command += ' ' + self.tupmk.get_var_string('AR_FLAGS')
        inputs = ' '.join(objs)
        lib_command += ' ' + inputs
        lib_command += self.tupmk.get_var_string('AR_EXTRA_ARGS')
        lib_command += ' && %s %%o' % self.tupmk.get_var_string('RANLIB')
        print ": %s |> ^ AR[nsprpub] %%o^ %s |> %s" % (inputs, lib_command, library)

        self.tupmk.set_var('@', shlib)
        mkshlib = self.tupmk.get_var_string('MKSHLIB')
        if mkshlib:
            mkshlib += ' ' + inputs
            mkshlib += ' ' + self.tupmk.get_var_string('RES')
            mkshlib += ' ' + self.tupmk.get_var_string('LDFLAGS')
            mkshlib += ' ' + self.tupmk.get_var_string('WRAP_LDFLAGS')
            extra_libs, deps = self.resolve_libraries(self.tupmk.get_var('EXTRA_LIBS'))
            mkshlib += ' ' + ' '.join(extra_libs)
            inputs += ' ' + ' '.join(deps)
            print ": %s |> ^ SHLIB[nsprpub] %%o^ %s |> %s" % (inputs, mkshlib, shlib)

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
    p.add_option('--security', action='store_true', dest='security', default=False,
                 help='Enable special treatment of security/*')
    p.add_option('-I', dest='tup_extra_includes', default=[], type=str,
                 action='append',
                 help='Extra include directories to pass to the compiler that are not in the Makefile')
    p.add_option('-m', dest='makefile', default='Makefile.in',
                 help='Optional: Name of the Makefile (defaults to Makefile.in)')

    (options, args) = p.parse_args()

    # If unspecified, build host and target srcs. This is normally the case unless a
    # host program needs to generate a file that is needed by the target sources.
    if not options.host_srcs and not options.target_srcs:
        options.host_srcs = True
        options.target_srcs = True

    moz_root = args[0]
    moz_objdir = args[1]

    tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True,
                                     makefile_name=options.makefile,
                                     need_config_mk=True,
                                     js_src=options.js_src,
                                     nsprpub=options.nsprpub,
                                     security=options.security)
    tupmk.parse('.')

    tupcpp = TupCpp(tupmk, moz_objdir,
                    host_srcs_flag=options.host_srcs,
                    target_srcs_flag=options.target_srcs,
                    extra_includes=options.tup_extra_includes,
                    js_src=options.js_src,
                    nsprpub=options.nsprpub,
                    security=options.security)

    tupcpp.generate_cpp_rules()

    if options.target_srcs:
        tupcpp.generate_desc_file()
    if options.security:
        tupcpp.generate_security_library()
    if options.nsprpub:
        tupcpp.generate_nsprpub_library()
