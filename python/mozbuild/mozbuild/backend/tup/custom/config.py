#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import Preprocessor
import StringIO

def generate_rules(sandbox):
    if sandbox['WRAP_SYSTEM_INCLUDES']:
        preprocessed_data = StringIO.StringIO()
        pp = Preprocessor.Preprocessor()
        pp.out = preprocessed_data

        args = []
        args.append('system-headers')

        pp.handleCommandLine(args, False)
        preprocessed_data.seek(0)
        outputs = {}
        for line in preprocessed_data.readlines():
            line = line.strip()
            if len(line) > 0:
                if line not in outputs:
                    outputs[line] = 1

        for header in outputs:
            print ": |> ^ System wrapper: %s^ (echo '#pragma GCC system_header'; echo '#pragma GCC visibility push(default)'; echo '#include_next <%s>'; echo '#pragma GCC visibility pop') > '%%o' |> $(DIST)/system_wrappers/%s | $(MOZ_ROOT)/<installed-headers>" % (header, header, header)

    if sandbox['WRAP_STL_INCLUDES']:
        f = open('stl-headers')
        lines = [line.strip() for line in f.readlines()]
        f.close()

        # Get a list of the headers from stl-headers. Prune out all the comments
        # and blank lines
        headers = []
        for line in lines:
            if not line.startswith('#') and len(line) > 0:
                headers.append('$(DIST)/stl_wrappers/%s' % (line))

        stl_compiler = sandbox.get_string('stl_compiler')
        outputs = ' '.join(headers)
        print ": |> $(PYTHON) make-stl-wrappers.py $(DIST)/stl_wrappers %s %s-stl-wrapper.template.h stl-headers |> %s | $(MOZ_ROOT)/<installed-headers>" % (stl_compiler, stl_compiler, outputs)
