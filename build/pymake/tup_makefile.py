#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

class TupMakefile(object):
    def __init__(self, moz_root):
        self.autoconf_makefile = pymake.data.Makefile()
        self.autoconf_makefile.variables = pymake.data.Variables()
        self.autoconf_makefile.variables.set('srcdir', pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC, '.')

        self.context = pymake.parserdata._EvalContext(weak=False)
        self.moz_root = moz_root

        autoconf_path = os.path.join(moz_root, "autoconf.mk")
        toolkit_tiers_path = os.path.join(moz_root, "toolkit/toolkit-tiers.mk")

        self.process_makefile(self.autoconf_makefile, self.context, autoconf_path)
        self.process_makefile(self.autoconf_makefile, self.context, toolkit_tiers_path)

        # enabled_dirs is our cache of directories that are enabled. By default,
        # all directories in tier_platform_dirs are enabled. Others are set to
        # enabled when requested.
        toolkit_tiers = self.get_var('tier_platform_dirs', self.autoconf_makefile)
        self.enabled_dirs = {}
        for dirname in toolkit_tiers:
            tier = os.path.join(moz_root, dirname)
            self.enabled_dirs[tier] = True

        # TODO: Where are these enabled? They aren't part of tier_platform_dirs
        for dirname in ['browser', 'chrome']:
            tier = os.path.join(moz_root, dirname)
            self.enabled_dirs[tier] = True

    def process_makefile(self, makefile, context, filename):
        source = None

        statements = pymake.parser.parsefile(filename)

        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ['DEPTH', 'topsrcdir', 'srcdir']:
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

    def get_var(self, varname, makefile=None):
        if makefile is None:
            makefile = self.subdir_makefile

        var_tuple = makefile.variables.get(varname)
        if var_tuple is not None and var_tuple[2] is not None:
            return var_tuple[2].resolvesplit(makefile, makefile.variables)
        return []

    def check_dirs_variables(self, subdir):
        paths = os.path.split(subdir)

        parent = paths[0]
        child = paths[1]
        while True:
            # If we reached the top of the tree without finding a parent
            # Makefile.in, then we aren't enabled.
            if parent == self.moz_root:
                return False

            # If the parent directory has a Makefile.in, break out so we can
            # check if we are in its DIRS variable (and it too is enabled).
            makefile_in = os.path.join(parent, "Makefile.in")
            if os.path.exists(makefile_in):

                # Parent not enabled means we aren't either
                if not self.makefile_is_enabled(parent):
                    return False

                # Check parent's DIRS variables for our name
                tmpmakefile = copy.deepcopy(self.autoconf_makefile)
                self.process_makefile(tmpmakefile, self.context, makefile_in)

                dirs = self.get_var('DIRS', tmpmakefile)
                dirs.extend(self.get_var('PARALLEL_DIRS', tmpmakefile))
                dirs.extend(self.get_var('TOOL_DIRS', tmpmakefile))
                dirs.extend(self.get_var('TEST_DIRS', tmpmakefile))
                if dirs and child in dirs:
                    return True
                return False

            # Recurse up the tree looking for a parent Makefile.in
            paths = os.path.split(parent)
            parent = paths[0]
            child = os.path.join(paths[1], child)

    def makefile_is_enabled(self, subdir):
        """
        Make sure that this Makefile.in is in a relevant DIRS variable of a parent.
        """

        if subdir not in self.enabled_dirs:
            self.enabled_dirs[subdir] = self.check_dirs_variables(subdir)

        return self.enabled_dirs[subdir]

    def parse(self, subdir):
        self.subdir_makefile = copy.deepcopy(self.autoconf_makefile)
        if self.makefile_is_enabled(subdir):
            makefile_in = os.path.join(subdir, "Makefile.in")
            self.process_makefile(self.subdir_makefile, self.context, makefile_in)
