# Copyright (c) 2013 Mozilla Foundation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import gyp
import gyp.common
import sys
import os
import tup_makefile
import tup_cpp

generator_default_variables = {}
for dirname in ['INTERMEDIATE_DIR', 'SHARED_INTERMEDIATE_DIR', 'PRODUCT_DIR',
                                'LIB_DIR', 'SHARED_LIB_DIR']:
    # Some gyp steps fail if these are empty(!).
    generator_default_variables[dirname] = 'dir'
for unused in ['RULE_INPUT_PATH', 'RULE_INPUT_ROOT', 'RULE_INPUT_NAME',
                             'RULE_INPUT_DIRNAME', 'RULE_INPUT_EXT',
                             'EXECUTABLE_PREFIX', 'EXECUTABLE_SUFFIX',
                             'STATIC_LIB_PREFIX', 'STATIC_LIB_SUFFIX',
                             'SHARED_LIB_PREFIX', 'SHARED_LIB_SUFFIX',
                             'LINKER_SUPPORTS_ICF']:
    generator_default_variables[unused] = ''

def GetFlavor(params):
    """Returns |params.flavor| if it's set, the system's default flavor else."""
    flavors = {
        'win32': 'win',
        'darwin': 'mac',
        'sunos5': 'solaris',
        'freebsd7': 'freebsd',
        'freebsd8': 'freebsd',
    }
    flavor = flavors.get(sys.platform, 'linux')
    return params.get('flavor', flavor)


def CalculateVariables(default_variables, params):
    generator_flags = params.get('generator_flags', {})
    default_variables['OS'] = generator_flags.get('os', GetFlavor(params))

def striplib(name):
    "Strip lib prefixes from library names."
    if name[:3] == 'lib':
        return name[3:]
    return name

CPLUSPLUS_EXTENSIONS = set([
    '.cc',
    '.cpp',
    '.cxx'
])
COMPILABLE_EXTENSIONS = set([
    '.c',
    '.s',
    '.S',
    '.m',
    '.mm'
])
COMPILABLE_EXTENSIONS.update(CPLUSPLUS_EXTENSIONS)

def swapslashes(p):
    "Swap backslashes for forward slashes in a path."
    return p.replace('\\', '/')

def Compilable(filename):
    return os.path.splitext(filename)[1] in COMPILABLE_EXTENSIONS

class TupfileGenerator(object):
    def __init__(self, target_dicts, data, options, flavor, tupmk, cpp):
        self.target_dicts = target_dicts
        self.data = data
        self.options = options
        self.flavor = flavor
        self.tupmk = tupmk
        self.cpp = cpp

    def ProcessTargets(self, needed_targets):
        """
        Put all targets in proper order so that dependencies get built before
        the targets that need them.
        """
        for qualified_target in needed_targets:
            self.ProcessTarget(qualified_target)

    def ProcessTarget(self, qualified_target):
        """
        Generate tup rules for the target
        """
        spec = self.target_dicts[qualified_target]
        # Now write a Makefile for this target
        build_file, target, toolset = gyp.common.ParseQualifiedTarget(
            qualified_target)
        build_file = os.path.abspath(build_file)
        self.WriteTargetRules(qualified_target, spec, build_file)

    def WriteTargetRules(self, qualified_target, spec, build_file):
        configs = spec['configurations']
        data = {}
        #TODO: handle actions/rules/copies
        if 'actions' in spec:
            pass
        if 'rules' in spec:
            pass
        if 'copies' in spec:
            pass
        libs = []
        if libs:
            data['EXTRA_LIBS'] = libs

        # Get DEFINES/INCLUDES
        for configname in sorted(configs.keys()):
            config = configs[configname]
            #XXX: this sucks
            defines = config.get('defines')
            if defines:
                data['DEFINES_%s' % configname] = ["-D%s" % d for d in defines]
            includes = []
            for i in config.get('include_dirs', []):
                # Make regular paths into srcdir-relative paths, leave
                # variable-specified paths alone.
                if i.startswith("$(") or os.path.isabs(i):
                    if ' ' in i:
                        includes.append('"%s"' % i)
                    else:
                        includes.append(i)
                else:
                    includes.append("$(srcdir)/" + i)
            if includes:
                data['INCLUDES_%s' % configname] = ["-I%s" %i for i in includes]
            #XXX: handle mac stuff?
# we want to use our compiler options in general
#            cflags = config.get('cflags')
#            if cflags:
#                data['CPPFLAGS_%s' % configname] = cflags
#            cflags_c = config.get('cflags_c')
#            if cflags_c:
#                data['CFLAGS_%s' % configname] = cflags_c
#            cflags_cc = config.get('cflags_cc')
#            if cflags_cc:
#                data['CXXFLAGS_%s' % configname] = cflags_cc
# we need to keep pkg-config flags however
            cflags_mozilla = config.get('cflags_mozilla')
            if cflags_mozilla:
                data['CPPFLAGS_%s' % configname] = cflags_mozilla
        sources = {
            'CPPSRCS': {'exts': CPLUSPLUS_EXTENSIONS, 'files': []},
            'CSRCS': {'exts': ['.c'], 'files': []},
            'CMSRCS': {'exts': ['.m'], 'files': []},
            'CMMSRCS': {'exts': ['.mm'], 'files': []},
            'ASFILES': {'exts': ['.s'], 'files': []},
            }
        copy_srcs = []
        for s in spec.get('sources', []):
            if not Compilable(s):
                continue

            # Special-case absolute paths, they'll get copied into the objdir
            # for compiling.
            if os.path.isabs(s):
                # GNU Make falls down pretty badly with spaces in filenames.
                # Conveniently, using a single-character ? as a wildcard
                # works fairly well.
                copy_srcs.append(s.replace(' ', '?'))
                s = os.path.basename(s)
                print >> sys.stderr, "tup error: Absolute path found in .gyp file: ", s
                sys.exit(1)

            ext = os.path.splitext(s)[1]
            for source_type, d in sources.iteritems():
                if ext in d['exts']:
                    d['files'].append(s)
                    break
            
        for source_type, d in sources.iteritems():
            if d['files']:
                data[source_type] = d['files']

        if copy_srcs:
            data['COPY_SRCS'] = copy_srcs

        if spec['type'] == 'executable':
            data['PROGRAM'] = spec['target_name']
        elif spec['type'] == 'static_library':
            data['LIBRARY_NAME'] = striplib(spec['target_name'])
            data['FORCE_STATIC_LIB'] = 1
        elif spec['type'] in ('loadable_module', 'shared_library'):
            data['LIBRARY_NAME'] = striplib(spec['target_name'])
            data['FORCE_SHARED_LIB'] = 1
        else:
            # Maybe nothing?
            return False
        self.WriteTupRules(data)
        return True

#    def WriteCompileRules(self, data, srcs_name, display_string, cc_string,
#                          flag_string, obj_suffix):
#        if srcs_name in data:
#            srcs = data[srcs_name]
#            for filename in srcs:
#                print ": %s | $(MOZ_ROOT)/dist/include/<installed-headers> |> ^ %s %%f^ %s -c %%f -o %%o %s |> %%B.%s" % (filename, display_string, cc_string, flag_string, obj_suffix)
#
    def GetFlag(self, data, flag):
        return list(data[flag]) if flag in data else []

    def WriteTupRules(self, data):
        if self.tupmk.get_var('MOZ_DEBUG'):
            suffix = "Debug"
        else:
            suffix = "Release"
        includes = self.GetFlag(data, 'INCLUDES_' + suffix)

        cflags = self.GetFlag(data, 'DEFINES_' + suffix)
        cflags.extend(self.GetFlag(data, 'CPP_FLAGS_' + suffix))
        cflags.extend(self.GetFlag(data, 'CFLAGS_' + suffix))

        cxxflags = self.GetFlag(data, 'DEFINES_' + suffix)
        cxxflags.extend(self.GetFlag(data, 'CPP_FLAGS_' + suffix))
        cxxflags.extend(self.GetFlag(data, 'CXXFLAGS_' + suffix))

        cflag_string = ' '.join(cflags)
        cxxflag_string = ' '.join(cxxflags)
        for inc in includes:
            inc = inc.replace('$(srcdir)', '.')
            inc = inc.replace('$(DEPTH)', self.tupmk.moz_root)
            cflag_string += ' ' + inc
            cxxflag_string += ' ' + inc

        if 'CPPSRCS' in data:
            self.cpp.generate_cpp_rules(cppsrcs=data['CPPSRCS'],
                                        flags=cxxflag_string)
        if 'CSRCS' in data:
            self.cpp.generate_cpp_rules(csrcs=data['CSRCS'],
                                        flags=cflag_string)

def GenerateOutput(target_list, target_dicts, data, params):
    options = params['options']
    flavor = GetFlavor(params)
    generator_flags = params.get('generator_flags', {})
    moz_root = generator_flags['MOZ_ROOT']
    moz_objdir = generator_flags['MOZ_OBJDIR']
    tupmk = tup_makefile.TupMakefile(moz_root,
                                     moz_objdir,
                                     makefile_name='config.mk')
    # We need to parse config.mk so we can get definitions of things like
    # OS_COMPILE_CXXFLAGS
    tupmk.parse(os.path.join(moz_root, 'config'))

    # Work around the fact that Google codebases don't compile cleanly with
    # -pedantic.
    cpp = tup_cpp.TupCpp(tupmk, moz_objdir,
                         filter_out=['-pedantic'],
                         target_srcs_flag=True)

    # Find the list of targets that derive from the gyp file(s) being built.
    needed_targets = set()
    build_files = set()
    for build_file in params['build_files']:
        build_file = os.path.normpath(build_file)
        for target in gyp.common.AllTargets(target_list, target_dicts, build_file):
            needed_targets.add(target)
            build_file_, _, _ = gyp.common.ParseQualifiedTarget(target)

    generator = TupfileGenerator(target_dicts, data, options, flavor, tupmk, cpp)
    generator.ProcessTargets(needed_targets)
