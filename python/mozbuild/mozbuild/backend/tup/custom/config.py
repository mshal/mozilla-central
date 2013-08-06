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

        args = sandbox['DEFINES']
        args.extend(sandbox['ACDEFINES'])
        for i in [
            'MOZ_TREE_CAIRO',
            'MOZ_TREE_PIXMAN',
            'MOZ_NATIVE_HUNSPELL',
            'MOZ_NATIVE_BZ2',
            'MOZ_NATIVE_ZLIB',
            'MOZ_NATIVE_PNG',
            'MOZ_NATIVE_JPEG',
            'MOZ_NATIVE_LIBEVENT',
            'MOZ_NATIVE_LIBVPX',
        ]:
            args.append('-D%s=%s' % (i, sandbox.get_string(i)))
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

    # Some files (at least media/webrtc/signaling/) include this manually, so
    # they need to find it in dist/include. Unsure if that is really necessary,
    # since it is also -include'd directly on the command-line.
    print ": $(MOZ_ROOT)/@(MOZ_OBJDIR)/mozilla-config.h |> ^ INSTALL %f^ cp %f %o |> $(DIST)/include/%b | $(MOZ_ROOT)/<installed-headers>"
