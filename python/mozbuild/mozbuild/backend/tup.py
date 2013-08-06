#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
from optparse import OptionParser

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
    p.add_option('--gyp-file', action='store', dest='gypfile',
                 default=None,
                 help='Gyp file to process, it any.')
    p.add_option('--extra-manifest-files', action='append',
                 dest='extra_manifest_files', default=[],
                 help='Extra jar.mn files to process in addition to ./jar.mn')
    p.add_option('--always-enabled', action='store_true',
                 dest='always_enabled', default=False,
                 help='Always consider this directory to be enabled, even if it is not in a tiers dir or a subdirectory of one.')
    p.add_option('-I', dest='tup_extra_includes', default=[], type=str,
                 action='append',
                 help='Extra include directories to pass to the compiler that are not in the Makefile')
    p.add_option('-D', dest='gyp_extra_defines', default=[], type=str,
                 action='append',
                 help='Extra defines to pass to the gyp processor.')
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

    mozbuild = False
    make = False
    gyp = False
    if os.path.exists('moz.build'):
        mozbuild = True
    if os.path.exists('Makefile.in'):
        make = True
        makefile_name = 'Makefile.in'
    elif os.path.exists('Makefile'):
        make = True
        makefile_name = 'Makefile'

    if options.gypfile:
        gyp = True

    if not mozbuild and not make and not gyp:
        sys.exit(0)

    sys.path.append(os.path.join(os.getcwd(), moz_root, 'python', 'mozbuild'))
    sys.path.append(os.path.join(os.getcwd(), moz_root, 'config'))
    from mozbuild.backend.configenvironment import ConfigEnvironment
    from tup import mozbuildmakesandbox

    # Get the path relative to moz_root by finding the components of cwd using
    # the length of moz_root. Eg, if our cwd is HOME/m-c/xpcom/base, then
    # moz_root is "../..", so we count one '/' in moz_root, and add one to it so
    # path_count is 2. We pull off the last 2 parts of cwd to get "xpcom/base",
    # and prefixed with moz_root becomes "../../xpcom/base".
    cwd = os.getcwd()
    cwd_parts = cwd.split('/')
    path_count = moz_root.count('/') + 1
    relativesrcdir = os.path.join(*cwd_parts[-path_count:])

    if relativesrcdir.startswith('js/src'):
        # We need the main config.status in order to load the correct tiers,
        # then we need js/src/config.status to get the separate js/src
        # variables.
        config_status = os.path.join(moz_root, moz_objdir, 'js', 'src', 'config.status')

        # We can't properly parse moz.build files if we use js' config.status,
        # but we don't have the right substs (like JS_SHELL_NAME) if we don't
        # use js' config.status.  I have no idea how this works correctly with
        # make, but it's a pain for us.
        options.always_enabled = True
    else:
        config_status = os.path.join(moz_root, moz_objdir, 'config.status')
    env = ConfigEnvironment.from_config_status(config_status)

    root_path = os.path.normpath(os.path.join(os.getcwd(), moz_root))
    # Make sure include('/foo') is in the tup directory, rather than the root fs
    # until tup is fixed.
    env.topsrcdir = root_path

    mozbuild_file = os.path.join(os.getcwd(), 'moz.build')
    sandbox = mozbuildmakesandbox.MozbuildMakeSandbox(env, mozbuild_file, moz_root,
                                                      moz_objdir,
                                                      options.tup_extra_includes,
                                                      relativesrcdir)

    if mozbuild and not options.always_enabled:
        direnabled = sandbox.mozbuild_enabled(os.getcwd(), env.topsrcdir)
    else:
        direnabled = True

    if not direnabled:
        sys.exit(0)

    sys.path.append(os.path.join(os.getcwd(), moz_root, 'build', 'pymake'))
    from tup import makefile_parser

    if gyp:
        from tup import tupgyp
        tupgyp.generate_rules(sandbox, options.gypfile, options.gyp_extra_defines)
        sys.exit(0)

    if mozbuild:
        sandbox.exec_file(mozbuild_file, filesystem_absolute=True)
    if make:
        makefile_parser.parse(sandbox, makefile_name)
    else:
        # We at least need config.mk
        makefile_parser.parse(sandbox, None)

    # Custom rules in Makefile.in need special treatment
    if sandbox.relativesrcdir == 'toolkit/components/urlformatter':
        from tup.custom import urlformatter
        urlformatter.generate_rules(sandbox)
    elif sandbox.relativesrcdir.startswith('nsprpub'):
        from tup.custom import nspr
        nspr.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'config':
        from tup.custom import config
        config.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'js/xpconnect/src':
        from tup.custom import js_xpconnect_src
        js_xpconnect_src.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'dom/encoding':
        from tup.custom import dom_encoding
        dom_encoding.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'gfx/thebes':
        from tup.custom import gfx_thebes
        gfx_thebes.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'intl/locale/src':
        from tup.custom import intl_locale_src
        intl_locale_src.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'netwerk/dns':
        from tup.custom import netwerk_dns
        netwerk_dns.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'media/libvpx':
        from tup.custom import media_libvpx
        media_libvpx.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'media/libjpeg':
        from tup.custom import media_libjpeg
        media_libjpeg.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'build':
        from tup.custom import build
        build.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'security/nss/lib/ckfw/builtins':
        from tup.custom import ckfw_builtins
        ckfw_builtins.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'intl/locale/src/unix':
        from tup.custom import intl_locale_src_unix
        intl_locale_src_unix.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'js/src/ctypes/libffi':
        from tup.custom import libffi
        libffi.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'toolkit/library':
        from tup.custom import toolkit_library
        toolkit_library.generate_rules(sandbox)

    if 'all_webidl_files' in sandbox:
        from tup import dombindings
        dombindings.generate_rules(sandbox)
    if 'XPIDL_SOURCES' in sandbox:
        from tup import xpidl
        xpidl.generate_rules(sandbox)
    if 'EXPORTS' in sandbox:
        from tup import exports
        exports.generate_rules(sandbox)
    if 'PRIVATE_EXPORTS' in sandbox:
        from tup import private_exports
        private_exports.generate_rules(sandbox)
    if 'EXPORTS_NAMESPACES' in sandbox:
        from tup import oldexports
        oldexports.generate_rules(sandbox)
    if 'CPP_SOURCES' in sandbox:
        from tup import cppsrcs
        cppsrcs.generate_rules(sandbox)
    if 'CPPSRCS' in sandbox:
        from tup import oldcppsrcs
        oldcppsrcs.generate_rules(sandbox)
    if 'CSRCS' in sandbox:
        from tup import csrcs
        csrcs.generate_rules(sandbox)
    if 'HOST_CPPSRCS' in sandbox:
        from tup import host_cppsrcs
        host_cppsrcs.generate_rules(sandbox)
    if 'HOST_CSRCS' in sandbox:
        from tup import host_csrcs
        host_csrcs.generate_rules(sandbox)
    if 'HOST_SIMPLE_PROGRAMS' in sandbox:
        from tup import host_simple_programs
        host_simple_programs.generate_rules(sandbox)
    if 'ASFILES' in sandbox:
        from tup import asm
        asm.generate_rules(sandbox)
    if 'CPP_UNIT_TESTS' in sandbox:
        from tup import cppunittests
        cppunittests.generate_rules(sandbox)
    if 'GTEST_CPP_SOURCES' in sandbox:
        from tup import gtest_cpp_sources
        gtest_cpp_sources.generate_rules(sandbox)
    if os.path.exists('jar.mn'):
        from tup import jarmn
        jarmn.generate_rules(sandbox)
    if 'NO_DIST_INSTALL' not in sandbox:
        from tup import distinstall
        distinstall.generate_rules(sandbox)

    objs = sandbox['OBJS']
    if not objs:
        objs = sandbox.objs

    objs = ['%s/%s' % (sandbox.outputdir, o) for o in objs]
    from tup import linker
    linker.generate_rules(sandbox, objs)

    # Needs to come after since freebl is parsed twice - once with
    # FREEBL_CHILD_BUILD set and once without
    if sandbox.relativesrcdir == 'security/nss/lib/freebl':
        from tup.custom import freebl
        freebl.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'js/src':
        from tup.custom import js_src
        js_src.generate_rules(sandbox)
