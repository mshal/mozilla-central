#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

class TupMakefile(object):
    def __init__(self, autoconf_path):
        self.autoconf_makefile = pymake.data.Makefile()
        self.autoconf_makefile.variables = pymake.data.Variables()
        self.context = pymake.parserdata._EvalContext(weak=False)

        self.process_makefile(self.autoconf_makefile, self.context, autoconf_path)

    def process_makefile(self, makefile, context, filename):
        source = None

        statements = pymake.parser.parsefile(filename)

        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ['DEPTH', 'topsrcdir', 'srcdir', 'VPATH']:
                    continue

                s.execute(makefile, context)
            elif isinstance(s, pymake.parserdata.Include):
                # Includes are ignored. We just want the variable data from
                # Makefile.in
                continue
            elif isinstance(s, pymake.parserdata.ConditionBlock):
                s.execute(makefile, context)
    #        else:
    #            print >> sys.stderr, "[33mStatement: [0m", s

    def get_var(self, varname):
        var_tuple = self.subdir_makefile.variables.get(varname)
        if var_tuple is not None and var_tuple[2] is not None:
            return var_tuple[2].resolvesplit(self.subdir_makefile, self.subdir_makefile.variables)
        return None

    def parse(self, subdir):
        self.subdir_makefile = copy.deepcopy(self.autoconf_makefile)
        makefile_in = os.path.join(subdir, "Makefile.in")
        self.process_makefile(self.subdir_makefile, self.context, makefile_in)
