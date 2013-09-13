#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    final_target = sandbox.get_string('FINAL_TARGET')
    defines = sandbox['DEFINES']
    defines.extend(sandbox['ACDEFINES'])

    component_dir = os.path.join(final_target, 'components')
    js_module_dir = sandbox.get_string('JS_MODULES_PATH')
    if not js_module_dir:
        js_module_dir = 'modules'
    js_module_dir = os.path.join(final_target, js_module_dir)

    extra_pp_components = sandbox['EXTRA_PP_COMPONENTS']
    extra_pp_components_flags = sandbox['EXTRA_PP_COMPONENTS_FLAGS']
    for component in extra_pp_components:
        sandbox.generate_pp_rule(component, defines, extra_pp_components_flags, component_dir, input_group="$(MOZ_ROOT)/<generated-headers>")

    pref_js_exports = sandbox['PREF_JS_EXPORTS']
    if sandbox['GRE_MODULE']:
        pref_dir = 'greprefs'
    elif sandbox['XPI_NAME'] or sandbox['LIBXUL_SDK'] or sandbox['DIST_SUBDIR']:
        pref_dir = 'defaults/preferences'
    else:
        pref_dir = 'defaults/pref'
    pref_pp_flags = sandbox['PREF_PP_FLAGS']
    if sandbox['OS_ARCH'] == 'WINNT':
        # on win32, pref files need CRLF line endings... see bug 206029
        pref_pp_flags.append('--line-endings=crlf')
    for export in pref_js_exports:
        sandbox.generate_pp_rule(export, defines, pref_pp_flags, os.path.join(final_target, pref_dir))

    extra_components = sandbox['EXTRA_COMPONENTS']
    for component in extra_components:
        sandbox.generate_install_rule(component, component_dir)

    extra_js_modules = sandbox['EXTRA_JS_MODULES']
    for module in extra_js_modules:
        fullpath = sandbox.vpath_resolve(module)
        sandbox.generate_install_rule(fullpath, js_module_dir)

    extra_pp_js_modules = sandbox['EXTRA_PP_JS_MODULES']
    for module in extra_pp_js_modules:
        sandbox.generate_pp_rule(module, defines, [], js_module_dir)

    autocfg_js_exports = sandbox['AUTOCFG_JS_EXPORTS']
    autocfg_dest = os.path.join(final_target, 'defaults', 'autoconfig')
    for export in autocfg_js_exports:
        sandbox.generate_install_rule(export, autocfg_dest)

    pp_targets = sandbox['PP_TARGETS']
    for target in pp_targets:
        files = sandbox[target]
        dest = sandbox.get_string('%s_PATH' % target)
        if not dest:
            dest = sandbox.outputdir
        for f in files:
            prefix = ""
            if target == 'SEARCHPLUGINS':
                # SEARCHPLUGINS uses vpath to locate the xml. Ugh.
                prefix = 'en-US/searchplugins/'
            flags = sandbox['%s_FLAGS' % target]
            sandbox.generate_pp_rule(prefix + f, defines, flags, dest)

    install_targets = sandbox['INSTALL_TARGETS']

    if 'NSINSTALL' in install_targets:
        # For some reason nsinstall is linked as nsinstall_real, then copied
        # to nsinstall, then installed.
        input_file = "%s/%s" % (sandbox.outputdir,
                                sandbox.get_string('HOST_PROGRAM'))
        output_file = "%s/nsinstall%s" % (sandbox.outputdir,
                                          sandbox.get_string('HOST_BIN_SUFFIX'))
        print ": %s |> cp %%f %%o |> %s" % (input_file, output_file)

    # Files that exist in the objdir
    obj_files = ('xpcom-config.h',
                 'js-config.h',
                 'cairo-features.h',
                 'necko-config.h',
                 'nsinstall')
    for target in install_targets:
        if target == 'NSINSTALL' and sandbox.relativesrcdir == 'js/src/config':
            # Both js/src/config/ and config/ try to create nsinstall, but we
            # only need one.
            continue
        # TODO: Currently only some targets are supported
        # GDBINIT: has hidden '.gdbinit' path
        if target in ('EXPORTS_GENERATED', 'BRANDING', 'SYNC_MAIN', 'SYNC_ENGINES', 'SYNC_STAGES', 'WORKER', 'MODULES', 'CRYPTO_MODULE', 'globalgen_headers', 'xpcom', 'jsconfig', 'histoenums', 'extra_export_files', 'structlist', 'cairo_features', 'neckoconfig', 'errorlist', 'GDB_INSTALL_AUTOLOAD', 'SHELL_INSTALL_AUTOLOAD', 'SHELL_INSTALL_AUTOLOAD_SCRIPT', 'xpcaccevents', 'ACCESSFU', 'HEADERS', 'TEST_PLUGIN', 'ICON', 'NSINSTALL'):
            files = sandbox['%s_FILES' % target]
            dest = sandbox.get_string('%s_DEST' % target)
            for f in files:
                if f in obj_files:
                    sandbox.generate_install_rule(os.path.join(sandbox.outputdir, f), dest)
                else:
                    sandbox.generate_install_rule(f, dest)

    # Files manually exported to dist/bin/res
    for target in sandbox['EXPORT_RESOURCE']:
        sandbox.generate_install_rule(target, '$(DIST)/bin/res')
    for target in sandbox['EXPORT_RESOURCE_CONTENT']:
        sandbox.generate_install_rule(target, '$(DIST)/bin/res/dtd')
