import Sword as SW
import os
import re
import sys
from util.debug import *
from util.unicode import to_str, to_unicode
from util import is_py2exe
from util import classproperty
from util.observerlist import ObserverList

def _test():
	from swlib import pysw
	import doctest	
	print doctest.testmod(pysw)

if __name__ == '__main__':
	_test()

	# don't go any further, or we will crash after creating a versekey after 
	# the second stringmgr we construct (__main__ and swlib.pysw each have a
	# stringmgr)
	sys.exit()

# constants
REG_ICASE = 1 << 1
SWMULTI = -2
SWPHRASE = -1
SWREGEX = 0

POS_TOP = 1
POS_BOTTOM = 2
POS_MAXVERSE = 3
POS_MAXCHAPTER = 4
POS_MAXBOOK = 5

TOP = SW.SW_POSITION(POS_TOP)
BOTTOM = SW.SW_POSITION(POS_BOTTOM)
MAXVERSE = SW.SW_POSITION(POS_MAXVERSE)
MAXCHAPTER = SW.SW_POSITION(POS_MAXCHAPTER)
MAXBOOK = SW.SW_POSITION(POS_MAXBOOK)

# do renaming of SW.SWMgr -> SW.Mgr
for a in dir(SW):
	if(a[:2]=="SW"):
		setattr(SW, a[2:], getattr(SW, a))


if is_py2exe():
	# py2exe may get paths wrong
	if os.path.dirname(sys.argv[0]):
		os.chdir(os.path.dirname(sys.argv[0]))

if hasattr(sys, "SW_dont_do_stringmgr"):
	dprint(WARNING, "Skipping StringMgr initialization")
else:
	# StringMgr handling
	class MyStringMgr(SW.PyStringMgr):
		def getUpper(self, buf):
			# TODO: a more advanced heuristic like bibletime's to check whether it
			# is utf8 or latin1
			encodings = "UTF-8", "cp1252"
			text = buf.c_str()
			#print `text`
			for enc in encodings:
				try:
					# do an uppercase on the unicode object, then re-encode it 
					# back to how it was.
					# then set the buffer to the new string
					buf.set(text.decode(enc).upper().encode(enc))
					return
	
				except UnicodeDecodeError:
					pass
	
			dprint(WARNING, "Couldn't convert text to uppercase", text)
			buf.set(text.upper())
			return
	
		def supportsUnicode(self):
			return True
			
	
	m = MyStringMgr()
	
	# we don't own this, the system string mgr holder does
	m.thisown = False
	SW.StringMgr.setSystemStringMgr(m)
	
# *only* after we've set the system string mgr can we set the system 
# locale mgr...
locale_mgr = SW.LocaleMgr.getSystemLocaleMgr()
locale_mgr.loadConfigDir("resources/locales.d")

if locale_mgr.getLocale("bpbible"):
	locale_mgr.setDefaultLocaleName("bpbible")
else:
	dprint(WARNING, "bpbible locale not found")


class VerseParsingError(Exception): pass

def KeyExists(key_text, base_key=None):
	if base_key is None:
		base_key = u_vk
	
	SW.VerseKey.setText(base_key, key_text.encode(base_key.encoding))
	return not base_key.Error()

def set_vk_chapter_checked(self, chapter):
	chapters = self.chapterCount(ord(self.Testament()), ord(self.Book()))
	if 0 < chapter <= chapters:
		self.Chapter(chapter)
	else:
		raise VerseParsingError(_("There are only %(chapters)d chapters "
			"in %(book)s (given %(given)d)") % dict(
				chapters=chapters, book=self.getBookName(), 
				given=chapter
			)
		)
	
def set_vk_verse_checked(self, verse):
	chapter = self.Chapter()
	verses = self.verseCount(
		ord(self.Testament()), 
		ord(self.Book()), 
		chapter
	)
	if 0 < verse <= verses:
		self.Verse(verse)
	else:
		raise VerseParsingError(_("There are only %(verses)d verses in "
			"%(book)s %(chapter)s (given %(given)d)") % dict(
				verses=verses, book=self.getBookName(),
				chapter=chapter, given=verse
			)
		)

class VK(SW.VerseKey):#, object):
	"""VK - a wrapper around VerseKey
	
	A VK is a list of consecutive verses. Created like this:

	VK("Genesis 3:5")
	VK(("Genesis 3:5", "Genesis 3:8"))
	
	Modify like this:
	vk.text="Genesis 3:5'
	vk += 1

	>>> from swlib import pysw
	>>> pysw.VK("Genesis 3:5")
	VK('Genesis 3:5')
	>>> pysw.VK(("Genesis 3:5", "Genesis 3:8"))
	VK('Genesis 3:5-Genesis 3:8')
	>>> vk = pysw.VK("Genesis 3:5")
	>>> vk += 1
	>>> vk
	VK('Genesis 3:6')
	>>> vk.text = "Matt 5:3"
	>>> vk
	VK('Matthew 5:3')
	>>> vk = pysw.VK(("Genesis 3:5", "Genesis 3:8"))
	>>> vk == pysw.VerseList("genesis 3:5 - 8")[0]
	True
	>>> vk == None
	False
	>>> vk
	VK('Genesis 3:5-Genesis 3:8')
	>>> for item in vk:
	...     print item
	...     assert item != vk
	...
	Genesis 3:5
	Genesis 3:6
	Genesis 3:7
	Genesis 3:8
	"""

	encoding = "ascii"
	def __init__(self, key=()):
		if isinstance(key, basestring):
			#if not KeyExists(key):
			#	raise VerseParsingError, key
			SW.VerseKey.__init__(self, key.encode(self.encoding))
			if self.Error():
				raise VerseParsingError, key
			return
			
		if isinstance(key, SW.Key):
			SW.VerseKey.__init__(self, key)
			
			return

		if len(key)==2:
			#isinstance(key, tuple):
			top, bottom=key
			if not KeyExists(top):
				raise VerseParsingError, top
		
			if not KeyExists(bottom):
				raise VerseParsingError, bottom

		SW.VerseKey.__init__(self, *key)

	@classproperty
	def books(cls): return books

	def __cmp___(self, other): return self.compare(other)
	def __lt__( self, other): return self.compare(other)<0
	def __le__( self, other): return self.compare(other)<1
	def __gt__( self, other): return self.compare(other)>0
	def __ge__( self, other): return self.compare(other)>-1
	def __eq__(self, other):
		if other is None:
			return False

		if self.isBoundSet() != other.isBoundSet():
			return False

		if not self.isBoundSet():
			return self.equals(other)

		return (self.LowerBound().equals(other.LowerBound())
				and self.UpperBound().equals(other.UpperBound()))

	def __ne__(self, other):
		return not self == other

	# TODO: __nonzero__?
	def __str__(self): return to_unicode(self.getRangeText())
	def __repr__(self): return "%s('%s')" % (self.__class__.__name__, to_unicode(self.getRangeText()))

	def __iadd__(self, amount): 
		if amount < 0:
			return self.__isub__(-amount)
		self.increment(amount)
		return self
	
	def __isub__(self, amount):
		self.decrement(amount)
		return self
	
	def get_text(self):
		return self.__str__()
	
	def set_text(self, value):
		if(isinstance(value, basestring)):
			self.ClearBounds()

			if not KeyExists(value, self):
				raise VerseParsingError, value
				
			self.setText(value.encode(self.encoding))
		else:
			self.ClearBounds()
			
			top, bottom = value
			if not KeyExists(top, self):
				raise VerseParsingError, top
		
			if not KeyExists(bottom, self):
				raise VerseParsingError, bottom

			self.UpperBound(bottom)
			self.LowerBound(top)
	
	text = property(get_text, set_text)
	
	def set_text_checked(self, value):
		assert isinstance(value, basestring)
		an = self.AutoNormalize(0)
		try:
			self.setText(value)
			check_vk_bounds(self)

		finally:
			self.AutoNormalize(an)

	def __len__(self):
		if self.isBoundSet():
			self.setPosition(TOP)
			length=0
			while not self.Error():
				length+=1
				self+=1
			return length
		#else
		return 1


		if self.isBoundSet():
			#find out number of chapters
			upper=self.UpperBound()
			lower=self.LowerBound()
			if(upper>lower):
				lower, upper = upper, lower
			num=self.UpperBound().NewIndex()-self.LowerBound().NewIndex()+1
			#subtract one for each book, chapter and testament in the middle:
			if(upper.Chapter()==lower.Chapter()):
				return num
			num -= lower.Chapter() - upper.Chapter()
			if(upper.Book()==lower.Book()):
				return num
			if(upper.Testament()==lower.Testament()):
				num-=lower.Book()-upper.Book()
				uc=upper.getChapterCount(upper.Testament(), upper.Book())
				lc=upper.getChapterCount(lower.Testament(), lower.Book())
		return 1

	def __iter__(self):
		#class iterator(object):
		#	def __iter__(self):return self
		#	def next(self):
				
		if(not self.isBoundSet()):
			yield self
			raise StopIteration
		self.setPosition(TOP)
		while not self.Error():
			vk = VK()
			vk.Headings(self.Headings())
			vk.setText(SW.VerseKey.getText(self))
			yield vk

			self+=1

	def __getitem__(self, key):
		if not self.isBoundSet():
			if key == 0 or key == -1:
				return self
			raise IndexError, key
		if key < 0:
			self.setPosition(BOTTOM)
			for a in range(-key-1):
				self-=1
			if self.Error():
				raise IndexError, key
			return self.__class__(self.getText())

		self.setPosition(TOP)
		for a in range(key):
			self+=1#key
		if self.Error():
			raise IndexError, key
		return self.__class__(self.getText())

	def __reduce__(self):
		if self.isBoundSet():
			args = (self.LowerBound().getText(), self.UpperBound().getText())
		else:
			args = self.getText()
		return VK, (args,)
		
	def approxlen(self):
		"""The approximate length of this versekey.
		
		Faster than len. One extra for every chapter, book and testament 
		difference."""
		return self.UpperBound().NewIndex()-self.LowerBound().NewIndex()+1
	
	def _get(self, item):
		vk = VK()
		vk.this = item.this
		return vk

	#def UpperBound(self, to=None):
	#	if to is not None:
	#		return self._get(self.UpperBound(to))
	#	return self._get(self.UpperBound())
	#
	#def UpperBound(self, to=None):
	#	if to is not None:
	#		return self._get(self.UpperBound(to))
	#	return self._get(self.UpperBound())
		
		
	def clone(self): return VK(self)
	def Error(self): 
		return ord(SW.VerseKey.Error(self))
	
	def set_chapter(self, value):
		self.Chapter(value)
	
	def get_chapter(self):
		return self.Chapter()

	chapter = property(get_chapter, set_chapter)
	
	set_chapter_checked = set_vk_chapter_checked
	set_verse_checked = set_vk_verse_checked

	def get_book_chapter(self):
		return u"%s %d" % (self.getBookName(), self.Chapter())

		

			
	

	# horrible swig magic...
	__swig_setmethods__	 = {"text":set_text, "chapter":set_chapter}
	__swig_getmethods__	 = {"text":get_text, "chapter":get_chapter}
	for _s in [SW.VerseKey]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
	__setattr__ = lambda self, name, value: SW._swig_setattr(self, VK, name, value)
	__swig_getmethods__ = {}
	for _s in [SW.VerseKey]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
	__getattr__ = lambda self, name: SW._swig_getattr(self, VK, name)
	
class EncodedVK(VK):

	def getInternalVK(self):
		return VK(self)

	def getBookAbbrev(self):
		return super(EncodedVK, self).getBookAbbrev().decode(self.encoding)
	
	def getBookName(self):
		return super(EncodedVK, self).getBookName().decode(self.encoding)

	def LowerBound(self, text=None):
		if text is None:
			return super(EncodedVK, self).LowerBound()

		super(EncodedVK, self).LowerBound(text.encode(self.encoding))
	
	def UpperBound(self, text=None):
		if text is None:
			return super(EncodedVK, self).UpperBound()

		super(EncodedVK, self).UpperBound(text.encode(self.encoding))	
	
	def getText(self):
		return super(EncodedVK, self).getText().decode(self.encoding)
	
	def getRangeText(self):
		return super(EncodedVK, self).getRangeText().decode(self.encoding)
		
		

class UserVK(EncodedVK):
	def __init__(self, arg=None):
		if isinstance(arg, SW.Key):
			super(UserVK, self).__init__(arg)
			arg = None

		else:
			super(UserVK, self).__init__()

		self.setLocale(locale_lang)
		self.encoding = locale_encoding
		
		if arg is not None:
			self.set_text(arg)

	def getBookAbbrev(self):
		return AbbrevVK(self).getBookName().decode(self.encoding)	
	
	def getBookName(self):
		return process_dash_hack(
			super(UserVK, self).getBookName(), locale_dash_hack
		)
		
	def getText(self):
		return process_dash_hack(
			super(UserVK, self).getText(), locale_dash_hack
		)
		
	def getRangeText(self):
		return process_dash_hack(
			super(UserVK, self).getRangeText(), locale_dash_hack
		)

class AbbrevVK(EncodedVK):
	def __init__(self, arg=None):
		if isinstance(arg, SW.Key):
			super(AbbrevVK, self).__init__(arg)
			arg = None

		else:
			super(AbbrevVK, self).__init__()

		self.setLocale(abbrev_locale_lang)
		self.encoding = abbrev_locale_encoding
		
		if arg is not None:
			self.set_text(arg)

	def getBookName(self):
		return process_dash_hack(
			super(AbbrevVK, self).getBookName(), abbrev_locale_dash_hack
		)
	
	def getText(self):
		return process_dash_hack(
			super(AbbrevVK, self).getText(), abbrev_locale_dash_hack
		)
	
	def getRangeText(self):
		return process_dash_hack(
			super(AbbrevVK, self).getRangeText(), abbrev_locale_dash_hack
		)
		
		

def check_vk_bounds(vk):	
	"""Check that a given VK was in bounds. Autonormalize should be turned off
	before calling this method"""
	#print vk.getText()
	#if vk.isBoundSet():
	#	check_vk_bounds(vk.UpperBound())
	#	check_vk_bounds(vk.LowerBound())
	#	return
		
	testament, book = ord(vk.Testament()), ord(vk.Book())
	chapters = vk.chapterCount(testament, book)
	chapter = vk.Chapter()

	if chapter > chapters:
		raise VerseParsingError(_("There are only %(chapters)d chapters "
			"in %(book)s (given %(given)d)") % dict(
				chapters=chapters, book=vk.bookName(testament, book), 
				given=chapter
			)
		)

	verse = vk.Verse()
	verses = vk.verseCount(testament, book, chapter)
	
	if verse > verses:
		raise VerseParsingError(_("There are only %(verses)d verses in "
			"%(book)s %(chapter)s (given %(given)d)") % dict(
				verses=verses, book=vk.bookName(testament, book), 
				chapter=chapter, given=verse
			)
		)
	

#	def ParseVerseList(self, range, context="", expand=True):
#		"""Return a VerseList made from the range"""
#		result=SW.VerseKey.ParseVerseList(self, range, context, expand)
#		return VerseList(result)

class VerseList(list): 
	"""A list of VK's

	Construct like this:
	VerseList([VK("Genesis 3:1"), VK("Genesis 3:3")])
	VerseList("3:10-12", "Matthew")
	VerseList(SW.ListKey()) """
	REPLACEMENTS = [
		# Mat. 4v6 -> Mat. 4:6
		(r"""
		(\d) # any digit
		\s*  # some optional whitespace
		v    # the letter v
		\s*  # more optional whitespace 
		(\d) # and then another digit""", r"\1:\2"),

		# Mat. 4 6 -> Mat. 4:6
		(r"""
		(?P<word>(			# match a word without numbers or underscore
			(?=[^\d_])		# following letter is not a digit
			\w				# but is alphanumeric
		)+)
		\s*					# and then possibly whitespace
		(?P<chapter>\d+)	# digits
		\s+					# some whitespace
		(?P<verse>\d+)		# and more digits
		""", "\g<word> \g<chapter>:\g<verse>"),

		# Hakim-Hakim 3:5-9 -> HakimHakim
		(r"""
		([^\s\d:.,;])
		-
		([^\s\d:.,;])""", r"\1\2"),
	]
	replacements = [(re.compile(f, flags=re.VERBOSE|re.UNICODE), t) 
						for f, t in REPLACEMENTS]
	

	def __init__(self, args=None, context="", expand=True, raiseError=False,
				userInput=False, userOutput=False):
		converted = False

		if(isinstance(args, (list, tuple))):
			assert not userInput
			args2 = []
			for a in args:
				if(isinstance(a, SW.VerseKey)):
					args2.append(a)
				else:
					args2.append(VK(a))
			list.__init__(self, args2)
			return

		locale_changed = False
		if isinstance(args, basestring):
			orig_args = args
			for matcher, replacement in self.replacements:
				args = matcher.sub(replacement, args)
			
			args = to_str(args)
			context = to_str(context)
			s = args

			if userInput:
				vk = u_vk
				locale = locale_lang
				
			else:
				vk = i_vk
				locale = locale_mgr.getDefaultLocaleName()

			try:
	
				# make sure we have this set correctly
				# TestForError uses this, 
				# as does ParseVerseList with expand on
				old = locale_mgr.getDefaultLocaleName()
				if old != locale:
					locale_mgr.setDefaultLocaleName(locale)
					locale_changed = True
				
				if not raiseError:
					args = vk.ParseVerseList(args, context, expand)

				else:
					an = vk.AutoNormalize(0)
					try:
						args = vk.ParseVerseList(args, context, expand)
						self.TestForError(s, context, orig_args)
					finally:
						vk.AutoNormalize(an)
			finally:
				if locale_changed:
					if old != locale:
						locale_mgr.setDefaultLocaleName(old)
						

		if(isinstance(args, SW.ListKey)):
			if userOutput:
				KeyType = UserVK
			else:
				KeyType = VK

			self.RefreshVKs(args, raiseError=raiseError, KeyType=KeyType,
			userInput=userInput, userOutput=userOutput)

		else:
			raise TypeError, `args`

			
				
			

		for a in self:
			if a[-1]==VK("rev 22:21"):
				dprint(WARNING, "Possibly incorrect string. Result is", self)


	def TestForError(self, args, context, orig_args):
		"""Check whether a given referencelist looks good.
		The default locale must be the locale for this VerseList
		
		>>> from swlib import pysw
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Matt en 3:15", "5", "Matt en 3:15")
		Traceback (most recent call last):
		  File "<stdin>", line 1, in <module>
		  File "swlib\pysw.py", line 301, in TestForError
		    raise VerseParsingError, "Invalid Reference: %s" % args
		VerseParsingError: Invalid Reference: Matt en 3:15
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Test", "5", "Test")
		Traceback (most recent call last):
		  File "<stdin>", line 1, in <module>
		  File "swlib\pysw.py", line 301, in TestForError
		    raise VerseParsingError, "Invalid Reference: %s" % args
		VerseParsingError: Invalid Reference: Test
		
		
		"""
		# not a very nice way, I'm afraid :(
		# expected osisref: <reference osisRef="Gen.3.5">gen 3:5</reference>
		#<reference osisRef="Gen.3.1-Gen.3.24">gen 3</reference>
		# wrong osisrefs: x
		# <reference osisRef="Gen.3.5-Rev.22.21">gen 3:5 -</reference> foobar'
		my_re = r'\s*(<reference osisRef=[^>]*>[^>]*</reference>((;|,)?\s*))+$'
		osis_ref = VK.convertToOSIS(args, SW.Key(context))
		match = re.match(my_re, osis_ref)

		if not match:
			raise VerseParsingError(_(u"Invalid Reference: %s") % orig_args)

	def RefreshVKs(self, lk, raiseError=False, KeyType=VK, 
		userInput=False, userOutput=False):
		"""Turns a listkey into a VerseList"""
		#TODO: error
		l=[]
		#clear list
		del self[:]
		while lk.Error()=='\x00':
			l.append(lk.GetElement(len(l)))
	
		for a in l:
			if(not a):
				continue
			v=SW.VerseKey.castTo(a)
			if not v:
				key = get_a_key(userInput)

				#1 verse only
				t = a.getText()
				if "-" in t:
					t = t.replace("-", "")

				if not raiseError:
					key.text = t
				else:
					key.AutoNormalize(False)
					key.set_text_checked(t)
					key.AutoNormalize(True)

				v = KeyType(key)
					

			else:
				check_vk_bounds(v)

				if userInput != userOutput or userOutput:
					assert userInput

					# we need to do this carefully
					# if we just copy across the bounds get mussed when they
					# have dashes. We don't want this happening, so set the
					# bounds separately.
					# Use VerseKey's getText so we don't worry about unicode
					v = KeyType((
						SW.VerseKey.getText(VK(v.LowerBound())),
						SW.VerseKey.getText(VK(v.UpperBound())),
					))
				
				else:
					# if we stay inside, just use a straight copy
					v=KeyType(v)
					
			self.append(v)
			
	
	def __iadd__(self, amount):
		if(isinstance(amount, VerseList)):
			list.__iadd__(self, amount)
			return self
		if(not isinstance(amount, VK)):
			amount=VK(amount)
		
		list.__iadd__(self, [amount])
		return self
	
	def __add__(self, amount):
		if(isinstance(amount, VerseList)):
			return VerseList(list.__add__(self, amount))
		if(not isinstance(amount, VK)):
			amount=VK(amount)
		return VerseList(list.__add__(self, [amount]))
	
	def keyallowed(self, value):
		if not isinstance(value, VK):
			value=VK(value)
		return value

	def append(self, value): 
		return list.append(self, self.keyallowed(value))

	def __setitem__(self, name, value):
		return list.__setitem__(self, name, self.keyallowed(value))
	
	def getRangeText(self):	
		return "; ".join(item.text for item in self)

	def VerseInRange(self, verse):#, range, context="", vklist=None):
		#if not(vklist): #lastrange and range==lastrange):
		#	vklist=GetVKs(range, context)
		try:
			vk=VK(verse)
		except VerseParsingError, e:
			return False
		for a in self: #vklist:
			if(vk>=a[0] and vk<=a[-1]):
				return True
		return False


	def GetBestRange(self, short=False):#text, context=""):
		"""
		>>> from swlib.pysw import GetBestRange
		>>> GetBestRange("Gen 3:16")
		'Genesis 3:16'
		>>> GetBestRange("Gen 3:3-5")
		'Genesis 3:3-5'
		>>> GetBestRange("Gen 3:16-gen 4:5")
		'Genesis 3:16-4:5'
		>>> GetBestRange("Gen 3-ex5:3")
		'Genesis 3:1-Exodus 5:3'
		>>> GetBestRange("Gen 3-5")
		'Genesis 3-5'
		>>> GetBestRange("Gen 3-matt 5")
		'Genesis 3-Matthew 5'
		>>> GetBestRange("Gen 3:3-5", abbrev=True)
		'Gen 3:3-5'
		>>> GetBestRange("Gen 3-Matt 5", abbrev=True)
		'Gen 3-Matt 5'
		>>> GetBestRange("Psa 58:0-1") # a bit of a dodgy case
		'Psalms 57:11-58:1'
		>>> GetBestRange("Matthew 24v27-30,44")
		'Matthew 24:27-30,44'
		>>> GetBestRange("Matthew 24 27")
		'Matthew 24:27'
		>>> GetBestRange("Matthew 24:27 28")
		'Matthew 24:27,28'
		>>> GetBestRange("Genesis 2 ")
		'Genesis 2'
		>>> GetBestRange("Genesis 2:3 ")
		'Genesis 2:3'
		>>> GetBestRange("Genesis 2 3")
		'Genesis 2:3'
		>>> GetBestRange("Matthew 5:3")
		'Matthew 5:3'
		>>> GetBestRange("Matthew 5")
		'Matthew 5'
		>>> GetBestRange("Genesis 3:5-9, 13-15;17")
		'Genesis 3:5-9,13-15,17'
		>>> GetBestRange("Genesis 3:5,8, 13:15")
		'Genesis 3:5,8;13:15'
		>>> GetBestRange("Gen 3:15-18, 23;Matt 5:3-8")
		'Genesis 3:15-18,23;Matthew 5:3-8'
		>>> GetBestRange("Jude")
		'Jude 1'
		>>> GetBestRange("Mark 15:23")
		'Mark 15:23'
		>>> GetBestRange("Jude 1:5")
		'Jude 1:5'
		>>> GetBestRange("Gen 3:23,24")
		'Genesis 3:23,24'
		>>> GetBestRange("Gen 3:23,24;1,5")
		'Genesis 3:23,24,1,5'
		>>> GetBestRange("Gen 4:5, Exodus 23:1")
		'Genesis 4:5;Exodus 23:1'
		>>> GetBestRange("Gen, Exodus")
		'Genesis 1-50;Exodus 1-40'
		>>> # need Genesis to make it a chapter ref
		... # TODO this could be Genesis 4,5
		... GetBestRange("Gen 4,5") 
		'Genesis 4;Genesis 5'
		>>> # need Genesis to make it a chapter ref	
		... # TODO this might be done as Genesis 4:1, ch 5?
		... # TODO this is interpreted by SWORD as verse 5, not chapter 5
		... GetBestRange("Gen 4:1,Genesis 5")
		'Genesis 4:1,Genesis 5'
		>>> GetBestRange("1 Chr 2:5-2 Chr 3:9")
		'1 Chronicles 2:5-2 Chronicles 3:9'
		>>> GetBestRange("v5")
		'Revelation 1:5'
		>>> GetBestRange("Gen.4.5")
		'Genesis 4:5'
		"""
		
		def getdetails(versekey):
			if short: 
				book = versekey.getBookAbbrev()
			else: 
				book = versekey.getBookName()

			chapter = versekey.Chapter()
			verse = versekey.Verse()

			chapter_verses = versekey.verseCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
				chapter
			)

			return book, chapter, verse, chapter_verses

		#take details of first and last of each VK
		l2 = [[getdetails(vk) for vk in (item[0], item[-1])] for item in self]
				
		# book, chapter, verse
		lastbook, lastchapter, lastverse = None, None, None
		range = ""

		for item in l2:
			((book1, chapter1, verse1, verse_count1), 
			 (book2, chapter2, verse2, verse_count2)) = item

			# check whether we have a chapter range
			# this means that the first verse is verse 1 and the second one is
			# the last in the chapter
			if (verse1, verse2) == (1, verse_count2):
				if not range:
					separator=""
				
				else:
					separator=";"

				range += separator

				if (book1, chapter1) != (book2, chapter2):
					range += "%s %d-" % (book1, chapter1)
				
					if book1 != book2:
						range += "%s %d" % (book2, chapter2)
					else:
						range += "%d" % (chapter2)
					
				else:
					range += "%s %d" % (book2, chapter2)
				
				lastbook, lastchapter, lastverse = book2, chapter2, verse2
				continue
				
					
			for idx, (book, chapter, verse, _) in enumerate(item):
				if (book, chapter, verse) == (lastbook, lastchapter, lastverse):
					break

				# if we don't have a range, no separator
				if not range:
					separator = ""
				
				# if we are the second item in a pair, use a -
				elif idx:
					separator = "-"

				# use comma to separate when in the same chapter				
				elif (book, chapter) == (lastbook, lastchapter):
					separator = ","
				
				else:
					separator = ";"
				
				range += separator

				if book != lastbook:
					range += "%s %d:%d" % (book, chapter, verse)

				elif chapter != lastchapter:
					range += "%d:%d" % (chapter, verse)

				elif verse != lastverse:
					range += "%d" % (verse)

				lastbook, lastchapter, lastverse = book, chapter, verse
			
		return range			

	
	def getListKey(self):
		lk=SW.ListKey()
		#add verses
		map(lk.add, self)
		return lk

	def sorted(self):
		"""Sort the list into Biblical order and returns a new VerseList
		
		>>> from swlib import pysw
		>>> pysw.VerseList("Gen 3:3-5").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5')])
		>>> pysw.VerseList("Gen 3:3-5;Matt 15:10").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		>>> pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Jonah 4:5-Micah 1:12'), VK('Matthew 15:10')])
		>>> vl = pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10")
		>>> vl.sorted() is vl
		False
		"""
		lk=self.getListKey()
		lk.sort()
		return VerseList(lk)
	
	def sort(self):
		"""
		>>> from swlib import pysw
		>>> vl = pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10")
		>>> vl
		VerseList([VK('Jonah 4:5-Micah 1:12'), VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		>>> vl.sort()
		>>> vl
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Jonah 4:5-Micah 1:12'), VK('Matthew 15:10')])
		"""
	
		lk=self.getListKey()
		lk.sort()
		self.RefreshVKs(lk)

	def __repr__(self):
		"""
		>>> from swlib import pysw
		>>> vl = pysw.VerseList("Jonah3:1-3;4:5,Gen 3:3-5;Matt 15:10")
		>>> vl
		VerseList([VK('Jonah 3:1-Jonah 3:3'), VK('Jonah 4:5'), VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		
		"""
	
		return "VerseList([%s])" % ", ".join(map(repr, self))

	def __str__(self): return self.GetBestRange() #Text()

	def clone(self): return VerseList(self)

class BookData(object):
	def __init__(self, bookname, testament, booknumber):
		self.chapters=[]
		self.bookname=bookname
		self.testament=testament
		self.booknumber=booknumber
	
	def __repr__(self):
		return "<BookData: %s>" % self.bookname

	def __str__(self):
		return self.bookname

	def __getitem__(self, item):
		return self.chapters[item]

	def __len__(self):
		return len(self.chapters)
	
	def __iter__(self):
		for item in range(len(self.chapters)):
			yield ChapterData(
				item+1, 
				i_vk.verseCount(self.testament, self.booknumber, item + 1),
			)

class ChapterData(object):
	"""A class so that we can tell it is chapter data"""
	def __init__(self, chapter_number, chapter_length):
		self.chapter_number = chapter_number
		self.chapter_length = chapter_length

	def __iter__(self):
		return iter(xrange(1, self.chapter_length+1))
	
	def __len__(self):
		return self.chapter_length
	
	def __str__(self):
		return "%s" % self.chapter_number

books = []
i_vk = VK()
i_vk.Book(1)

while not i_vk.Error():
	t = ord(i_vk.Testament())
	b = ord(i_vk.Book())
	n = i_vk.bookName(t, b)
	books.append(BookData(n, t, b))
	i_vk.Book(ord(i_vk.Book()) + 1)

for book in books:
	for chapter in range(i_vk.chapterCount(book.testament, book.booknumber)):
		book.chapters.append(
			ChapterData(chapter+1, 
				i_vk.verseCount(book.testament, book.booknumber, chapter+1)
			)
		)
del book
del chapter

locale_changed = ObserverList()

def get_dash_hack(locale):
	lookup = {}
	for testament in range(locale.getNumBookGroupings()):
		for book in range(locale.getNumBooks(testament)):
			b = locale.getBook(testament, book)
			with_dash = locale.translate(b.name)
			if with_dash != b.name:
				lookup[b.name] = with_dash
				print b.name, "->", with_dash
	
	return lookup

	desc = locale.getDescription()
	section = re.search(r"\(dash-hack:([^\)]*)\)", desc)
	if not section:
		return {}
	
	# print section.group(1)
	
	lookup = {}
	for key, value in re.findall("([^=]*)=([^,]*),?", section.group(1)):
		lookup[key] = value
	
	return lookup
		
def change_locale(lang, abbrev_lang):
	global locale, locale_lang, locale_encoding, locale_dash_hack
	global abbrev_locale, abbrev_locale_lang, abbrev_locale_encoding
	global abbrev_locale_dash_hack
	locale = locale_mgr.getLocale(lang)
	if not locale:
		dprint(WARNING, "Couldn't find locale %r" % lang,
		[x.c_str() for x in locale_mgr.getAvailableLocales()])
		locale_lang = lang
		locale_encoding = "ascii"
		locale_dash_hack = {}
		
	
	else:
		locale_lang = lang
		locale_encoding = locale.getEncoding()
		locale_dash_hack = get_dash_hack(locale)

	
	abbrev_locale = locale_mgr.getLocale(abbrev_lang)
	if abbrev_locale:
		abbrev_locale_lang = abbrev_lang
		abbrev_locale_encoding = abbrev_locale.getEncoding()
		abbrev_locale_dash_hack = get_dash_hack(abbrev_locale)
	
	
	else:
		dprint(WARNING, "Couldn't find locale %r" % abbrev_lang,
		[x.c_str() for x in locale_mgr.getAvailableLocales()])
		abbrev_locale_lang = locale_lang
		abbrev_locale_encoding = locale_encoding
		abbrev_locale_dash_hack = locale_dash_hack
		
		
	locale_changed(locale, lang, abbrev_locale, abbrev_lang)

change_locale("en_AU", "abbrev")#"ko", "ko_abbrev")
u_vk = UserVK()
a_vk = AbbrevVK()


def change_vk_locale(locale, lang, abbrev_locale, abbrev_lang):
	if locale:
		u_vk.setLocale(lang)
		u_vk.encoding = locale_encoding

	if abbrev_locale:
		a_vk.setLocale(abbrev_lang)
		a_vk.encoding = abbrev_locale_encoding

locale_changed += change_vk_locale

class TK(SW.TreeKeyIdx):
	"""A tree key. As this is module specific, create it from an existing tree
	key retrieved from the module"""

	def __init__(self, tk, module=None):
		# result of tk.clone() is unowned
		tk2 = SW.TreeKeyIdx.castTo(tk.clone())

		# use the same swig pointer as the other, then kill the other
		self.this = tk2.this
		del tk2

		# we own this now
		self.thisown = True
		
		self.tk = self
		self.module = module
		if module is None and hasattr(tk, "module"):
			self.module = tk.module
		
		assert self.module, "Moduleless tree key :("

	def check_changed(self):
		pass

	def __iter__(self):
		self.check_changed()
		cls = type(self)
		tk = cls(self.tk)
		if(tk.firstChild()):
			yield cls(tk)
			while(tk.nextSibling()):
				yield cls(tk)

	def __repr__(self):
		self.check_changed()
	
		return "<%s(%s)>" % (type(self).__name__, 
			to_unicode(self.getText(), self.module))
	
	def __str__(self):
		self.check_changed()
	
		return to_unicode(self.getLocalName(), self.module)
	
	def __getitem__(self, key):
		self.check_changed()
	
		return [a for a in self][key]

	def breadcrumb(self, include_home=None, delimiter=" > "):
		self.check_changed()
	
		breadcrumb = [unicode(self)]
		bref = TK(self)
		while bref.parent():
			breadcrumb.append(unicode(bref))

		if include_home:
			breadcrumb[-1] = include_home
		else:
			del breadcrumb[-1]

		return delimiter.join(breadcrumb[::-1])
	
	def get_text(self):
		self.check_changed()
	
		return to_unicode(self.getText(), self.module)

	def set_text(self, value):
		self.setText(to_str(value, self.module))
	
	# horrible swig magic...
	__swig_setmethods__	 = {"text":set_text}
	__swig_getmethods__	 = {"text":get_text}
	for _s in [SW.TreeKeyIdx]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
	__setattr__ = lambda self, name, value: SW._swig_setattr(self, TK, name, value)
	__swig_getmethods__ = {}
	for _s in [SW.TreeKeyIdx]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
	__getattr__ = lambda self, name: SW._swig_getattr(self, TK, name)
	
	text = property(get_text, set_text)


class ImmutableTK(TK):
	"""A TK which is immutable - it can't/shouldn't be changed.

	Don't assign this to a module permanently - i.e. with Persist turned on,
	or it may be changed by something moving the module position.

	This will raise errors if it detects a change."""
	def __init__(self, *args, **kwargs):
		super(ImmutableTK, self).__init__(*args, **kwargs)
		self.immutable = self.getText()

	def check_changed(self):
		if self.immutable != self.getText():
			raise TypeError, "Detected mutating ImmutableTK"

	def error(self, *args, **kwargs):
		raise TypeError, "This is immutable"
	
	increment = setText = set_text = root = error

# -- Utility functions
def GetVerseStr(verse, context = "", raiseError=False, 
	userInput=False, userOutput=False):
	"""Returns a standardized verse string"""
	if not verse:
		if raiseError:
			raise VerseParsingError, _("Invalid empty reference")
			
		return ""
		#assert verse

	# Parse List (This is for context)
	verse_split = verse.split(";")[0].split(",")[0]

	vklist = VerseList(verse_split, context, expand=False,
		raiseError=raiseError, userInput=userInput)
	if not vklist: 
		if raiseError:
			raise VerseParsingError, _(u"Invalid Reference: %s") % verse

		else:
			return ""
	
	vk = vklist[0]

	if userInput != userOutput:
		assert userInput
		return VK(vk[0]).text
		
	return vk[0].text

def process_dash_hack(text, lookup):
	for item, value in lookup.items():
		text = text.replace(item, value)
	
	return text
		
def abbrev_to_user(key):
	return VK(key).text

def internal_to_user(key):
	return UserVK(VK(key)).text
	
def user_to_internal(key):
	return VK(UserVK(key)).text

def get_a_key(userInput):
	if userInput:
		return u_vk
	else:
		return i_vk

def GetBookChapter(string, context=""):
	chapter = i_vk.ParseVerseList(
		to_str(string), to_str(context), True
	).getText()#.decode(locale_encoding)
	index = chapter.find(":")
	
	if index != -1:
		chapter = chapter[:index]
	return chapter
	

def BookName(text):
	#TODO: u_vk or i_vk?
	u_vk.setText(to_str(text))
	if u_vk.Error(): return None
	return u_vk.getBookName()

def GetBestRange(text, context="", abbrev=False, raiseError=False,
		userInput=False, userOutput=False):
	vl = VerseList(text, context=context, raiseError=raiseError,
		userInput=userInput, userOutput=userOutput)
	return vl.GetBestRange(abbrev)

class Searcher(SW.Searcher):
	def __init__(self, book, userdata = None):
		SW.Searcher.__init__(self, book.mod)
		self.mod = book.mod
		self.callback = None
		self.userdata = userdata
		self.vk = VK()
		self.vk.thisown = False

	def PercentFunction(self, number):
		if(self.callback):
			continuing = self.callback(number, self.userdata)
			if not continuing:
				self.TerminateSearch()
	
	def Search(self, string, options=0, scopestr=None, case_sensitive=False):
		self.mod.setKey(self.vk)

		scope = None
		if(scopestr):
			# TODO: this is VerseKey specific
			scope = self.vk.ParseVerseList(to_str(scopestr), "", True)

		verseslist = self.doSearch(string, options, 
			(not case_sensitive)*REG_ICASE, scope)

		strings = verseslist.getRangeText()

		if not strings: 
			return []
		
		# TODO: ;'s don't cut it - in the ISBE, they are often used		
		return strings.split("; ")


