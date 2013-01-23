#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import Preprocessor
import StringIO

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT directory' % sys.argv[0])

moz_root = sys.argv[1]
subdir = sys.argv[2]

preprocessed_data = StringIO.StringIO()
pp = Preprocessor.Preprocessor()
pp.out = preprocessed_data

args = sys.argv[3:]
args.append(os.path.join(moz_root, 'config/system-headers'))

pp.handleCommandLine(args, False)
preprocessed_data.seek(0)
outputs = {}
for line in preprocessed_data.readlines():
    line = line.strip()
    if len(line) > 0:
        if subdir == '.' and line.find('/') == -1:
            if line not in outputs:
                outputs[line] = line
        elif line.startswith(subdir) and line[len(subdir)+1:].find('/') == -1:
            if line not in outputs:
                outputs[line] = line[len(subdir)+1:]

for header in outputs:
    print ": |> ^ System wrapper: %s^ (echo '#pragma GCC system_header'; echo '#pragma GCC visibility push(default)'; echo '#include_next <%s>'; echo '#pragma GCC visibility pop') > '%%o' |> %s | $(MOZ_ROOT)/dist/include/<installed-headers>" % (header, header, outputs[header])
