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
    def __init__(self, config, path, moz_root, moz_objdir, extra_includes, relativesrcdir):
        MozbuildSandbox.__init__(self, config, path)
        self.makefile = None
        self.objs = []
        self.hostobjs = []
        self.moz_root = moz_root
        self.moz_objdir = moz_objdir
        self.variables = {}
        self.extra_deps = []
        self.extra_includes = extra_includes
        self.objsgroup = ""
        self.tupcpp = None

        self.relativesrcdir = relativesrcdir
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

    def get_tupcpp(self):
        if not self.tupcpp:
            from cpp import TupCpp
            self.tupcpp = TupCpp(self)
        return self.tupcpp

    def resolve(self, name):
        if name.startswith('$(') and name.endswith(')'):
            return self[name[2:-1]]
        else:
            return [name]

    def get_output_group(self):
        xpi_name = self.get_string('XPI_NAME')
        if xpi_name:
            group_suffix = "-xpi-%s" % xpi_name
        else:
            dist_subdir = self.get_string('DIST_SUBDIR')
            if dist_subdir:
                group_suffix = "-%s" % dist_subdir
            else:
                group_suffix = ""
        return '$(MOZ_ROOT)/<installed-manifests%s>' % group_suffix

    def generate_pp_rule(self, filename, defines, extra_flags, output_path, input_group=""):
        flags = ' '.join(defines)
        if(extra_flags):
            flags += ' ' + ' '.join(extra_flags)
        output_group = ""
        if filename.endswith('.manifest'):
            output_group = self.get_output_group()
        output_file = os.path.basename(filename)
        if output_file.endswith('.in'):
            output_file, ext = os.path.splitext(output_file)
        print ": foreach %s | %s |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %%f > %%o |> %s/%s | %s" % (filename, input_group, flags, output_path, output_file, output_group)

    def generate_install_rule(self, filename, output_path, output_group=""):
        if filename.endswith('.manifest'):
            output_group = self.get_output_group()
        elif filename.endswith('.h'):
            output_group = "$(MOZ_ROOT)/<installed-headers>"
        elif filename.endswith('.png'):
            # This is to help browser/app/Makefile.in copy pngs from
            # $(DIST)/branding to $(FINAL_TARGET)/chrome/icons/default
            output_group = "$(MOZ_ROOT)/<installed-icons>"

        if '*' in filename:
            # If we're using a wildcard-ed input due to VPATH, it's easier to just
            # copy the file.
            print ": foreach %s |> !cp |> %s/%%b | %s" % (filename,
                                                          output_path, output_group)
            return

        if '/' in filename:
            ifile = filename
        else:
            ifile = '%s/%s' % (self.relativesrcdir, filename)
        ofile = '%s/%s' % (output_path, os.path.basename(ifile))

        # Find longest prefix
        prefix = None
        index = ([x[0]==x[1] for x in zip(ofile, ifile)]+[0]).index(0)
        if index:
            while index > 0 and ofile[index] != '/':
                index -= 1
            if index:
                prefix = ofile[:index+1]
        if prefix:
            dotdots = '../' * ofile.replace(prefix, '').count('/')
            symtarget = dotdots + ifile.replace(prefix, '')
        else:
            tmppath = output_path.replace('../', '')
            dotdots = '../' * (tmppath.count('/') + 1)
            symtarget = dotdots + ifile
        print ": %s |> ^ INSTALL %%f^ ln -s %s %s |> %s | %s" % (filename, symtarget, ofile, ofile, output_group)

    def __getitem__(self, name):
        if name in self.variables:
            return self.variables[name]

        value = []
        if self.makefile:
            makevalue = self.makefile.get_var(name)
            if makevalue is not None:
                value.extend(makevalue)
                # CSRCS is currently split between moz.build and Makefile.in
                # in gfx/cairo/cairo/src
                if name != 'CSRCS':
                    return value

        try:
            mozbuild_value = super(MozbuildMakeSandbox, self).__getitem__(name)

            if not isinstance(mozbuild_value, list):
                # If we already got a value from the Makefile, use that.
                # Some variables (eg: EXPORTS) show up in in moz.build even
                # if we don't have a moz.build file.
                if value:
                    return value
                return mozbuild_value

            # Some values in moz.build still rely on definitions from
            # Makefile.in. Until that is finished, we need to resolve them here.
            for v in mozbuild_value:
                value.extend(self.resolve(v))
        except KeyError:
            pass
        if value:
            return value

        if name in self.config.defines:
            return [self.config.defines[name]]
        if name in self.config.substs:
            return [self.config.substs[name]]

        return []

    def __contains__(self, name):
        if super(MozbuildMakeSandbox, self).__contains__(name):
            return True
        if name in self.variables:
            return True
        if name in self.config.defines:
            return True
        if name in self.config.substs:
            return True
        if self.makefile and self.makefile.get_var(name) is not None:
            return True
        return False
