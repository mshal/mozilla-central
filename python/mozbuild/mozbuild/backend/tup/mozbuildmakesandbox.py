#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
from mozbuild.frontend.reader import MozbuildSandbox

class MozbuildMakeSandbox(MozbuildSandbox):
    """Support class to handle both moz.build and Makefile.in variables
    at the same time.
    """
    def __init__(self, config, path, moz_root):
        MozbuildSandbox.__init__(self, config, path)
        self.makefile = None
        self.objs = []
        self.moz_root = moz_root

    def get_string(self, name):
        value = self[name]
        if type(value) == list:
            return ' '.join(value)
        return value

    def vpath_resolve(self, filename):
        if self.makefile:
            return self.makefile.vpath_resolve('.', self['VPATH'], filename)
        return filename

    def __getitem__(self, name):
        if self.makefile:
            value = self.makefile.get_var(name)
            if value:
                return value

        try:
            return super(MozbuildMakeSandbox, self).__getitem__(name)
        except KeyError:
            pass

        return []
