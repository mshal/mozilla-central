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
    def __init__(self, config, path):
        MozbuildSandbox.__init__(self, config, path)
        self.makevars = {}

    def __getitem__(self, name):
        if name in self.makevars:
            return self.makevars[name]

        try:
            return super(MozbuildMakeSandbox, self).__getitem__(name)
        except KeyError:
            pass

        return []

    def __setitem__(self, name, value):
        if name in self.makevars:
            self.makevars[name] = value
            return

        try:
            return self._globals.__setitem__(name, value)
        # For things not yet in moz.build
        except KeyError:
            pass
        # For things that moz.build supports but may still be in a Makefile
        except ValueError:
            pass

        self.makevars[name] = value
