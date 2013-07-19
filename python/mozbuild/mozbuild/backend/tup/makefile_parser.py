#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

def parse(sandbox, moz_root, moz_objdir):
    tupmk = TupMakefile(moz_root, moz_objdir, sandbox)
    tupmk.process_makefile('Makefile.in')

class TupMakefile(object):
    def __init__(self, moz_root, moz_objdir, sandbox,
                 allow_includes=False, always_enabled=False, need_config_mk=False,
                 js_src=False, nsprpub=False, security=False):
        self.makefile = pymake.data.Makefile()
        self.makefile.variables = pymake.data.Variables()

        # Import config.status into the Makefile, as if we had parsed
        # autoconf.mk
        for key, value in sandbox.config.defines.iteritems():
            self.set_var(key, value)
        for key, value in sandbox.config.substs.iteritems():
            self.set_var(key, value)

        self.set_var('srcdir', '.')
        self.set_var('topsrcdir', moz_root)
        self.set_var('MOZILLA_DIR', moz_root)

        self.sandbox = sandbox

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
        self.set_var('relativesrcdir', self.relativesrcdir)

        if js_src:
            depth = os.path.join(moz_root, moz_objdir, 'js', 'src')
        elif nsprpub:
            depth = os.path.join(moz_root, moz_objdir, 'nsprpub')
        else:
            depth = os.path.join(moz_root, moz_objdir)
        self.set_var('DEPTH', depth)
        self.set_var('DIST', os.path.join(moz_root, 'dist'))

        # This determines whether or not to include makeutils.mk in
        # package-name.mk, and we don't need makeutils.mk
        self.set_var('INCLUDED_RCS_MK', '1')

        self.context = pymake.parserdata._EvalContext(weak=False)
        self.moz_root = moz_root
        self.always_enabled = always_enabled
        self.need_config_mk = need_config_mk

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
            obj_suffix = self.get_var('OBJ_SUFFIX')
            self.set_var('_OBJ_SUFFIX', obj_suffix[0])

        if security:
            build_makefile = os.path.join(moz_root, 'security', 'build',
                                          'Makefile.in')
            self.process_makefile(self.context, build_makefile)

        self.allow_includes = allow_includes

        if security:
            self.set_var('SOURCE_MD_DIR', os.path.join(moz_root, 'dist'))

            # The security/ Makefiles are a little weird - first make recurses
            # into build/Makefile, then executes sub-makes with a bunch of
            # variables defined at the command-line (DEFAULT_GMAKE_FLAGS). Here
            # we pull out those defines and add them to our base variable set.
            for gmake_flag in self.get_var('DEFAULT_GMAKE_FLAGS'):
                parts = gmake_flag.split('=', 1)
                if(len(parts) == 2):
                    # It is a bit difficult to pull out all the flags correctly
                    # because of the spacing in variable definitions and the way
                    # pymake parses them. Here we include anything that is
                    # obviously a binary flag (value is 0 or 1), as well as the
                    # SQLITE defines that we need.
                    if(parts[1] == '0' or parts[1] == '1' or
                       parts[0].startswith('SQLITE')):
                        self.set_var(parts[0], parts[1],
                                     source=pymake.data.Variables.SOURCE_COMMANDLINE)
            # We need to also override NSS_ENABLE_ZLIB, similar to
            # security/build/Makefile.in
            self.set_var('NSS_ENABLE_ZLIB', '',
                         source=pymake.data.Variables.SOURCE_COMMANDLINE)

        # Once we have parsed autoconf.mk and build.mk, we can set the "true"
        # topsrcdir for nsprpub.
        self.set_var('topsrcdir', self.topsrcdir)

    def process_statements(self, dirname, statements):
        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ['DEPTH', 'topsrcdir', 'srcdir', 'relativesrcdir']:
                    continue
                if s.vnameexp.to_source() in ['GRE_BUILDID', 'APP_BUILDID']:
                    # This is for the config/buildid file, since it is not
                    # generated from configure, we won't find it in the
                    # MOZ_OBJDIR.
                    s.value = s.value.replace('$(DEPTH)', self.moz_root)

                s.execute(self.makefile, self.context)
                vname = s.vnameexp.resolvestr(self.makefile, self.makefile.variables)
                if vname not in self.sandbox:
                    self.sandbox[vname] = []
                self.sandbox[vname].append(s.value)
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
                            self.process_makefile(config_mk)
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
                        files = s.exp.resolvesplit(self.makefile, self.makefile.variables)
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
                            self.process_statements(dirname, included_statements)
                continue
            elif isinstance(s, pymake.parserdata.ConditionBlock):
                for c, ifstatements in s._groups:
                    if c.evaluate(self.makefile):
                        self.process_statements(dirname, ifstatements)
                        break
            elif isinstance(s, pymake.parserdata.VPathDirective):
                s.execute(self.makefile, self.context)

    def process_makefile(self, filename):
        statements = pymake.parser.parsefile(filename)

        self.process_statements(os.path.dirname(filename), statements)

    def set_var(self, varname, value,
                source=pymake.data.Variables.SOURCE_MAKEFILE):
        self.makefile.variables.set(varname,
                                    pymake.data.Variables.FLAVOR_SIMPLE,
                                    source,
                                    value)

    def get_var(self, varname, variables=None):
        if variables is None:
            variables = self.makefile.variables

        var_tuple = variables.get(varname)
        if var_tuple is not None and var_tuple[2] is not None:
            return var_tuple[2].resolvesplit(self.makefile, variables)
        return []

    def vpath_resolve(self, subdir, vpath, filename):
        for p, dirs in self.makefile._patternvpaths:
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
