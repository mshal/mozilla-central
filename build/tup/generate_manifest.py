#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

if len(sys.argv) < 2:
    sys.exit('usage: %s [manifest file]' % sys.argv[0])

# We are given a filename which has a list of files that were created
# by JarMaker.py. Among these files are .manifest files, which we
# concatenate together to create the output (which we write to stdout)
with open(sys.argv[1], 'r') as f:
    for line in f:
        line = line.strip()
        if line.endswith('.manifest'):
            with open(line, 'r') as inf:
                for inline in inf:
                    print inline,
                    # TODO: Remove duplicate lines
