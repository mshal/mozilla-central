#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
from mozbuild.frontend.reader import MozbuildSandbox

class MozbuildMakeSandbox(MozbuildSandbox):
    """Support class to handle both moz.build and Makefile.in variables
    at the same time.
    """
    def __init__(self, config, path, moz_root, moz_objdir):
        MozbuildSandbox.__init__(self, config, path)
        self.makefile = None
        self.objs = []
        self.moz_root = moz_root
        self.moz_objdir = moz_objdir
        self.variables = {}

        # Get the path relative to moz_root by finding the components of cwd
        # using the length of moz_root. Eg, if our cwd is
        # HOME/m-c/xpcom/base, then moz_root is "../..", so we count one '/'
        # in moz_root, and add one to it so path_count is 2. We pull off the
        # last 2 parts of cwd to get "xpcom/base", and prefixed with
        # moz_root becomes "../../xpcom/base".
        cwd = os.getcwd()
        cwd_parts = cwd.split('/')
        path_count = moz_root.count('/') + 1
        self.relativesrcdir = os.path.join(*cwd_parts[-path_count:])
        self.outputdir = os.path.join(moz_root, moz_objdir, self.relativesrcdir)

        self.set_var('abs_srcdir', os.path.join(moz_root, self.relativesrcdir))
        self.set_var('relativesrcdir', self.relativesrcdir)
        self.set_var('topsrcdir', self.moz_root)
        self.set_var('DIST', os.path.join(moz_root, moz_objdir, 'dist'))
        self.set_var('AB_CD', self.get_string('MOZ_UI_LOCALE'))
        self.set_var('LOCALE_SRCDIR', 'en-US')
        self.set_var('ACDEFINES', self.config.substs['ACDEFINES'].split(' '))

    def set_var(self, name, value):
        if type(value) == list:
            self.variables[name] = value
        else:
            self.variables[name] = [value]

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
        if name in self.variables:
            return self.variables[name]

        if self.makefile:
            value = self.makefile.get_var(name)
            if value is not None:
                return value

        try:
            return super(MozbuildMakeSandbox, self).__getitem__(name)
        except KeyError:
            pass

        if name in self.config.defines:
            return [self.config.defines[name]]
        if name in self.config.substs:
            return [self.config.substs[name]]

        return []
