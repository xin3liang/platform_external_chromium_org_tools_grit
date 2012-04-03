#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Formats as a .C file for compilation.
"""

import os
import re
import types

from grit import util
from grit.format import interface
from grit.node import io


class TopLevel(interface.ItemFormatter):
  """Writes out the required preamble for C files."""

  def Format(self, item, lang='en', output_dir='.'):
    """Format the C file header."""
    assert isinstance(lang, types.StringTypes)
    # Find the location of the resource header file, so that we can include
    # it.
    resource_header = 'resource.h'  # fall back to this
    for output in item.GetRoot().GetOutputFiles():
      if output.attrs['type'] == 'rc_header':
        resource_header = os.path.abspath(output.GetOutputFilename())
        resource_header = util.MakeRelativePath(output_dir,
                                                resource_header)
    return """//  Copyright %d Google Inc. All Rights Reserved.
// This file is automatically generated by GRIT.  Do not edit.

#include "%s"

// All strings are UTF-8
""" % (util.GetCurrentYear(), resource_header)
# end Format() function


class StringTable(interface.ItemFormatter):
  """Outputs a C switch statement representing the string table."""

  def Format(self, item, lang='en', output_dir='.'):
    """Format the start of the table."""
    assert isinstance(lang, types.StringTypes)
    return 'const char* GetString(int id) {\n  switch (id) {'

  def FormatEnd(self, item, lang='en', output_dir='.'):
    """Format the end of the table."""
    assert isinstance(lang, types.StringTypes)
    return '\n    default:\n      return 0;\n  }\n}'


def _HexToOct(match):
  "Return the octal form of the hex numbers"
  hex = match.group("hex")
  result = ""
  while len(hex):
    next_num = int(hex[2:4], 16)
    result += "\\" + '%03d' % int(oct(next_num), 10)
    hex = hex[4:]
  return match.group("escaped_backslashes") + result


class Message(interface.ItemFormatter):
  """Writes out a single message as part of the switch."""

  def Format(self, item, lang='en', output_dir='.'):
    """Format a single message."""
    from grit.node import message
    assert isinstance(lang, types.StringTypes)
    assert isinstance(item, message.MessageNode)

    message = item.ws_at_start + item.Translate(lang) + item.ws_at_end
    # output message with non-ascii chars escaped as octal numbers
    # C's grammar allows escaped hexadecimal numbers to be infinite,
    # but octal is always of the form \OOO
    message = message.encode('utf-8').encode('string_escape')
    # an escaped char is (\xHH)+ but only if the initial
    # backslash is not escaped.
    not_a_backslash = r"(^|[^\\])"  # beginning of line or a non-backslash char
    escaped_backslashes = not_a_backslash + r"(\\\\)*"
    hex_digits = r"((\\x)[0-9a-f]{2})+"
    two_digit_hex_num = re.compile(
      r"(?P<escaped_backslashes>%s)(?P<hex>%s)"
      % (escaped_backslashes, hex_digits))
    message = two_digit_hex_num.sub(_HexToOct, message)
    # unescape \ (convert \\ back to \)
    message = message.replace('\\\\', '\\')
    message = message.replace('"', '\\"')
    message = util.LINEBREAKS.sub(r'\\n', message)

    name_attr = item.GetTextualIds()[0]

    return '\n    case %s:\n      return "%s";' % (name_attr, message)
