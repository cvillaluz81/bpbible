import wx
from wx import html
import re

import displayframe
from util.unicode import get_module_encoding
from util import languages
from util.i18n import N_
from gui.htmlbase import html_settings

def get_html_height(module, text):
	import fontchoice

	default, (font, size, in_gui) = fontchoice.get_module_font_params(module)
	dc = wx.MemoryDC()
	bmp = wx.EmptyBitmap(1, 1)
	dc.SelectObject(bmp)
	dc.Font = wx.FFont(size, wx.FONTFAMILY_ROMAN, face=font)
	
	return dc.GetTextExtent(text)

def process(info):
	if not info: return ""

	def uniconvert(object):
		return unichr(int(object.group(1)))
	
	def uniconvert_neg(object):
		return unichr(int(object.group(1)) + 65536)
		
		
	# take out links
	info = re.sub(
		r'<a href([^>]*)>([^<]*)</a>', 
		"{link \x00\\1\x00\\2\x00}",
		info
	)

	# now replace <>
	info = re.sub("&", "&amp;", info)
	
	info = re.sub("<", "&lt;", info)
	info = re.sub(">", "&gt;", info)

	# put the links back in
	info = re.sub(
		"{link \x00([^\x00]*)\x00([^\x00]*)\x00}",
		r"<a href\1>\2</a>",
		info
	)

	info = re.sub(r"\\qc ?(.*?)(\pard|$)", r"<center>\1</center>\2", info)
	info = re.sub(r"\\pard", "", info)
	
	info = re.sub(r"\\par ?", "<br />", info)
	info = re.sub(r"\\u(\d+)\?", uniconvert, info)
	info = re.sub(r"\\u(-\d+)\?", uniconvert_neg, info)
	
	return info

def try_unicode(text, mod):
	encodings = ["utf8", "cp1252"]
	enc = get_module_encoding(mod)
	i = encodings.index(enc)
	try:
		return text.decode(enc)
	except UnicodeDecodeError:
		try:
			# ESV doesn't properly utf-8 copyright symbol in its about
			# so if we can't convert it to unicode, leave it as it is
			return text.decode(encodings[not i])
		except UnicodeDecodeError:
			return text.decode(enc, "replace")

class ModuleInfo(wx.Dialog):
	def __init__(self, parent, module):
		super(ModuleInfo, self).__init__(parent, title=_("Book Information"), 
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.module = module
		panel = wx.Panel(self)

		fields = (
			(N_("Name"), process(try_unicode(module.Name(), module)), -1), 
			(N_("Description"), 
				process(try_unicode(module.Description(), module)), 75),
			(N_("Language"),
				process(try_unicode(
						languages.get_language_description(module.Lang()), 
						module)), -1), 
			
			(N_("About"), process(
				try_unicode(module.getConfigEntry("About"), module)), 115), 
			(N_("License"), process(try_unicode(
						module.getConfigEntry("DistributionLicense"), 
						module
					)), 75)
		)

		self.add_fields(fields, panel)
		
		# now put the OK button on
		b = wx.Button(self, id=wx.ID_OK)
		s = wx.StdDialogButtonSizer()
		s.AddButton(b)
		s.Realize()

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(panel, 1, wx.GROW|wx.ALL, 10)
		sizer.Add(s, 0, wx.GROW|wx.ALL, 6)
		self.SetSizerAndFit(sizer)
	
	def add_fields(self, fields, panel):
		gs = wx.FlexGridSizer(len(fields) + 1, 2, 5, 5)
		gs.AddGrowableCol(1, 1)
		for id, (item, value, height) in enumerate(fields):
			label = wx.StaticText(panel, label=_(item)+":", 
				style=wx.ALIGN_RIGHT)
			font = label.Font
			font.Weight = wx.FONTWEIGHT_BOLD
			label.Font = font

			field = displayframe.DisplayFrame(panel, style=wx.SUNKEN_BORDER)
			field.mod = self.module
			field.SetBorders(1)
			
			wx.CallAfter(field.SetPage, value)

			# we get nasty horizontal scrollbars - by sending a size event
			# they disappear
			def SendSizeEvent(html):
				s = wx.SizeEvent(html.Size)
				s.EventObject = html
				html.EventHandler.ProcessEvent(s)

			wx.CallAfter(wx.CallAfter, SendSizeEvent, field)
			if height == -1:
				w, height = get_html_height(self.module, value)
				height += 8
			
			gs.AddGrowableRow(id, height)

			field.SetSize((250, height))

			gs.Add(label, 0, wx.GROW|wx.TOP, 3)
			gs.Add(field, 1, flag=wx.GROW)
		
		self.make_choice_field(panel, gs, fields)
		panel.SetSizerAndFit(gs)
			

	def make_choice_field(self, panel, gs, fields):
		self.variable_choice = wx.Choice(panel)
		
		config_map = self.module.getConfigMap()
		
		items = [
			(
				item.c_str(), 
				process(try_unicode(value.c_str(), self.module))
			) 
			for item, value in config_map.items()
		]

		self.variable_items = [(item, value) for item, value in items 
			if item not in (y[0] for y in fields)]
		
		self.variable_choice.Items = [x for x, y in self.variable_items]
		self.variable_choice.Selection = 0
		self.variable_choice.Bind(wx.EVT_CHOICE, self.update_value)

		self.variable_field = displayframe.DisplayFrame(panel, 
			style=wx.SUNKEN_BORDER)
		self.variable_field.mod = self.module			
		self.variable_field.SetBorders(1)
		self.update_value()
		
		
		gs.AddGrowableRow(len(fields), 75)
		gs.Add(self.variable_choice, 0, wx.TOP, 3)
		gs.Add(self.variable_field, 1, flag=wx.GROW)
		
		self.variable_field.SetSize((250, 75))
	
	def update_value(self, event=None):
		if self.variable_choice.Selection == -1:
			return

		value = self.variable_items[self.variable_choice.Selection][1]
		wx.CallAfter(self.variable_field.SetPage, value)

if __name__ == '__main__':
	from backend.bibleinterface import biblemgr
	app = wx.App(0)
	ModuleInfo(None, biblemgr.bible.mod).ShowModal()