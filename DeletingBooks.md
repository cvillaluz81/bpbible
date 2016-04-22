# Introduction #

If you have downloaded and installed a book, you may want to delete the book if you do not want to use it any more. As of BPBible 0.4, books can be deleted in the book manager (File > Manage Books). This is much easier than the manual method detailed below.

**Warning:**
You cannot undo this deletion.

# Details #
NOTE: this method is now not required or recommended.
  1. Find which path the book is in. If you have the portable version of BPBible, it is likely to be in the resources directory.  If you don't know the path, try each path mentioned in `File > Set SWORD paths`.
  1. Go to the mods.d folder in that path. Look for a file called _module\_abbreviation_.conf (where _module\_abbreviation_ is the abbreviation of the module - e.g. ESV for the English Standard Version).
  1. Open this up in a text editor, and look for the line starting with DataPath= to find out where the module data is stored. For example, if DataPath=./modules/texts/ztext/esv/, then the folder is modules\texts\ztext\esv (going from the starting path found in point 1 above). For books other than bibles and commentaries, the abbreviation will be repeated twice on the end. Ignore the second one.
  1. Delete the folder. This will free up most of the disk space used by the module.
  1. Delete the _module\_abbreviation_.conf found in step 2. This will stop the book appearing in BPBible.

So if the path you are using is c:\Sword, and you are trying to delete the ESV, you will need to delete the file c:\sword\mods.d\esv.conf and the folder c:\sword\modules\texts\ztext\esv\