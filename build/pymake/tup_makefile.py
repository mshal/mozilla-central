#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

class TupMakefile(object):
    def __init__(self, moz_root, moz_objdir, makefile_name='Makefile.in',
                 allow_includes=False, always_enabled=False, need_config_mk=False):
        self.autoconf_makefile = pymake.data.Makefile()
        self.autoconf_makefile.variables = pymake.data.Variables()
        self.autoconf_makefile.variables.set('srcdir',
                                             pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC,
                                             '.')
        self.autoconf_makefile.variables.set('topsrcdir',
                                             pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC,
                                             moz_root)
        self.autoconf_makefile.variables.set('DEPTH',
                                             pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC,
                                             os.path.join(moz_root, moz_objdir))
        self.autoconf_makefile.variables.set('DIST',
                                             pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC,
                                             os.path.join(moz_root, 'dist'))

        # This determines whether or not to include makeutils.mk in
        # package-name.mk, and we don't need makeutils.mk
        self.autoconf_makefile.variables.set('INCLUDED_RCS_MK',
                                             pymake.data.Variables.FLAVOR_SIMPLE,
                                             pymake.data.Variables.SOURCE_AUTOMATIC,
                                             '1')

        self.context = pymake.parserdata._EvalContext(weak=False)
        self.moz_root = moz_root
        self.makefile_name = makefile_name
        self.always_enabled = always_enabled
        self.need_config_mk = need_config_mk

        autoconf_path = os.path.join(moz_root, moz_objdir, "config/autoconf.mk")
        browser_build_mk = os.path.join(moz_root, "browser/build.mk")
        root_makefile_path = os.path.join(moz_root, "Makefile.in")

        self.allow_includes = True
        self.process_makefile(self.autoconf_makefile, self.context, autoconf_path)
        self.process_makefile(self.autoconf_makefile, self.context, browser_build_mk)
        self.allow_includes = False
        self.process_makefile(self.autoconf_makefile, self.context, root_makefile_path)
        self.allow_includes = allow_includes

        # enabled_dirs is our cache of directories that are enabled. By default,
        # all directories in tier_platform_dirs are enabled. Others are set to
        # enabled when requested.
        base_directories = self.get_var('tier_platform_dirs', self.autoconf_makefile)
        base_directories.extend(self.get_var('tier_app_dirs', self.autoconf_makefile))
        base_directories.extend(self.get_var('tier_base_dirs', self.autoconf_makefile))

        self.enabled_dirs = {}
        for dirname in base_directories:
            tier = os.path.join(moz_root, dirname)
            self.enabled_dirs[tier] = True

        # TODO: Where are these enabled? They aren't part of tier_platform_dirs
        for dirname in [
                'chrome',
                'db/sqlite3/src',
                'js/src',
                'security/nss',
                ]:
            tier = os.path.join(moz_root, dirname)
            self.enabled_dirs[tier] = True

    def process_statements(self, makefile, context, dirname, statements):
        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ['DEPTH', 'topsrcdir', 'srcdir']:
                    continue

                s.execute(makefile, context)
            elif isinstance(s, pymake.parserdata.Include):
                # Includes are generally ignored. The Makefiles in security/nss
                # are an exception, since much of the data is actually defined
                # in security/coreconf/* and the manifest.mn files, which are
                # included by the Makefile.
                if self.allow_includes:
                    include_filename = s.exp.to_source()
                    if '/rules.mk' in include_filename:
                        # Ignore rules.mk, since we are doing our own tup-based
                        # rules, but make sure we get config.mk if it hasn't
                        # already been included. Some Makefile.in's include this
                        # manually, while others rely on rules.mk including it.
                        # Since we don't include rules.mk, we won't pick it up
                        # in that case.
                        #
                        # Note that extra parsing of config.mk when it's not
                        # needed can greatly slow down some cases (such as
                        # dist/include), so we only grab it if need_config_mk is
                        # set.
                        if self.need_config_mk and not self.get_var('INCLUDED_CONFIG_MK', makefile):
                            config_mk = os.path.join(self.moz_root, 'config/config.mk')
                            self.process_makefile(makefile, context, config_mk)
                        continue
                    elif '/baseconfig.mk' in include_filename:
                        # Ignore baseconfig.mk
                        continue
                    elif '$(MKDEPENDENCIES)' in include_filename:
                        # Make dependencies aren't needed for tup, and this
                        # variable may not be defined (in
                        # security/coreconf/config.mk)
                        continue
                    elif '$(DEPENDENCIES)' in include_filename:
                        # Similar to MKDEPENDENCIES, but now in
                        # security/coreconf/rules.mk
                        continue
                    elif 'autoconf.mk' in include_filename:
                        # We already include this file automatically, so skip
                        # any lines that try to include it again.
                        continue
                    elif 'app-config.mk' in include_filename:
                        # This file doesn't seem to exist, and is only included
                        # with -include
                        continue
                    elif 'MY_CONFIG' in include_filename:
                        # This file doesn't seem to exist, and is only included
                        # with -include
                        continue
                    else:
                        files = s.exp.resolvesplit(makefile, makefile.variables)
                        if '$(topsrcdir)' in include_filename:
                            prefix_dir = '.'
                        else:
                            prefix_dir = dirname
                        for f in files:
                            # We always include relative to the main Makefile
                            # since that's what make does, so we have to pass in
                            # the original dirname to process_statements(),
                            # rather than going back through process_makefile().
                            include_path = os.path.join(prefix_dir, f)
                            included_statements = pymake.parser.parsefile(include_path)
                            self.process_statements(makefile, context, dirname, included_statements)
                continue
            elif isinstance(s, pymake.parserdata.ConditionBlock):
                for c, ifstatements in s._groups:
                    if c.evaluate(makefile):
                        self.process_statements(makefile, context, dirname, ifstatements)
                        break
            elif isinstance(s, pymake.parserdata.VPathDirective):
                s.execute(makefile, context)

    def process_makefile(self, makefile, context, filename):
        statements = pymake.parser.parsefile(filename)

        self.process_statements(makefile, context, os.path.dirname(filename), statements)

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

            # If the parent directory has a Makefile.in, check if we are in its
            # DIRS variable (and it too is enabled). If not, keep going up the
            # tree, since it may be out grandparent (or above) that enables us.
            makefile_in = os.path.join(parent, self.makefile_name)
            if os.path.exists(makefile_in):
                # Check parent's DIRS variables for our name
                tmpmakefile = copy.deepcopy(self.autoconf_makefile)
                self.process_makefile(tmpmakefile, self.context, makefile_in)

                dirs = self.get_var('DIRS', tmpmakefile)
                dirs.extend(self.get_var('PARALLEL_DIRS', tmpmakefile))
                dirs.extend(self.get_var('TOOL_DIRS', tmpmakefile))
                dirs.extend(self.get_var('TEST_DIRS', tmpmakefile))
                if dirs and child in dirs:
                    return self.makefile_is_enabled(parent)

            # Recurse up the tree looking for a parent Makefile.in
            paths = os.path.split(parent)
            parent = paths[0]
            child = os.path.join(paths[1], child)

    def makefile_is_enabled(self, subdir):
        """
        Make sure that this Makefile.in is in a relevant DIRS variable of a parent.
        """

        if subdir == '.':
            # Get the path relative to moz_root by finding the components of cwd
            # using the length of moz_root. Eg, if our cwd is
            # HOME/m-c/xpcom/base, then moz_root is "../..", so we count one '/'
            # in moz_root, and add one to it so path_count is 2. We pull off the
            # last 2 parts of cwd to get "xpcom/base", and prefixed with
            # moz_root becomes "../../xpcom/base".
            cwd = os.getcwd()
            cwd_parts = cwd.split('/')
            path_count = self.moz_root.count('/') + 1
            subdir = os.path.join(self.moz_root, *cwd_parts[-path_count:])

        if subdir not in self.enabled_dirs:
            self.enabled_dirs[subdir] = self.check_dirs_variables(subdir)

        return self.enabled_dirs[subdir]

    def vpath_resolve(self, subdir, vpath, filename):
        # When parsing manifest.mn, for example, VPATH may not be set.
        if not vpath:
            vpath = ['.']

        for p, dirs in self.subdir_makefile._patternvpaths:
            if p.match(filename):
                vpath.extend(dirs)

        # Don't use the wild-carding method if we:
        # 1) Just have a single VPATH (ie: the current directory), or
        # 2) Are specifying an explicit relative directory where we don't expect
        #    VPATH to kick in. Otherwise tup returns errors when non-existent
        #    directories are used.
        if len(vpath) == 1 or filename.find('/') != -1:
            if(subdir == '.'):
                return filename
            else:
                return os.path.join(subdir, filename)

        # When VPATH is enabled, we return one entry for each path with a
        # wildcard attached. If we use something like os.path.exists() to find
        # the exact correct file, tup will detect these dependencies and cause
        # the Tupfile to be re-parsed when the file is modified. Extraneous
        # parsing is undesirable, and this strange way of handling VPATH avoids
        # the issue. It does also cause symlinks to files like js-config.h.in
        # since js-config.h* matches both, but that isn't likely to cause
        # problems.
        returned_path = []
        wildcard_filename = filename + "*"
        for path in vpath:

            # Since we are using Makefile.in, @srcdir@ won't be substituted.
            # We just want to use the current directory in such cases.
            path = path.replace('@srcdir@', '.')

            if path == '.':
                fullpath = os.path.join(subdir, wildcard_filename)
            elif path.startswith('..'):
                # other-licenses/snappy/Makefile.in uses $(topsrcdir) in its
                # VPATH, so we account for that here.
                fullpath = os.path.join(path, wildcard_filename)
            else:
                fullpath = os.path.join(subdir, path, wildcard_filename)

            returned_path.append(fullpath)

        return ' '.join(returned_path)

    def parse(self, subdir):
        self.subdir_makefile = copy.deepcopy(self.autoconf_makefile)

        makefile_in = os.path.join(subdir, self.makefile_name)
        if not os.path.exists(makefile_in):
            print >> sys.stderr, "Error: Unable to find file: ", makefile_in
            sys.exit(1)
        if self.always_enabled or self.makefile_is_enabled(subdir):
            self.process_makefile(self.subdir_makefile, self.context, makefile_in)
