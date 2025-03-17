# SPDX-FileCopyrightText: 2025 Vincent Marchetti
#
# SPDX-License-Identifier: GPL-3.0-or-later

__all__ = ['encode', 'decode']

import logging
logger = logging.getLogger("mfstring")
logger.addHandler( logging.NullHandler() )
logger.setLevel( logging.WARN )

"""
The _ONLY_WARN_ON_ERRORS_ module level value will specify the behavior
when function argument string values cannot be interpreted as validly encoded
SFString or MFString values

When _ONLY_WARN_ON_ERRORS_ is False, an invalid encoding will result in an Exception
being raised.

Client code can set _ONLY_WARN_ON_ERRORS_ to be true, in which case no exception will be
thrown, only a logging module WARN level message will be omitted. It is up to client
code to decide on the disposition of that warning.

Use case for this loosey-goosey behavior is for use in a tolerant X3D importer which
would process MFString encodings with invalidly encoded SFString items without raising
an Exception.

The only goal of setting _ONLY_WARN_ON_ERRORS_ to false is to avoid throwing an exception,
no intent is claimed provide a useful decoded value from the function
"""
_ONLY_WARN_ON_ERRORS_ = True

"""
Python (targeting 3.7) implementation of the rules for
encoding X3D MFString values into a single unicode string.
"""

BACKSLASH=u"\u005C"   # unicode REVERSE_SOLIDUS, the \ character
QUOTE_MARK= u"\u0022" # double quotes "
SPACE=u" "
ITEM_SEPARATORS = u", \n\r\t" # allowed without warning between list items

from io import StringIO

class SlashEncodingError(ValueError):
    "Exception thrown when an a string cannot be slash-decoded"

    def __init__(self,xString, *tups, **keyw):
        """initialize SlashEncodingError

        xString: the unicode string that fails as argument to slash_decoding
        """
        self.encodedString = xString
        Exception.__init__(self,xString, *tups, **keyw)

    def __str__(self):
        return "invalid slash-encoded value: {%s}" % (self.encodedString,)

class ListEncodingError(ValueError):
    "Exception thrown when an a string cannot be decoded as a list of strings"
    def __init__(self,xString, *tups, **keyw):
        """initialize ListEncodingError

        xString : the unicode string that fails as argument to decoding
        """
        Exception.__init__(self,xString, *tups, **keyw)

    def __str__(self):
        return "invalid slash-encoded value: {%s}" % self.args[0]


def slash_encode(aString):
    """Applies escaping to backslash and quote character

    Applied to elements of an MFString collection to allow the complete
    list to be encoded as a space delimited list of strings enclosed in unescaped quotes

    This method is exposed for the purpose of testing. It is applied to the
    elements of an MFString as part of the encode function. Users of this module will
    not have to call this function.

    aString : arbitrary unicode string
    return :  unicode string with \ --> \\ ; " --> \" replacements
    """
    rv=StringIO()
    for c in aString:
        if c==BACKSLASH or c==QUOTE_MARK:
            rv.write(BACKSLASH)
        rv.write(c)
    return rv.getvalue()


def slash_decode( xString ):
    """Reverses the slash_encoding

    This method is exposed for the purpose of testing. It is applied to the
    elements of an MFString as part of the decode function. Users of this module will
    not have to call this function.

    Note added 7 Feb 2025:  Exposing this function is also useful for decoding classic VRML files

    xString : a unicode string that is the result of an application of the slash_encode algorithm

    returns : The string that would be encoded to xString
    """
    logger.debug("slash_decode: %r" % (xString,))
    rv=StringIO()
    escaping = False
    for c in xString:
        if escaping:
            if c==BACKSLASH or c==QUOTE_MARK:
                rv.write(c)
            else:
                raise SlashEncodingError(xString)
            escaping = False
        else: # not escaping
            if c==BACKSLASH:
                escaping = True
            else:
                rv.write(c)
    if escaping:
        raise SlashEncodingError(xString)
    return rv.getvalue()



def encode( aList):
    """Encode a list of unicode strings to a single unicode string

    input argument: a sequence of unicode strings
    returns: a unicode string
    """
    slash_encoded_items = [slash_encode(s) for s in aList ]
    quoted_items = ['"%s"' % item for item in slash_encoded_items]
    return SPACE.join(quoted_items)



def decode( mfstring_enc ):
    """Decode unicode string into a list of unicode strings


    This method is to be applied to the normalized attribute value, the
    result of appluing the algorithm specified in the section 3.3.3 of the
    XML reference document
    https://www.w3.org/TR/2008/REC-xml-20081126/#AVNormalize

    mfstring_enc : A unicode string, the result of the application of the encode function
    returns : Python list of unicode strings
    """


    retVal = []
    looking_for_delim = True
    escaping = False
    ix_start = -1
    for ix,c in enumerate(mfstring_enc):
        if looking_for_delim:
            if c==QUOTE_MARK:
                looking_for_delim = False
                escaping = False
                ix_start=ix+1
            elif c not in ITEM_SEPARATORS:
                msg="unexpected character %r between MFString items" % c
                if _ONLY_WARN_ON_ERRORS_:
                    logger.warning( msg )
                else:
                    raise ListEncodingError( msg )
        else:
            if c==QUOTE_MARK and not escaping:
                try:
                    retVal.append(slash_decode(mfstring_enc[ix_start:ix]))
                except (SlashEncodingError,) as exc:
                    if _ONLY_WARN_ON_ERRORS_:
                        logger.warning( str(exc) )
                        retVal.append(mfstring_enc[ix_start:ix])
                    else:
                        raise
                looking_for_delim = True
            escaping = (c == BACKSLASH) and not escaping
    if not looking_for_delim:
        msg = "encoded MFString not terminated by unescaped quote"
        if _ONLY_WARN_ON_ERRORS_:
            logger.warning( msg )
        else:
            raise ListEncodingError( msg )
    return retVal
