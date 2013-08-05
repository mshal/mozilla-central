#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def resolve_libraries(sandbox, libs):
    flags = []
    deps = []
    for lib in libs:
        if lib.startswith('-l'):
            deps.append('$(MOZ_ROOT)/<%s>' % lib)

        if lib.startswith('-L/'):
            # TODO: Convert flags that use a full path for -L/foo to
            # be relative so that it doesn't circumvent tup's dependency
            # detection, until we can run everything in a chroot environment.
            index = lib.find(sandbox.moz_objdir)
            if index == -1:
                flags.append(lib)
            else:
                flags.append('-L%s/%s' % (sandbox.moz_root, lib[index:]))
        else:
            flags.append(lib)
    return flags, deps

def generate_desc_file(sandbox, objs):
    lib_prefix = sandbox.get_string('LIB_PREFIX')
    lib_suffix = sandbox.get_string('LIB_SUFFIX')
    program = sandbox.get_string('PROGRAM')

    if program:
        program_exec = "$(PYTHON_PATH)"
        program_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config"
        program_exec += " $(MOZ_ROOT)/config/expandlibs_exec.py"
        program_exec += " --relative-path $(MOZ_ROOT)"
        program_exec += " --target %o"
        program_exec += " --"
        program_exec += ' ' + sandbox.get_string('CCC')
        program_exec += ' -o %s' % program
        program_exec += ' ' + sandbox.get_string('CXXFLAGS')
        inputs = sandbox.get_string('PROGOBJS')
        program_exec += ' ' + inputs

        flags1 = ['RESFILE', 'WIN32_EXE_LDFLAGS', 'LDFLAGS', 'WRAP_LDFLAGS', 'LIBS_DIR']
        program_exec += ' ' + ' '.join(self.get_all_flags(flags1, program))

        libs = tupmk.get_var('LIBS')
        libs.extend(tupmk.get_var('MOZ_GLUE_PROGRAM_LDFLAGS'))
        libs.extend(tupmk.get_var('OS_LIBS'))
        libs.extend(tupmk.get_var('EXTRA_LIBS'))
        actual_libs, lib_deps = resolve_libraries(sandbox, libs)
        inputs += ' ' + ' '.join(lib_deps)
        program_exec += ' ' + ' '.join(actual_libs)

        flags2 = ['BIN_FLAGS', 'EXE_DEF_FILE']
        program_exec += ' ' + ' '.join(self.get_all_flags(flags2, program))
        print ": %s | $(MOZ_ROOT)/dist/bin/<installed-libs> |> ^ LINK %%o^ %s |> %s" % (inputs, program_exec, program)

    if sandbox['FORCE_SHARED_LIB']:
        library_name = '%s%s%s' % (sandbox.get_string('DLL_PREFIX'),
                                   sandbox.get_string('SHARED_LIBRARY_NAME'),
                                   sandbox.get_string('DLL_SUFFIX'))
        output = '%s/%s' % (sandbox.outputdir, library_name)
        sandbox.makefile.set_var('@', output)
        inputs = ' '.join(objs)

        # In make, EXTRA_DSO_LIBS is converted by the EXPAND_MOZLIBNAME
        # macro called from rules.mk. We expand it here before evaluating
        # EXTRA_DSO_LDOPTS, where it is used.
        extra_dso_libs = sandbox.get_string('EXTRA_DSO_LIBS')
        if extra_dso_libs:
            extra_dso_libs = '$(MOZ_ROOT)/dist/lib/%s%s.%s' % (lib_prefix,
                                                               extra_dso_libs,
                                                               lib_suffix)
            sandbox.makefile.set_var('EXTRA_DSO_LIBS', extra_dso_libs)

        extra_dso_ldopts = sandbox['EXTRA_DSO_LDOPTS']

        actual_libs, lib_deps = resolve_libraries(sandbox, extra_dso_ldopts)

        libs, deps = resolve_libraries(sandbox, sandbox['SHARED_LIBRARY_LIBS'])
        actual_libs.extend(libs)
        lib_deps.extend(deps)

        lib_deps_string = ' '.join(lib_deps)

        expandlibs_exec = "$(PYTHON_PATH)"
        expandlibs_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config"
        expandlibs_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/_virtualenv/lib/python2.7/site-packages"
        expandlibs_exec += " $(MOZ_ROOT)/config/expandlibs_exec.py"
        # TODO
#        expandlibs_exec += " --relative-path $(MOZ_ROOT)"
        expandlibs_exec += " --target %o"
        expandlibs_exec += " " + sandbox.get_string('EXPAND_MKSHLIB_ARGS')
        expandlibs_exec += " --"
        expandlibs_exec += " " + sandbox.get_string('MKSHLIB')
        expandlibs_exec += " %f"
        expandlibs_exec += " " + sandbox.get_string('LDFLAGS')
        if sandbox['IS_COMPONENT']:
            expandlibs_exec += ' ' + sandbox.get_string('MOZ_COMPONENTS_VERSION_SCRIPT_LDFLAGS')
            expandlibs_exec += ' -Wl,-Bsymbolic'
        expandlibs_exec += " " + ' '.join(actual_libs)
        expandlibs_exec += " " + sandbox.get_string('OS_LIBS')

        print ": %s | %s |> ^ SHLIB %%o^ %s |> %s" % (inputs, lib_deps_string, expandlibs_exec, output)
        output_group = '$(MOZ_ROOT)/<-l%s>' % (sandbox.get_string('SHARED_LIBRARY_NAME'))
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)
    else:
        if not static_library_name:
            static_library_name = self.tupmk.get_var_string('STATIC_LIBRARY_NAME')

        if static_library_name:
            output = '%s%s.%s' % (self.tupmk.get_var_string('LIB_PREFIX'),
                                  static_library_name,
                                  self.tupmk.get_var_string('LIB_SUFFIX'))
            output_desc = '%s.%s' % (output,
                                     self.tupmk.get_var_string('LIBS_DESC_SUFFIX'))
            inputs = ' '.join(self.get_objs('OBJS'))
            cmd_inputs = inputs

            # Tup's gyp support creates files in the directory where the gyp
            # file is processed, rather than in some subdirectory like with
            # make. Therefore, we have to trim the library path to be the root
            # of the gyp directory.
            gyp_dirs = ["media/webrtc/trunk/src/modules/video_coding/codecs/vp8",
                        "media/webrtc/trunk/src/modules",
                        "media/webrtc/trunk/src/common_audio",
                        "media/webrtc/trunk/src/system_wrappers/source",
                        "media/webrtc/trunk/src/common_video",
                        "media/webrtc/trunk/src/video_engine",
                        "media/webrtc/trunk/src/voice_engine",
                        "media/webrtc/trunk/third_party/libyuv",
                        "media/mtransport/third_party/nICEr",
                        "media/mtransport/third_party/nrappkit",
                        ]

            for lib in self.tupmk.get_var('SHARED_LIBRARY_LIBS'):
                # Our libraries are not in the autoconf objdir, so remove
                # that from the path.
                if self.moz_objdir in lib:
                    lib = lib.replace(self.moz_objdir + os.path.sep, '')

                # For gyp modules, the library is in the root gyp directory.
                for gyp_dir in gyp_dirs:
                    index = lib.find(gyp_dir)
                    if index != -1:
                        lib = os.path.join(lib[0:index + len(gyp_dir)], os.path.basename(lib))
                        break

                # Some .a files have dist/lib, or strange paths - point them to
                # their actual locations.
                lib, dep = self.resolve_library(lib)

                if dep:
                    inputs += ' %s' % (dep)
                cmd_inputs += ' %s' % (lib)

            print ": %s |> ^ expandlibs_gen.py %%o^ $(PYTHON_PATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config $(MOZ_ROOT)/config/expandlibs_gen.py -o %%o %s --relative-path $(MOZ_ROOT) |> %s" % (inputs, cmd_inputs, output_desc)

            if self.tupmk.get_var('SDK_LIBRARY') or self.tupmk.get_var('DIST_INSTALL') or self.tupmk.get_var('NO_EXPAND_LIBS'):
                print ": %s |> ^ expandlibs_exec.py %%o^ $(PYTHON_PATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config $(MOZ_ROOT)/config/expandlibs_exec.py --relative-path $(MOZ_ROOT) --target %%o --extract -- %s %s %%o %s |> %s" % (inputs, self.tupmk.get_var_string('AR'), self.tupmk.get_var_string('AR_FLAGS'), cmd_inputs, output)

def generate_security_library(sandbox):
    objs = sandbox['SIMPLE_OBJS']
    # We get OBJ_SUFFIX from config.status, which is just 'o', whereas
    # nss expects it to be '.o', so we fix that here.
    obj_suffix = sandbox.get_string('OBJ_SUFFIX')
    objs = ['%s/%s.%s' % (sandbox.outputdir, o[:-len(obj_suffix)], obj_suffix) for o in objs]
    targets = sandbox['TARGETS']
    objdir = sandbox.get_string('OBJDIR') + '/'

    inputs = ' '.join(objs)

    # See if we should build an archive (.a) file
    library = sandbox.get_string('LIBRARY')
    if library and library in targets:
        output = '%s/%s' % (sandbox.outputdir, library.replace(objdir, ''))
        ar = sandbox.get_string('AR')
        print ": %s |> ^ AR[nss] %%o^ %s %%o %%f |> %s" % (inputs, ar, output)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | $(MOZ_ROOT)/<installed-archives>" % (output)

    # See if we should build a shared library
    shared_library = sandbox.get_string('SHARED_LIBRARY')
    mapfile = sandbox.get_string('MAPFILE')
    if shared_library and shared_library in targets and mapfile:
        output = '%s/%s' % (sandbox.outputdir, shared_library.replace(objdir, ''))

        # First process the map file into something the linker can use
        mapfile = sandbox.get_string('MAPFILE')
        mapfile = mapfile.replace(objdir, '')
        output_mapfile = mapfile + '.processed'
        sandbox.makefile.set_var('<', mapfile)
        sandbox.makefile.set_var('@', output_mapfile)

        process_map_file = sandbox.get_string('PROCESS_MAP_FILE')
        print ": |> ^ Generate %%o^ %s |> %s" % (process_map_file, output_mapfile)

        # Now that we have a proper map file, generate the linker rule
        sandbox.makefile.set_var('@', shared_library)
        sandbox.makefile.set_var('MAPFILE', output_mapfile)

        extra_inputs = output_mapfile
        extra_flags = ""
        for i in ['LD_LIBS', 'EXTRA_LIBS', 'EXTRA_SHARED_LIBS', 'OS_LIBS']:
            resolved_values, lib_deps = resolve_libraries(sandbox, sandbox[i])
            for lib in lib_deps:
                extra_inputs += ' ' + lib
            extra_flags += ' ' + ' '.join(resolved_values)

        extra_inputs += " $(MOZ_ROOT)/<installed-archives>"

        extra_files = ""
        for i in sandbox['SHARED_LIBRARY_DIRS']:
            extra_files += ' ' + os.path.join('%s/%s/*.o' % (sandbox.outputdir, i))

        mkshlib = sandbox.get_string('MKSHLIB')
        print ": %s | %s |> ^ SHLIB %%o^ %s -o %%o %%f %s %s |> %s" % (inputs, extra_inputs, mkshlib, extra_files, extra_flags, output)
        output_group = '$(MOZ_ROOT)/<-l%s%s>' % (sandbox.get_string('LIBRARY_NAME'), sandbox.get_string('LIBRARY_VERSION'))
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)

def generate_nsprpub_library(sandbox, objs):
    library_name = sandbox.get_string('LIBRARY_NAME')
    if not library_name:
        return
    library_version = sandbox.get_string('LIBRARY_VERSION')
    lib_suffix = sandbox.get_string('LIB_SUFFIX')
    dll_suffix = sandbox.get_string('DLL_SUFFIX')
    library = '%s/lib%s%s.%s' % (sandbox.outputdir, library_name, library_version, lib_suffix)
    shlib = '%s/lib%s%s.%s' % (sandbox.outputdir, library_name, library_version, dll_suffix)

    sandbox.makefile.set_var('@', library)
    lib_command = sandbox.get_string('AR')
    lib_command += ' ' + sandbox.get_string('AR_FLAGS')
    inputs = ' '.join(objs)
    lib_command += ' ' + inputs
    lib_command += sandbox.get_string('AR_EXTRA_ARGS')
    lib_command += ' && %s %%o' % sandbox.get_string('RANLIB')
    print ": $(MOZ_ROOT)/nsprpub/<objs> |> ^ AR[nsprpub] %%o^ %s |> %s" % (lib_command, library)

    sandbox.makefile.set_var('@', shlib)
    mkshlib = sandbox.get_string('MKSHLIB')
    if mkshlib:
        mkshlib += ' ' + inputs
        mkshlib += ' ' + sandbox.get_string('RES')
        mkshlib += ' ' + sandbox.get_string('LDFLAGS')
        mkshlib += ' ' + sandbox.get_string('WRAP_LDFLAGS')

        lib_flags, deps = resolve_libraries(sandbox, sandbox['EXTRA_LIBS'])
        deps.append('$(MOZ_ROOT)/nsprpub/<objs>')
        mkshlib += ' ' + ' '.join(lib_flags)
        groups = ' '.join(deps)

        print ": %s |> ^ SHLIB[nsprpub] %%o^ %s |> %s" % (groups, mkshlib, shlib)
        output_group = '$(MOZ_ROOT)/<-l%s%s>' % (library_name, library_version)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (shlib, output_group)

def generate_nsprpub_progs(sandbox, objs):
    cc = sandbox.get_string('CC')
    flags = sandbox.get_string('XCFLAGS') + \
            sandbox.get_string('LDFLAGS') + \
            sandbox.get_string('XLDOPTS')
    outoption = sandbox.get_string('OUTOPTION')
    prog_suffix = sandbox.get_string('PROG_SUFFIX')
    obj_suffix = sandbox.get_string('OBJ_SUFFIX')

    # For some reason the space at the end of '-o ' doesn't seem to carry through.
    if outoption == '-o':
        outoption = '-o '

    for prog in sandbox['PROGS']:
        prog = prog.replace('./', '')
        print ": %s/%s |> %s %s %%f %s%%o |> %s/%s | $(MOZ_ROOT)/nsprpub/<progs>" % (sandbox.outputdir, prog + '.' + obj_suffix, cc, flags, outoption, sandbox.outputdir, prog + prog_suffix)

def generate_rules(sandbox, objs):
    if sandbox.relativesrcdir.startswith('nsprpub'):
        if sandbox['PROGS']:
            generate_nsprpub_progs(sandbox, objs)
        else:
            generate_nsprpub_library(sandbox, objs)
    elif sandbox.relativesrcdir.startswith('security'):
        generate_security_library(sandbox)
    else:
        generate_desc_file(sandbox, objs)
