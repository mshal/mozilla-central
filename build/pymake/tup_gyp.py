#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
from optparse import OptionParser

if len(sys.argv) < 4:
    sys.exit('usage: %s file.gyp MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

p = OptionParser()
p.add_option('-D', dest='gyp_extra_defines', default=[], type=str,
             action='append',
             help='Extra defines to pass to the gyp parser')

(options, args) = p.parse_args()

gyp_file = args[0]
moz_root = args[1]
moz_objdir = args[2]

sys.path.insert(0, os.path.join(moz_root, 'media', 'webrtc', 'trunk', 'tools', 'gyp', 'pylib'))
import gyp

args = []
args.append('--format=moztup')

args.append('-D')
args.append('build_with_mozilla=1')

for define in options.gyp_extra_defines:
    args.append('-D')
    args.append(define)

args.append('--include')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'webrtc_config.gypi'))

args.append('--depth')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'trunk'))

args.append('-G')
args.append('MOZ_ROOT=' + moz_root)

args.append('-G')
args.append('MOZ_OBJDIR=' + moz_objdir)

# This normally gets added by the gyp_chromium program, but we skip that here.
args.append('--include')
args.append(os.path.join(moz_root, 'media', 'webrtc', 'trunk', 'build', 'common.gypi'))

# Call out to gyp, which will call out to moztup.py to actually generate the tup
# rules.
gyp.gyp_main(args)
