#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile

if len(sys.argv) < 4:
    sys.exit('usage: %s file.gyp MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

gyp_file = sys.argv[1]
moz_root = sys.argv[2]
moz_objdir = sys.argv[3]

sys.path.insert(0, os.path.join(moz_root, 'media', 'webrtc', 'trunk', 'tools', 'gyp', 'pylib'))
import gyp

tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir)

if tupmk.get_var_string('MOZ_DEBUG', makefile=tupmk.autoconf_makefile) == '1':
    debug = True
else:
    debug = False

args = []
args.append('--format=moztup')

args.append('-D')
args.append('build_with_mozilla=1')

args.append('--include')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'webrtc_config.gypi'))

args.append('--depth')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'trunk'))

if debug:
    args.append('-G')
    args.append('MOZ_DEBUG')

args.append('-G')
args.append('MOZ_ROOT=' + moz_root)

args.append('-G')
args.append('CC=' + tupmk.get_var_string('CC', makefile=tupmk.autoconf_makefile))

args.append('-G')
args.append('OBJ_SUFFIX=' + tupmk.get_var_string('OBJ_SUFFIX', makefile=tupmk.autoconf_makefile))

# This normally gets added by the gyp_chromium program, but we skip that here.
args.append('--include')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'trunk', 'build', 'common.gypi'))

# Call out to gyp, which will call out to moztup.py to actually generate the tup
# rules.
gyp.gyp_main(args)
