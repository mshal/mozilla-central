#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import pymake.parser

def parse(sandbox, makefile):
    tupmk = TupMakefile(sandbox, allow_includes=True)
    if makefile:
        tupmk.process_makefile(makefile)
    else:
        tupmk.process_config_mk()

class TupMakefile(object):
    def __init__(self, sandbox,
                 allow_includes=False, always_enabled=False):
        self.makefile = pymake.data.Makefile()
        self.makefile.variables = pymake.data.Variables()
        self.sandbox = sandbox

        sandbox.makefile = self

        # Import config.status into the Makefile, as if we had parsed
        # autoconf.mk
        for key, value in sandbox.config.defines.iteritems():
            self.set_var(key, value)
        for key, value in sandbox.config.substs.iteritems():
            self.set_var(key, value)
        for key, value in sandbox.variables.iteritems():
            self.set_var(key, value)

        # Set some variables that are defined in moz.build but are used in
        # the Makefile or config.mk
        for var in ['LIBRARY_NAME']:
            if var in sandbox:
                self.set_var(var, sandbox[var])

        self.set_var('srcdir', '.')
        self.set_var('MOZILLA_DIR', sandbox.moz_root)

        self.allow_includes = allow_includes

        self.set_var('relativesrcdir', sandbox.relativesrcdir)

        if sandbox.relativesrcdir.startswith('nsprpub'):
            nsprpub = True
            sandbox.objsgroup = '$(MOZ_ROOT)/nsprpub/<objs>'
        else:
            nsprpub = False

        if sandbox.relativesrcdir.startswith('js/src'):
            js_src = True
        else:
            js_src = False

        if sandbox.relativesrcdir.startswith('security/nss'):
            security = True
            sandbox.objsgroup = '$(MOZ_ROOT)/security/nss/<objs>'
        else:
            security = False

        if js_src:
            depth = os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'js', 'src')
            self.topsrcdir = os.path.join(sandbox.moz_root, 'js', 'src')
        elif nsprpub:
            depth = os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'nsprpub')
            self.topsrcdir = os.path.join(sandbox.moz_root, 'nsprpub')
        else:
            depth = os.path.join(sandbox.moz_root, sandbox.moz_objdir)
            self.topsrcdir = sandbox.moz_root
        self.set_var('DEPTH', depth)
        self.set_var('topsrcdir', self.topsrcdir)

        # This determines whether or not to include makeutils.mk in
        # package-name.mk, and we don't need makeutils.mk
        self.set_var('INCLUDED_RCS_MK', '1')

        self.context = pymake.parserdata._EvalContext(weak=False)
        self.always_enabled = always_enabled

        # The config.mk, baseconfig.mk, and autoconf.mk do weird things with
        # OBJ_SUFFIX and _OBJ_SUFFIX. The autoconf.mk file has the value we
        # want, so put that in _OBJ_SUFFIX as well (since that value gets put
        # back into the original OBJ_SUFFIX in config.mk).
        obj_suffix = self.get_var('OBJ_SUFFIX')
        self.set_var('_OBJ_SUFFIX', obj_suffix[0])

        if security:
            self.set_var('SOURCE_MD_DIR', os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'dist'))
            self.set_var('SOURCE_XP_DIR', os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'dist'))
            self.set_var('SOURCE_XPHEADERS_DIR', os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'dist', 'include', 'nss'))
            self.set_var('NSPR_INCLUDE_DIR', os.path.join(sandbox.moz_root, sandbox.moz_objdir, 'dist', 'include', 'nspr'))

            # The security/ Makefiles are a little weird - first make recurses
            # into build/Makefile, then executes sub-makes with a bunch of
            # variables defined at the command-line (DEFAULT_GMAKE_FLAGS). Here
            # we pull out those defines and add them to our base variable set.
            backup_makefile = copy.deepcopy(self.makefile)
            build_path = os.path.join(sandbox.moz_root, 'security', 'build',
                                      'Makefile.in')
            self.process_makefile(build_path)
            default_gmake_flags = self.get_var('DEFAULT_GMAKE_FLAGS')
            self.makefile = backup_makefile

            for gmake_flag in default_gmake_flags:
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

        if nsprpub:
            autoconf_mk = os.path.join(sandbox.moz_root, sandbox.moz_objdir,
                                       'nsprpub', 'config', 'autoconf.mk')
            self.process_makefile(autoconf_mk)

    def process_config_mk(self):
        if not self.get_var('INCLUDED_CONFIG_MK') and not self.get_var('NSPR_CONFIG_MK'):
            config_mk = os.path.join(self.topsrcdir, 'config', 'config.mk')
            self.process_makefile(config_mk)

    def process_statements(self, dirname, statements):
        for s in statements:
            if isinstance(s, pymake.parserdata.SetVariable):

                # These variables are specific to make's implementation, and aren't
                # needed in general
                if s.vnameexp.to_source() in ('DEPTH', 'topsrcdir', 'srcdir', 'relativesrcdir', 'abs_srcdir', 'DIST'):
                    continue

                # These are passed in to the nss build, and we override them
                if s.vnameexp.to_source() in ('SOURCE_XPHEADERS_DIR', 'NSPR_INCLUDE_DIR'):
                    continue

                # This breaks because we can't wildcard libs before there are
                # any (security/nss/cmd/shlibsign)
                if s.vnameexp.to_source() == 'CHECKLIBS':
                    continue

                s.execute(self.makefile, self.context)
            elif isinstance(s, pymake.parserdata.Include):
                # Certain includes are generally ignored, such as those
                # specifically used by the make backend.
                if self.allow_includes and s.required:
                    include_filename = s.exp.to_source()
                    if 'config/rules.mk' in include_filename:
                        # Ignore rules.mk, but rules.mk picks up config.mk
                        self.process_config_mk()
                        continue
                    elif '/baseconfig.mk' in include_filename:
                        # Ignore baseconfig.mk
                        continue
                    elif include_filename == '$(topsrcdir)/config/config.mk':
                        self.process_config_mk()
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
                    elif 'exported_headers.mk' in include_filename and self.sandbox.relativesrcdir.startswith('js/src'):
                        # mfbt already exports these headers - don't try to
                        # export them again.
                        continue
                    elif include_filename == 'ipdlsrcs.mk':
                        # ipdlsrcs.mk is generated for the make backend - we
                        # don't use it ourselves, but we need other data
                        # in the Makefile.in for ipdl generation
                        continue
                    else:
                        files = s.exp.resolvesplit(self.makefile, self.makefile.variables)
                        if '$(topsrcdir)' in include_filename or '$(MOZILLA_DIR)' in include_filename or '$(DEPTH)' in include_filename:
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
        if type(value) == list:
            realval = ' '.join(value)
        else:
            realval = value
        self.makefile.variables.set(varname,
                                    pymake.data.Variables.FLAVOR_RECURSIVE,
                                    source,
                                    realval)

    def get_var(self, varname, variables=None):
        if variables is None:
            variables = self.makefile.variables

        var_tuple = variables.get(varname)
        if var_tuple is not None and var_tuple[2] is not None:
            return var_tuple[2].resolvesplit(self.makefile, variables)
        return None

    def vpath_resolve(self, subdir, vpath, filename):
        for p, dirs in self.makefile._patternvpaths:
            if p.match(filename):
                vpath.extend(dirs)

        # Since we are using Makefile.in, @srcdir@ won't be substituted.
        # We just want to use the current directory in such cases.
        vpath = [path.replace('@srcdir@', '.') for path in vpath]

        # Some weird Makefiles (like gfx/tests/gtest) add DEPTH to VPATH,
        # which means the objdir is in there. We need to pull that out.
        vpath = [path.replace(self.sandbox.moz_objdir, '.') for path in vpath]

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
