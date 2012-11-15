# -*- makefile -*-
# vim:set ts=8 sw=8 sts=8 noet:
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

XPIDL_GEN_DIR ?= _xpidlgen
GARBAGE_DIRS  += $(XPIDL_GEN_DIR)

###########################################################################
## Defines
###########################################################################
ifndef INCLUDED_XPIDL_MK #{

  ifdef SDK_XPIDLSRCS
    _EXTRA_XPIDLSRCS := $(filter-out $(XPIDLSRCS),$(SDK_XPIDLSRCS))
    XPIDLSRCS += $(_EXTRA_XPIDLSRCS)
  endif

  ifneq (,$(strip $(XPIDLSRCS))) #{
	xpidlsrcs := $(XPIDLSRCS)

    # Dependencies
    dir-xpidl-gen = $(call mkdir_deps,$(XPIDL_GEN_DIR))
    dir-mddepdir  = $(call mkdir_deps,$(MDDEPDIR))

    xpidl-module-xpt = $(XPIDL_GEN_DIR)/$(XPIDL_MODULE).xpt

    xpidl-idl2h   = $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.h, $(XPIDLSRCS))
    xpidl-idl2xpt = $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.xpt,$(XPIDLSRCS))

    GARBAGE += $(xpidl-idl2h) $(xpidl-idl2xpt) $(xpidl-module-xpt)


    ifndef XPIDL_MODULE
      XPIDL_MODULE = $(MODULE)
    endif
    ifeq ($(XPIDL_MODULE),) # we need $(XPIDL_MODULE) to make $(XPIDL_MODULE).xpt
	    _xpidl-todo-export_ += xpidl-requires-MODULE
    endif

  xpidl-deps = \
    $(call errorIfEmpty,LIBXUL_DIST) \
    $(LIBXUL_DIST)/sdk/bin/header.py \
    $(LIBXUL_DIST)/sdk/bin/typelib.py \
    $(LIBXUL_DIST)/sdk/bin/xpidl.py \
    $(NULL)

  xpidl-preqs = \
    $(dir-xpidl-gen) \
    $(dir-mddepdir) \
    $(NULL)

  endif #} XPIDLSRCS
endif #} INCLUDED_XPIDL_MK


###########################################################################
## Conditional targets
###########################################################################
ifdef xpidlsrcs #{

  ifneq (,$(call isTargetStemExport))
    _xpidl-todo-export_ += xpidl-gen-headers
  endif

  ifneq (,$(call isTargetStemLibs)) #{
    _xpidl-todo-libs_ += xpidl-gen-xpt

    ifndef NO_DIST_INSTALL
      ifndef NO_INTERFACES_MANIFEST
		_xpidl-todo-libs_ += xpidl-gen-manifest
      endif
    endif

  endif #} isTargetStemLibs

endif #} xpidlsrcs


###########################################################################
## Installer values
###########################################################################
ifdef xpidlsrcs #{
  ifndef NO_DIST_INSTALL #{
	XPIDL_MODULE_FILES := $(XPIDL_GEN_DIR)/$(XPIDL_MODULE).xpt
	XPIDL_MODULE_DEST := $(FINAL_TARGET)/components
	INSTALL_TARGETS += XPIDL_MODULE

	XPIDL_HEADERS_FILES := $(xpidl-idl2h)
	XPIDL_HEADERS_DEST := $(DIST)/include
	XPIDL_HEADERS_TARGET := export
	INSTALL_TARGETS += XPIDL_HEADERS

	XPIDLSRCS_FILES := $(XPIDLSRCS)
	XPIDLSRCS_DEST := $(IDL_DIR)
	XPIDLSRCS_TARGET := export
	INSTALL_TARGETS += XPIDLSRCS
  endif #} NO_DIST_INSTALL
endif #}


###########################################################################
## export::
###########################################################################
ifneq (,$(_xpidl-todo-export_)) #{

export:: $(_xpidl-todo-export_)

xpidl-gen-headers-preqs =\
  $(dir-xpidl-gen) \
  $(xpidl-idl2h) \
  $(NULL)

xpidl-gen-headers: $(xpidl-gen-headers-preqs)

.PHONY: xpidl-requires-MODULE
xpidl-requires-MODULE: # we need $(XPIDL_MODULE) to make $(XPIDL_MODULE).xpt
	@echo
	@echo "*** Error processing XPIDLSRCS:"
	@echo "Please define MODULE or XPIDL_MODULE when defining XPIDLSRCS,"
	@echo "so we have a module name to use when creating MODULE.xpt."
	@echo; sleep 2; false

endif #} _xpidl-todo-export_


###########################################################################
## libs::
###########################################################################
ifneq (,$(_xpidl-todo-libs_)) #{

libs:: $(_xpidl-todo-libs_)

xpidl-gen-xpt: $(xpidl-idl2xpt)

xpidl-gen-manifest: $(call mkdir_deps,$(FINAL_TARGET)/components)
	@$(PYTHON) $(MOZILLA_DIR)/config/buildlist.py $(FINAL_TARGET)/components/interfaces.manifest "interfaces $(XPIDL_MODULE).xpt"
	@$(PYTHON) $(MOZILLA_DIR)/config/buildlist.py $(FINAL_TARGET)/chrome.manifest "manifest components/interfaces.manifest"

endif #} _xpidl-todo-libs_


###########################################################################
## pattern rules: can be listed with targets above but cleaner here
###########################################################################
ifdef xpidlsrcs #{

$(XPIDL_GEN_DIR)/%.h: %.idl $(xpidl-deps) $(xpidl-preqs)
	$(REPORT_BUILD)
	$(PYTHON_PATH) \
	  $(PLY_INCLUDE) \
	  $(LIBXUL_DIST)/sdk/bin/header.py $(XPIDL_FLAGS) $(_VPATH_SRCS) -d $(MDDEPDIR)/$(@F).pp -o $@
	@if test -n "$(findstring $*.h, $(EXPORTS))"; \
	  then echo "*** WARNING: file $*.h generated from $*.idl overrides $(srcdir)/$*.h"; else true; fi

# generate intermediate .xpt files into $(XPIDL_GEN_DIR), then link
# into $(XPIDL_MODULE).xpt and export it to $(FINAL_TARGET)/components.
$(XPIDL_GEN_DIR)/%.xpt: %.idl $(xpidl-deps) $(xpidl-preqs)
	$(REPORT_BUILD)
	$(PYTHON_PATH) \
	  $(PLY_INCLUDE) \
	  -I$(topsrcdir)/xpcom/typelib/xpt/tools \
	  $(LIBXUL_DIST)/sdk/bin/typelib.py $(XPIDL_FLAGS) $(_VPATH_SRCS) -d $(MDDEPDIR)/$(@F).pp -o $@

# no need to link together if XPIDLSRCS contains only XPIDL_MODULE
ifneq ($(XPIDL_MODULE).idl,$(strip $(XPIDLSRCS)))
  XPT_PY = $(filter %/xpt.py,$(XPIDL_LINK))

  xpidl-xpt-preqs =\
    $(dir-xpidl-gen) \
    $(xpidl-idl2xpt) \
    $(GLOBAL_DEPS) \
    $(XPT_PY) \
    $(NULL)

$(xpidl-module-xpt): $(xpidl-xpt-preqs)
	$(XPIDL_LINK) $@ $(xpidl-idl2xpt)

$(XPT_PY):
	$(MAKE) -C $(DEPTH)/xpcom/typelib/xpt/tools libs

endif # XPIDL_MODULE.xpt != XPIDLSRCS

endif #} xpidlsrcs


ifndef INCLUDED_XPIDL_MK #{
  INCLUDED_XPIDL_MK = 1
endif #}
