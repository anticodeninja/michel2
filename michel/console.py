#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

if os.name == 'posix':
  UP_CURSOR_CODE = "\033[A"
  CLEAN_ROW_CODE = "\033[K"
  
  def cleanLastRows(amount):
    print((UP_CURSOR_CODE + CLEAN_ROW_CODE) * amount + UP_CURSOR_CODE)

elif os.name == 'nt':
  import ctypes
  from ctypes import LibraryLoader
  from ctypes import wintypes

  class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    """struct in wincon.h."""
    _fields_ = [
      ("dwSize", wintypes._COORD),
      ("dwCursorPosition", wintypes._COORD),
      ("wAttributes", wintypes.WORD),
      ("srWindow", wintypes._SMALL_RECT),
      ("dwMaximumWindowSize", wintypes._COORD)]

    def __str__(self):
      return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
        self.dwSize.Y, self.dwSize.X,
        self.dwCursorPosition.Y, self.dwCursorPosition.X,
        self.wAttributes,
        self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right,
        self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X,
      )

  STDOUT = -11

  windll = LibraryLoader(ctypes.WinDLL)
  stdout_handle = windll.kernel32.GetStdHandle(STDOUT)

  def cleanLastRows(amount):
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    windll.kernel32.GetConsoleScreenBufferInfo(stdout_handle, ctypes.byref(csbi))
    
    pos = wintypes._COORD(0, csbi.dwCursorPosition.Y-amount)
    written = wintypes.DWORD(0)
    windll.kernel32.FillConsoleOutputCharacterA(stdout_handle,
                                                ctypes.c_char(32),
                                                wintypes.DWORD(csbi.dwSize.X * amount),
                                                pos,
                                                ctypes.byref(written))
    windll.kernel32.SetConsoleCursorPosition(stdout_handle, pos)
    
else:
  print("Sorry, your OS is not supported, please contact with a developer")
  sys.exit(2)
