#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

if len(sys.argv) < 2:
    sys.exit('usage: %s MOZ_ROOT' % sys.argv[0])

moz_root = sys.argv[1]

f = open(os.path.join(moz_root, 'config/stl-headers'))
lines = [line.strip() for line in f.readlines()]
f.close()

# Get a list of the headers from stl-headers. Prune out all the comments and
# blank lines
headers = []
for line in lines:
    if not line.startswith('#') and len(line) > 0:
        headers.append(line)

print ": |> $(PYTHON) $(MOZ_ROOT)/config/make-stl-wrappers.py . $(stl_compiler) $(MOZ_ROOT)/config/$(stl_compiler)-stl-wrapper.template.h $(MOZ_ROOT)/config/stl-headers |> " + ' '.join(headers) + ' | $(MOZ_ROOT)/dist/include/<installed-headers>'
