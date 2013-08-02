#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox, gyp_file, gyp_extra_defines):
    sys.path.insert(0, os.path.join(sandbox.moz_root, 'media', 'webrtc', 'trunk', 'tools', 'gyp', 'pylib'))
    import gyp

    gyp_args = []
    gyp_args.append('--format=moztup')

    gyp_args.append('-D')
    gyp_args.append('build_with_mozilla=1')

    gyp_args.append('-D')
    gyp_args.append('build_with_chromium=0')

    gyp_args.append('-D')
    if sandbox['HAVE_CLOCK_MONOTONIC']:
        gyp_args.append('have_clock_monotonic=1')
    else:
        gyp_args.append('have_clock_monotonic=0')

    for define in gyp_extra_defines:
        gyp_args.append('-D')
        gyp_args.append(define)

    gyp_args.append('--include')
    gyp_args.append(os.path.join(sandbox.moz_root, 'media', 'webrtc', 'webrtc_config.gypi'))

    gyp_args.append('--depth')
    gyp_args.append(os.path.join(sandbox.moz_root, 'media', 'webrtc', 'trunk'))

    gyp_args.append('-G')
    gyp_args.append('MOZ_ROOT=' + sandbox.moz_root)

    gyp_args.append('-G')
    gyp_args.append('MOZ_OBJDIR=' + sandbox.moz_objdir)

    gyp_args.append('-G')
    gyp_args.append('OUTPUTDIR=' + sandbox.outputdir)

    # These normally get added by the gyp_chromium program, but we are using
    # gyp_main() directly.
    gyp_args.append('--include')
    gyp_args.append(os.path.join(sandbox.moz_root, 'media', 'webrtc', 'trunk', 'build', 'common.gypi'))

    gyp_dir = os.path.dirname(gyp_file)
    supplement = os.path.join(gyp_dir, 'supplement', 'supplement.gypi')
    if os.path.exists(supplement):
        gyp_args.append('--include')
        gyp_args.append(supplement)

    gyp_args.append(gyp_file)

    # Call out to gyp, which will call out to moztup.py to actually generate the tup
    # rules.
    gyp.gyp_main(gyp_args)
