#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

def process_makefile(makefile, context, filename):
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

def get_var(makefile, varname):
    var_tuple = makefile.variables.get(varname)
    if var_tuple is not None and var_tuple[2] is not None:
        return var_tuple[2].resolvesplit(makefile, makefile.variables)
    return None

ac_makefile = pymake.data.Makefile()
ac_makefile.variables = pymake.data.Variables()
context = pymake.parserdata._EvalContext(weak=False)

if len(sys.argv) < 3:
    sys.exit('usage: %s path/to/autoconf.mk sub/dir1 [sub/dir2...]')
autoconf_mk = sys.argv[1]

process_makefile(ac_makefile, context, autoconf_mk)

for subdir in sys.argv[2:]:
    subdir_makefile = copy.deepcopy(ac_makefile)
    makefile_in = os.path.join(subdir, "Makefile.in")
    process_makefile(subdir_makefile, context, makefile_in)
    # TODO: If --xpidl is set? only should happen in dist/idl
    # TODO: Bug 698251 for SDK_XPIDLSRCS
    for varname in ['XPIDLSRCS', 'SDK_XPIDLSRCS']:
        xpidl = get_var(subdir_makefile, varname)
        if xpidl is not None:
            # Create a tup :-rule for each symlink to an .idl file that we need.
            print ": foreach ",
            for i in xpidl:
                print os.path.join(subdir, i),
            print " |> !ln |> %b <installed-idls>"
