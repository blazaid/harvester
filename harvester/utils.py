import re
from urllib.parse import urlsplit, quote, quote_plus, urlunsplit


def force_decode(bytes_array, codecs_to_try_first=None):
    """ Forces the decoding of the supplied bytes array.

    :param bytes_array: The bytes to decode
    :param codecs_to_try_first: A codec or list of codecs to try before the default codecs. It's and optional parameter.
    :return: The string decoded.
    :raises UnicodeDecodeError: If the bytes array couldn't be decoded with user supplied and default codecs.
    """
    if codecs_to_try_first is None:
        codecs_to_try_first = []
    elif isinstance(codecs_to_try_first, str):
        codecs_to_try_first = [codecs_to_try_first]

    for codec in codecs_to_try_first:
        try:
            return bytes_array.decode(codec)
        except UnicodeDecodeError:
            pass

    default_codecs = ['utf8', 'cp1252', 'iso8859', ]
    for codec in default_codecs:
        try:
            return bytes_array.decode(codec)
        except UnicodeDecodeError:
            pass
    raise ValueError()


def is_url(value):
    """ Checks if the given value is an url or not.

    :param value: The possible url.
    :return: True if the parameter is an url, False otherwise.
    """
    return re.match(r'^(?:http|ftp)s?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
                    r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', value, re.IGNORECASE) is not None


def fix_url(url):
    """ Fixes the url so it can be requested by urllib (i.e. spaces, odd characters, ...).

    :param url: The url to be fixed.
    :return: The url fixed.
    """
    scheme, netloc, path, qs, anchor = urlsplit(url)
    path = quote(path, '/%')
    qs = quote_plus(qs, ':&=')
    return urlunsplit((scheme, netloc, path, qs, anchor))
