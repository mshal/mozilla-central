#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    from tup import makefile_parser
    sandbox.set_var('FREEBL_CHILD_BUILD', '1')
    sandbox.makefile = None
    makefile_parser.parse(sandbox, 'Makefile')

    targets = sandbox.makefile.makefile._targets

    # Both OBJDIR and OBJ_SUFFIX have strange values that we aren't expecting,
    # so the target in the Makefile doesn't match the target that we are looking
    # for, but we need its target-specific compiler flags.
    filename = '%s/%sintel-gcm-wrap%s' % (
        sandbox.get_string('OBJDIR'),
        sandbox.get_string('PROG_PREFIX'),
        sandbox.get_string('OBJ_SUFFIX')
    )
    targets['intel-gcm-wrap.o'] = targets[filename]

    from tup import csrcs
    csrcs.generate_rules(sandbox)
    return
