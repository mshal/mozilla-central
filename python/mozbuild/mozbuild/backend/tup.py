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
    p.add_option('--js-src', action='store_true', dest='js_src', default=False,
                 help='Enable special treatment of js/src/*')
    p.add_option('--nsprpub', action='store_true', dest='nsprpub', default=False,
                 help='Enable special treatment of nsprpub/*')
    p.add_option('--security', action='store_true', dest='security', default=False,
                 help='Enable special treatment of security/*')
    p.add_option('--extra-manifest-files', action='append',
                 dest='extra_manifest_files', default=[],
                 help='Extra jar.mn files to process in addition to ./jar.mn')
    p.add_option('--always-enabled', action='store_true',
                 dest='always_enabled', default=False,
                 help='Always consider this directory to be enabled, even if it is not in a tiers dir or a subdirectory of one.')
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

    mozbuild = False
    make = False
    if os.path.exists('moz.build'):
        mozbuild = True
    if os.path.exists('Makefile.in'):
        make = True
        makefile_name = 'Makefile.in'
    elif os.path.exists('Makefile'):
        make = True
        makefile_name = 'Makefile'

    if not mozbuild and not make:
        sys.exit(0)

    sys.path.append(os.path.join(os.getcwd(), moz_root, 'python', 'mozbuild'))
    sys.path.append(os.path.join(os.getcwd(), moz_root, 'config'))
    from mozbuild.backend.configenvironment import ConfigEnvironment
    from tup import mozbuildmakesandbox

    config_status = os.path.join(moz_root, moz_objdir, 'config.status')
    env = ConfigEnvironment.from_config_status(config_status)

    root_path = os.path.normpath(os.path.join(os.getcwd(), moz_root))
    # Make sure include('/foo') is in the tup directory, rather than the root fs
    # until tup is fixed.
    env.topsrcdir = root_path

    mozbuild_file = os.path.join(os.getcwd(), 'moz.build')
    sandbox = mozbuildmakesandbox.MozbuildMakeSandbox(env, mozbuild_file, moz_root,
                                                      moz_objdir,
                                                      options.tup_extra_includes)

    if mozbuild and not options.always_enabled:
        direnabled = sandbox.mozbuild_enabled(os.getcwd(), env.topsrcdir)
    else:
        direnabled = True

    if not direnabled:
        sys.exit(0)

    sys.path.append(os.path.join(os.getcwd(), moz_root, 'build', 'pymake'))
    from tup import makefile_parser
    if mozbuild:
        sandbox.exec_file(mozbuild_file, filesystem_absolute=True)
    if make:
        makefile_parser.parse(sandbox, makefile_name)
    else:
        # We at least need config.mk
        makefile_parser.parse(sandbox, None)

    # Custom rules in Makefile.in need special treatment
    if sandbox.relativesrcdir == 'toolkit/components/urlformatter':
        from tup import urlformatter
        urlformatter.generate_rules(sandbox)
    elif sandbox.relativesrcdir.startswith('nsprpub'):
        from tup import nspr
        nspr.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'config':
        from tup import config
        config.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'js/xpconnect/src':
        from tup import js_xpconnect_src
        js_xpconnect_src.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'dom/encoding':
        from tup import domencoding
        domencoding.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'gfx/thebes':
        from tup import gfx_thebes
        gfx_thebes.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'intl/locale/src':
        from tup import intl_locale_src
        intl_locale_src.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'js/src':
        from tup import js_src
        js_src.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'netwerk/dns':
        from tup import netwerk_dns
        netwerk_dns.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'media/libvpx':
        from tup import media_libvpx
        media_libvpx.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'media/libjpeg':
        from tup import media_libjpeg
        media_libjpeg.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'build':
        from tup import build
        build.generate_rules(sandbox)
    elif sandbox.relativesrcdir == 'security/nss/lib/ckfw/builtins':
        from tup import ckfw_builtins
        ckfw_builtins.generate_rules(sandbox)

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
    if 'CSRCS' in sandbox:
        from tup import csrcs
        csrcs.generate_rules(sandbox)
    if 'ASFILES' in sandbox:
        from tup import asm
        asm.generate_rules(sandbox)
    if 'CPP_UNIT_TESTS' in sandbox:
        from tup import cppunittests
        cppunittests.generate_rules(sandbox)
    if os.path.exists('jar.mn'):
        from tup import jarmn
        jarmn.generate_rules(sandbox)
    if 'NO_DIST_INSTALL' not in sandbox:
        from tup import distinstall
        distinstall.generate_rules(sandbox)

    # Needs to come after since freebl is parsed twice - once with
    # FREEBL_CHILD_BUILD set and once without
    if sandbox.relativesrcdir == 'security/nss/lib/freebl':
        from tup import freebl
        freebl.generate_rules(sandbox)
