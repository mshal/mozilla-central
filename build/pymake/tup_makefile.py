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
                 allow_includes=False, always_enabled=False, need_config_mk=False,
                 js_src=False, nsprpub=False, security=False):
        self.subdir_makefile = None
        self.autoconf_makefile = pymake.data.Makefile()
        self.autoconf_makefile.variables = pymake.data.Variables()
        self.set_var('srcdir', '.')
        self.set_var('topsrcdir', moz_root)
        self.set_var('MOZILLA_DIR', moz_root)

        if js_src:
            depth = os.path.join(moz_root, moz_objdir, 'js', 'src')
        elif nsprpub:
            depth = os.path.join(moz_root, moz_objdir, 'nsprpub')
        else:
            depth = os.path.join(moz_root, moz_objdir)
        self.set_var('DEPTH', depth)
        self.set_var('DIST', os.path.join(moz_root, 'dist'))

        # This is used in some -I flags, and we need to make sure it gets set to
        # something so that "-I" isn't passed in without an argument. It isn't
        # needed for tup, since we generate XPIDLSRCS a little differently from
        # make.
        self.set_var('XPIDL_GEN_DIR', '.')

        # This determines whether or not to include makeutils.mk in
        # package-name.mk, and we don't need makeutils.mk
        self.set_var('INCLUDED_RCS_MK', '1')

        self.context = pymake.parserdata._EvalContext(weak=False)
        self.moz_root = moz_root
        self.makefile_name = makefile_name
        self.always_enabled = always_enabled
        self.need_config_mk = need_config_mk

        autoconf_path = os.path.join(depth, "config", "autoconf.mk")
        browser_build_mk = os.path.join(moz_root, "browser", "build.mk")
        root_makefile_path = os.path.join(moz_root, "Makefile.in")

        self.allow_includes = True
        self.process_makefile(self.autoconf_makefile, self.context, autoconf_path)
        self.process_makefile(self.autoconf_makefile, self.context, browser_build_mk)

        if nsprpub:
            self.topsrcdir = os.path.join(moz_root, 'nsprpub')
            # nsprpub's rules.mk passes in '-c' explicitly, but we use the
            # AS_DASH_C_FLAG in tup_cpp to support that variable for the
            # top-level rules.mk
            self.set_var('AS_DASH_C_FLAG', '-c')
        else:
            # The config.mk, baseconfig.mk, and autoconf.mk do weird things with
            # OBJ_SUFFIX and _OBJ_SUFFIX. The autoconf.mk file has the value we
            # want, so put that in _OBJ_SUFFIX as well (since that value gets
            # put back into the original OBJ_SUFFIX).
            self.topsrcdir = moz_root
            obj_suffix = self.get_var('OBJ_SUFFIX', self.autoconf_makefile)
            self.set_var('_OBJ_SUFFIX', obj_suffix[0])

        self.allow_includes = False
        self.process_makefile(self.autoconf_makefile, self.context, root_makefile_path)
        if security:
            build_makefile = os.path.join(moz_root, 'security', 'build',
                                          'Makefile.in')
            self.process_makefile(self.autoconf_makefile, self.context,
                                  build_makefile)
        self.allow_includes = allow_includes

        if security:
            self.set_var('SOURCE_MD_DIR', os.path.join(moz_root, 'dist'))

            # The security/ Makefiles are a little weird - first make recurses
            # into build/Makefile, then executes sub-makes with a bunch of
            # variables defined at the command-line (DEFAULT_GMAKE_FLAGS). Here
            # we pull out those defines and add them to our base variable set.
            for gmake_flag in self.get_var('DEFAULT_GMAKE_FLAGS', makefile=self.autoconf_makefile):
                parts = gmake_flag.split('=', 1)
                if(len(parts) == 2 and (parts[1] == '0' or parts[1] == '1')):
                    self.set_var(parts[0], parts[1])

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
                'security/manager',
                'security/dbm',
                'nsprpub',
                ]:
            tier = os.path.join(moz_root, dirname)
            self.enabled_dirs[tier] = True

        # Once we have parsed autoconf.mk and build.mk, we can set the "true"
        # topsrcdir for nsprpub.
        self.set_var('topsrcdir', self.topsrcdir)

    def process_statements(self, makefile, context, dirname, statements):
        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ['DEPTH', 'topsrcdir', 'srcdir']:
                    continue
                if s.vnameexp.to_source() in ['GRE_BUILDID', 'APP_BUILDID']:
                    # This is for the config/buildid file, since it is not
                    # generated from configure, we won't find it in the
                    # MOZ_OBJDIR.
                    s.value = s.value.replace('$(DEPTH)', self.moz_root)

                s.execute(makefile, context)
            elif isinstance(s, pymake.parserdata.Include):
                # Certain includes are generally ignored, such as those
                # specifically used by the make backend.
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
                        already_included = self.get_var('INCLUDED_CONFIG_MK')
                        if not already_included:
                            # This variable is defined in
                            # nsprpub/config/config.mk, so we can get our
                            # definitions from there for Makefiles in nsprpub/
                            already_included = self.get_var('NSPR_CONFIG_MK')
                        if not already_included:
                            # This variable is set by
                            # security/coreconf/config.mk, so we can use it
                            # to see if that config file has already been
                            # included for Makefiles under security/
                            already_included = self.get_var('USE_UTIL_DIRECTLY')

                        if self.need_config_mk and not already_included:
                            config_mk = os.path.join(self.topsrcdir, 'config', 'config.mk')
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
                        if '$(topsrcdir)' in include_filename or '$(MOZILLA_DIR)' in include_filename:
                            prefix_dir = '.'
                        else:
                            prefix_dir = dirname
                        for f in files:
                            # We always include relative to the main Makefile
                            # since that's what make does, so we have to pass in
                            # the original dirname to process_statements(),
                            # rather than going back through process_makefile().
                            include_path = os.path.join(prefix_dir, f)
                            include_path = include_path.replace('@srcdir@', '.')
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

    def set_var(self, varname, value, makefile=None):
        if makefile is None:
            if self.subdir_makefile:
                makefile = self.subdir_makefile
            else:
                makefile = self.autoconf_makefile
        makefile.variables.set(varname,
                               pymake.data.Variables.FLAVOR_SIMPLE,
                               pymake.data.Variables.SOURCE_MAKEFILE,
                               value)

    def get_var(self, varname, makefile=None, variables=None):
        if makefile is None:
            # Usually we want the variables from the subdir makefile, but in
            # some cases we just parse autoconf.mk and pull variables directly
            # from there.
            if self.subdir_makefile:
                makefile = self.subdir_makefile
            else:
                makefile = self.autoconf_makefile
        if variables is None:
            variables = makefile.variables

        var_tuple = variables.get(varname)
        if var_tuple is not None and var_tuple[2] is not None:
            return var_tuple[2].resolvesplit(makefile, variables)
        return []

    def get_var_string(self, varname, makefile=None, variables=None):
        return ' '.join(self.get_var(varname, makefile, variables))

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
        for p, dirs in self.subdir_makefile._patternvpaths:
            if p.match(filename):
                vpath.extend(dirs)

        # Since we are using Makefile.in, @srcdir@ won't be substituted.
        # We just want to use the current directory in such cases.
        vpath = [path.replace('@srcdir@', '.') for path in vpath]

        # When parsing manifest.mn, for example, VPATH may not be set.
        if '.' not in vpath:
            vpath.append('.')

        # Don't use the wild-carding method if we:
        # 1) Just have a single VPATH (ie: the current directory), or
        # 2) Are specifying an explicit relative directory where we don't expect
        #    VPATH to kick in. Otherwise tup returns errors when non-existent
        #    directories are used.
        if len(vpath) == 1 or filename.find('/') != -1:
            if subdir == '.':
                if vpath[0] == '.':
                    return filename
                else:
                    return os.path.join(vpath[0], filename)
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

    def parse_internal(self, subdir, makefile):
        makefile_in = os.path.join(subdir, self.makefile_name)
        if not os.path.exists(makefile_in):
            print >> sys.stderr, "Error: Unable to find file: ", makefile_in
            sys.exit(1)
        value = self.makefile_is_enabled(subdir)
        if self.always_enabled or self.makefile_is_enabled(subdir):
            self.process_makefile(makefile, self.context, makefile_in)

    def parse(self, subdir):
        self.subdir_makefile = copy.deepcopy(self.autoconf_makefile)

        self.parse_internal(subdir, self.subdir_makefile)

    def one_time_parse(self, subdir, varname):
        makefile = copy.deepcopy(self.autoconf_makefile)

        self.parse_internal(subdir, makefile)
        return self.get_var(varname, makefile)
