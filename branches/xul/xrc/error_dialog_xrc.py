# This file was automatically generated by pywxrc.
# -*- coding: UTF-8 -*-

import wx
import wx.xrc as xrc

__res = None

def get_resources():
    """ This function provides access to the XML resources in this module."""
    global __res
    if __res == None:
        __init_resources()
    return __res




class xrcErrorDialog(wx.Dialog):
#!XRCED:begin-block:xrcErrorDialog.PreCreate
    def PreCreate(self, pre):
        """ This function is called during the class's initialization.
        
        Override it for custom setup before the window is created usually to
        set additional window styles using SetWindowStyle() and SetExtraStyle().
        """
        pass
        
#!XRCED:end-block:xrcErrorDialog.PreCreate

    def __init__(self, parent):
        # Two stage creation (see http://wiki.wxpython.org/index.cgi/TwoStageCreation)
        pre = wx.PreDialog()
        self.PreCreate(pre)
        get_resources().LoadOnDialog(pre, parent, "ErrorDialog")
        self.PostCreate(pre)

        # Define variables for the controls, bind event handlers
        self.panel = xrc.XRCCTRL(self, "panel")
        self.exception_text = xrc.XRCCTRL(self, "exception_text")
        self.wxID_OK = xrc.XRCCTRL(self, "wxID_OK")
        self.details_button = xrc.XRCCTRL(self, "details_button")
        self.hide_error = xrc.XRCCTRL(self, "hide_error")
        self.traceback_text = xrc.XRCCTRL(self, "traceback_text")





# ------------------------ Resource data ----------------------

def __init_resources():
    global __res
    __res = xrc.EmptyXmlResource()

    __res.Load('error_dialog.xrc')
