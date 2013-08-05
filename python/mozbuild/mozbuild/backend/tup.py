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
                                                      moz_objdir)

    if mozbuild:
        direnabled = sandbox.mozbuild_enabled(os.getcwd(), env.topsrcdir)
    else:
        direnabled = True

    if not direnabled:
        sys.exit(0)

    if mozbuild:
        sandbox.exec_file(mozbuild_file, filesystem_absolute=True)
    if make:
        sys.path.append(os.path.join(os.getcwd(), moz_root, 'build', 'pymake'))
        from tup import makefile_parser
        makefile_parser.parse(sandbox)

    if 'XPIDL_SOURCES' in sandbox:
        from tup import xpidl
        xpidl.generate_rules(sandbox)
    if 'EXPORTS' in sandbox:
        from tup import exports
        exports.generate_rules(sandbox)
    if 'ASFILES' in sandbox:
        from tup import asm
        asm.generate_rules(sandbox)
    if os.path.exists('jar.mn'):
        from tup import jarmn
        jarmn.generate_rules(sandbox)
