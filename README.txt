humanize/bin/                                                                                       000755  000765  000000  00000000000 12674546615 014443  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/._humanize                                                                             000755  000765  000024  00000000261 12674546615 016432  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/                                                                              000755  000765  000000  00000000000 12674546615 016263  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize.py                                                                            000644  000765  000000  00000004413 12674543346 016635  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         #!/usr/bin/env python

import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators, Set
import humanize
import datetime


@Configuration()
class HumanizeCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    humanize_commands = Set("intcomma",
        "intword",
        "apnumber",
        "naturalday",
        "naturaldate",
        "naturaldelta",
        "naturaltime",
        "naturalsize",
        "fractional",
        )

    command = Option(
        doc='''
        **Syntax:** **command=***<command>*
        **Description:** Name of the Humanize command that will run''',
        require=True, validate=humanize_commands)

    out = Option(
        doc='''
        **Syntax:** **command=***<command>*
        **Description:** Name of the output field''',
        require=False, validate=validators.Fieldname())

    def processDate(self, event, field):
        try:
            timestamp = float(event[field])
            value = repr(datetime.date.fromtimestamp(timestamp))
            return eval("humanize." + self.command + "(" + value + ")")
        except ValueError:
            pass

    def processTime(self, event, field):
        try:
            timestamp = float(event[field])
            value = repr(datetime.datetime.fromtimestamp(timestamp))
            return eval("humanize." + self.command + "(" + value + ")")
        except ValueError:
            pass

    def stream(self, events):
        self.logger.debug('HumanizeCommand: {}\n {}'.format(self, self.command))  # logs command line
        for event in events:
            for field in self.fieldnames:
                if self.command in ['naturalday', 'naturaldate'] and field in event and len(event[field]) > 0:
                    event[field] = self.processDate(event, field)
                elif self.command == 'naturaltime' and field in event and len(event[field]) > 0:
                    event[field] = self.processTime(event, field)
                elif field in event and len(event[field]) > 0:
                    event[field] = eval("humanize." + self.command + "(" + event[field] + ")")
            yield event


dispatch(HumanizeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
                                                                                                                                                                                                                                                     humanize/bin/splunklib/                                                                             000755  000765  000000  00000000000 12674546615 016446  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/splunklib/__init__.py                                                                  000644  000765  000000  00000001271 12674041006 020540  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python library for Splunk."""

__version_info__ = (1, 5, 0)
__version__ = ".".join(map(str, __version_info__))

                                                                                                                                                                                                                                                                                                                                       humanize/bin/splunklib/binding.py                                                                   000644  000765  000000  00000152406 12674041006 020422  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""The **splunklib.binding** module provides a low-level binding interface to the
`Splunk REST API <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTcontents>`_.

This module handles the wire details of calling the REST API, such as
authentication tokens, prefix paths, URL encoding, and so on. Actual path
segments, ``GET`` and ``POST`` arguments, and the parsing of responses is left
to the user.

If you want a friendlier interface to the Splunk REST API, use the
:mod:`splunklib.client` module.
"""

import httplib
import logging
import socket
import ssl
import urllib
import io
import sys
import Cookie

from datetime import datetime
from functools import wraps
from StringIO import StringIO

from contextlib import contextmanager

from xml.etree.ElementTree import XML
try:
    from xml.etree.ElementTree import ParseError
except ImportError, e:
    from xml.parsers.expat import ExpatError as ParseError

from data import record

__all__ = [
    "AuthenticationError",
    "connect",
    "Context",
    "handler",
    "HTTPError"
]

# If you change these, update the docstring
# on _authority as well.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = "8089"
DEFAULT_SCHEME = "https"

def _log_duration(f):
    @wraps(f)
    def new_f(*args, **kwargs):
        start_time = datetime.now()
        val = f(*args, **kwargs)
        end_time = datetime.now()
        logging.debug("Operation took %s", end_time-start_time)
        return val
    return new_f


def _parse_cookies(cookie_str, dictionary):
    """Tries to parse any key-value pairs of cookies in a string,
    then updates the the dictionary with any key-value pairs found.

    **Example**::
        dictionary = {}
        _parse_cookies('my=value', dictionary)
        # Now the following is True
        dictionary['my'] == 'value'

    :param cookie_str: A string containing "key=value" pairs from an HTTP "Set-Cookie" header.
    :type cookie_str: ``str``
    :param dictionary: A dictionary to update with any found key-value pairs.
    :type dictionary: ``dict``
    """
    parsed_cookie = Cookie.SimpleCookie(cookie_str)
    for cookie in parsed_cookie.values():
        dictionary[cookie.key] = cookie.coded_value


def _make_cookie_header(cookies):
    """
    Takes a list of 2-tuples of key-value pairs of
    cookies, and returns a valid HTTP ``Cookie``
    header.

    **Example**::

        header = _make_cookie_header([("key", "value"), ("key_2", "value_2")])
        # Now the following is True
        header == "key=value; key_2=value_2"

    :param cookies: A list of 2-tuples of cookie key-value pairs.
    :type cookies: ``list`` of 2-tuples
    :return: ``str` An HTTP header cookie string.
    :rtype: ``str``
    """
    return "; ".join("%s=%s" % (key, value) for key, value in cookies)

# Singleton values to eschew None
class _NoAuthenticationToken(object):
    """The value stored in a :class:`Context` or :class:`splunklib.client.Service`
    class that is not logged in.

    If a ``Context`` or ``Service`` object is created without an authentication
    token, and there has not yet been a call to the ``login`` method, the token
    field of the ``Context`` or ``Service`` object is set to
    ``_NoAuthenticationToken``.

    Likewise, after a ``Context`` or ``Service`` object has been logged out, the
    token is set to this value again.
    """
    pass


class UrlEncoded(str):
    """This class marks URL-encoded strings.
    It should be considered an SDK-private implementation detail.

    Manually tracking whether strings are URL encoded can be difficult. Avoid
    calling ``urllib.quote`` to replace special characters with escapes. When
    you receive a URL-encoded string, *do* use ``urllib.unquote`` to replace
    escapes with single characters. Then, wrap any string you want to use as a
    URL in ``UrlEncoded``. Note that because the ``UrlEncoded`` class is
    idempotent, making multiple calls to it is OK.

    ``UrlEncoded`` objects are identical to ``str`` objects (including being
    equal if their contents are equal) except when passed to ``UrlEncoded``
    again.

    ``UrlEncoded`` removes the ``str`` type support for interpolating values
    with ``%`` (doing that raises a ``TypeError``). There is no reliable way to
    encode values this way, so instead, interpolate into a string, quoting by
    hand, and call ``UrlEncode`` with ``skip_encode=True``.

    **Example**::

        import urllib
        UrlEncoded('%s://%s' % (scheme, urllib.quote(host)), skip_encode=True)

    If you append ``str`` strings and ``UrlEncoded`` strings, the result is also
    URL encoded.

    **Example**::

        UrlEncoded('ab c') + 'de f' == UrlEncoded('ab cde f')
        'ab c' + UrlEncoded('de f') == UrlEncoded('ab cde f')
    """
    def __new__(self, val='', skip_encode=False, encode_slash=False):
        if isinstance(val, UrlEncoded):
            # Don't urllib.quote something already URL encoded.
            return val
        elif skip_encode:
            return str.__new__(self, val)
        elif encode_slash:
            return str.__new__(self, urllib.quote_plus(val))
        else:
            # When subclassing str, just call str's __new__ method
            # with your class and the value you want to have in the
            # new string.
            return str.__new__(self, urllib.quote(val))

    def __add__(self, other):
        """self + other

        If *other* is not a ``UrlEncoded``, URL encode it before
        adding it.
        """
        if isinstance(other, UrlEncoded):
            return UrlEncoded(str.__add__(self, other), skip_encode=True)
        else:
            return UrlEncoded(str.__add__(self, urllib.quote(other)), skip_encode=True)

    def __radd__(self, other):
        """other + self

        If *other* is not a ``UrlEncoded``, URL _encode it before
        adding it.
        """
        if isinstance(other, UrlEncoded):
            return UrlEncoded(str.__radd__(self, other), skip_encode=True)
        else:
            return UrlEncoded(str.__add__(urllib.quote(other), self), skip_encode=True)

    def __mod__(self, fields):
        """Interpolation into ``UrlEncoded``s is disabled.

        If you try to write ``UrlEncoded("%s") % "abc", will get a
        ``TypeError``.
        """
        raise TypeError("Cannot interpolate into a UrlEncoded object.")
    def __repr__(self):
        return "UrlEncoded(%s)" % repr(urllib.unquote(str(self)))

@contextmanager
def _handle_auth_error(msg):
    """Handle reraising HTTP authentication errors as something clearer.

    If an ``HTTPError`` is raised with status 401 (access denied) in
    the body of this context manager, reraise it as an
    ``AuthenticationError`` instead, with *msg* as its message.

    This function adds no round trips to the server.

    :param msg: The message to be raised in ``AuthenticationError``.
    :type msg: ``str``

    **Example**::

        with _handle_auth_error("Your login failed."):
             ... # make an HTTP request
    """
    try:
        yield
    except HTTPError as he:
        if he.status == 401:
            raise AuthenticationError(msg, he)
        else:
            raise

def _authentication(request_fun):
    """Decorator to handle autologin and authentication errors.

    *request_fun* is a function taking no arguments that needs to
    be run with this ``Context`` logged into Splunk.

    ``_authentication``'s behavior depends on whether the
    ``autologin`` field of ``Context`` is set to ``True`` or
    ``False``. If it's ``False``, then ``_authentication``
    aborts if the ``Context`` is not logged in, and raises an
    ``AuthenticationError`` if an ``HTTPError`` of status 401 is
    raised in *request_fun*. If it's ``True``, then
    ``_authentication`` will try at all sensible places to
    log in before issuing the request.

    If ``autologin`` is ``False``, ``_authentication`` makes
    one roundtrip to the server if the ``Context`` is logged in,
    or zero if it is not. If ``autologin`` is ``True``, it's less
    deterministic, and may make at most three roundtrips (though
    that would be a truly pathological case).

    :param request_fun: A function of no arguments encapsulating
                        the request to make to the server.

    **Example**::

        import splunklib.binding as binding
        c = binding.connect(..., autologin=True)
        c.logout()
        def f():
            c.get("/services")
            return 42
        print _authentication(f)
    """
    @wraps(request_fun)
    def wrapper(self, *args, **kwargs):
        if self.token is _NoAuthenticationToken and \
                not self.has_cookies():
            # Not yet logged in.
            if self.autologin and self.username and self.password:
                # This will throw an uncaught
                # AuthenticationError if it fails.
                self.login()
            else:
                # Try the request anyway without authentication.
                # Most requests will fail. Some will succeed, such as
                # 'GET server/info'.
                with _handle_auth_error("Request aborted: not logged in."):
                    return request_fun(self, *args, **kwargs)
        try:
            # Issue the request
            return request_fun(self, *args, **kwargs)
        except HTTPError as he:
            if he.status == 401 and self.autologin:
                # Authentication failed. Try logging in, and then
                # rerunning the request. If either step fails, throw
                # an AuthenticationError and give up.
                with _handle_auth_error("Autologin failed."):
                    self.login()
                with _handle_auth_error(
                        "Autologin succeeded, but there was an auth error on "
                        "next request. Something is very wrong."):
                    return request_fun(self, *args, **kwargs)
            elif he.status == 401 and not self.autologin:
                raise AuthenticationError(
                    "Request failed: Session is not logged in.", he)
            else:
                raise

    return wrapper


def _authority(scheme=DEFAULT_SCHEME, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Construct a URL authority from the given *scheme*, *host*, and *port*.

    Named in accordance with RFC2396_, which defines URLs as::

        <scheme>://<authority><path>?<query>

    .. _RFC2396: http://www.ietf.org/rfc/rfc2396.txt

    So ``https://localhost:8000/a/b/b?boris=hilda`` would be parsed as::

        scheme := https
        authority := localhost:8000
        path := /a/b/c
        query := boris=hilda

    :param scheme: URL scheme (the default is "https")
    :type scheme: "http" or "https"
    :param host: The host name (the default is "localhost")
    :type host: string
    :param port: The port number (the default is 8089)
    :type port: integer
    :return: The URL authority.
    :rtype: UrlEncoded (subclass of ``str``)

    **Example**::

        _authority() == "https://localhost:8089"

        _authority(host="splunk.utopia.net") == "https://splunk.utopia.net:8089"

        _authority(host="2001:0db8:85a3:0000:0000:8a2e:0370:7334") == \
            "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:8089"

        _authority(scheme="http", host="splunk.utopia.net", port="471") == \
            "http://splunk.utopia.net:471"

    """
    if ':' in host:
        # IPv6 addresses must be enclosed in [ ] in order to be well
        # formed.
        host = '[' + host + ']'
    return UrlEncoded("%s://%s:%s" % (scheme, host, port), skip_encode=True)

# kwargs: sharing, owner, app
def namespace(sharing=None, owner=None, app=None, **kwargs):
    """This function constructs a Splunk namespace.

    Every Splunk resource belongs to a namespace. The namespace is specified by
    the pair of values ``owner`` and ``app`` and is governed by a ``sharing`` mode.
    The possible values for ``sharing`` are: "user", "app", "global" and "system",
    which map to the following combinations of ``owner`` and ``app`` values:

        "user"   => {owner}, {app}

        "app"    => nobody, {app}

        "global" => nobody, {app}

        "system" => nobody, system

    "nobody" is a special user name that basically means no user, and "system"
    is the name reserved for system resources.

    "-" is a wildcard that can be used for both ``owner`` and ``app`` values and
    refers to all users and all apps, respectively.

    In general, when you specify a namespace you can specify any combination of
    these three values and the library will reconcile the triple, overriding the
    provided values as appropriate.

    Finally, if no namespacing is specified the library will make use of the
    ``/services`` branch of the REST API, which provides a namespaced view of
    Splunk resources equivelent to using ``owner={currentUser}`` and
    ``app={defaultApp}``.

    The ``namespace`` function returns a representation of the namespace from
    reconciling the values you provide. It ignores any keyword arguments other
    than ``owner``, ``app``, and ``sharing``, so you can provide ``dicts`` of
    configuration information without first having to extract individual keys.

    :param sharing: The sharing mode (the default is "user").
    :type sharing: "system", "global", "app", or "user"
    :param owner: The owner context (the default is "None").
    :type owner: ``string``
    :param app: The app context (the default is "None").
    :type app: ``string``
    :returns: A :class:`splunklib.data.Record` containing the reconciled
        namespace.

    **Example**::

        import splunklib.binding as binding
        n = binding.namespace(sharing="user", owner="boris", app="search")
        n = binding.namespace(sharing="global", app="search")
    """
    if sharing in ["system"]:
        return record({'sharing': sharing, 'owner': "nobody", 'app': "system" })
    if sharing in ["global", "app"]:
        return record({'sharing': sharing, 'owner': "nobody", 'app': app})
    if sharing in ["user", None]:
        return record({'sharing': sharing, 'owner': owner, 'app': app})
    raise ValueError("Invalid value for argument: 'sharing'")


class Context(object):
    """This class represents a context that encapsulates a splunkd connection.

    The ``Context`` class encapsulates the details of HTTP requests,
    authentication, a default namespace, and URL prefixes to simplify access to
    the REST API.

    After creating a ``Context`` object, you must call its :meth:`login`
    method before you can issue requests to splunkd. Or, use the :func:`connect`
    function to create an already-authenticated ``Context`` object. You can
    provide a session token explicitly (the same token can be shared by multiple
    ``Context`` objects) to provide authentication.

    :param host: The host name (the default is "localhost").
    :type host: ``string``
    :param port: The port number (the default is 8089).
    :type port: ``integer``
    :param scheme: The scheme for accessing the service (the default is "https").
    :type scheme: "https" or "http"
    :param sharing: The sharing mode for the namespace (the default is "user").
    :type sharing: "global", "system", "app", or "user"
    :param owner: The owner context of the namespace (optional, the default is "None").
    :type owner: ``string``
    :param app: The app context of the namespace (optional, the default is "None").
    :type app: ``string``
    :param token: A session token. When provided, you don't need to call :meth:`login`.
    :type token: ``string``
    :param cookie: A session cookie. When provided, you don't need to call :meth:`login`.
        This parameter is only supported for Splunk 6.2+.
    :type cookie: ``string``
    :param username: The Splunk account username, which is used to
        authenticate the Splunk instance.
    :type username: ``string``
    :param password: The password for the Splunk account.
    :type password: ``string``
    :param handler: The HTTP request handler (optional).
    :returns: A ``Context`` instance.

    **Example**::

        import splunklib.binding as binding
        c = binding.Context(username="boris", password="natasha", ...)
        c.login()
        # Or equivalently
        c = binding.connect(username="boris", password="natasha")
        # Or if you already have a session token
        c = binding.Context(token="atg232342aa34324a")
        # Or if you already have a valid cookie
        c = binding.Context(cookie="splunkd_8089=...")
    """
    def __init__(self, handler=None, **kwargs):
        self.http = HttpLib(handler)
        self.token = kwargs.get("token", _NoAuthenticationToken)
        if self.token is None: # In case someone explicitly passes token=None
            self.token = _NoAuthenticationToken
        self.scheme = kwargs.get("scheme", DEFAULT_SCHEME)
        self.host = kwargs.get("host", DEFAULT_HOST)
        self.port = int(kwargs.get("port", DEFAULT_PORT))
        self.authority = _authority(self.scheme, self.host, self.port)
        self.namespace = namespace(**kwargs)
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
        self.autologin = kwargs.get("autologin", False)

        # Store any cookies in the self.http._cookies dict
        if kwargs.has_key("cookie") and kwargs['cookie'] not in [None, _NoAuthenticationToken]:
            _parse_cookies(kwargs["cookie"], self.http._cookies)

    def get_cookies(self):
        """Gets the dictionary of cookies from the ``HttpLib`` member of this instance.

        :return: Dictionary of cookies stored on the ``self.http``.
        :rtype: ``dict``
        """
        return self.http._cookies

    def has_cookies(self):
        """Returns true if the ``HttpLib`` member of this instance has at least
        one cookie stored.

        :return: ``True`` if there is at least one cookie, else ``False``
        :rtype: ``bool``
        """
        return len(self.get_cookies()) > 0

    # Shared per-context request headers
    @property
    def _auth_headers(self):
        """Headers required to authenticate a request.

        Assumes your ``Context`` already has a authentication token or
        cookie, either provided explicitly or obtained by logging
        into the Splunk instance.

        :returns: A list of 2-tuples containing key and value
        """
        if self.has_cookies():
            return [("Cookie", _make_cookie_header(self.get_cookies().items()))]
        elif self.token is _NoAuthenticationToken:
            return []
        else:
            # Ensure the token is properly formatted
            if self.token.startswith('Splunk '):
                token = self.token
            else:
                token = 'Splunk %s' % self.token
            return [("Authorization", token)]

    def connect(self):
        """Returns an open connection (socket) to the Splunk instance.

        This method is used for writing bulk events to an index or similar tasks
        where the overhead of opening a connection multiple times would be
        prohibitive.

        :returns: A socket.

        **Example**::

            import splunklib.binding as binding
            c = binding.connect(...)
            socket = c.connect()
            socket.write("POST %s HTTP/1.1\\r\\n" % "some/path/to/post/to")
            socket.write("Host: %s:%s\\r\\n" % (c.host, c.port))
            socket.write("Accept-Encoding: identity\\r\\n")
            socket.write("Authorization: %s\\r\\n" % c.token)
            socket.write("X-Splunk-Input-Mode: Streaming\\r\\n")
            socket.write("\\r\\n")
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.scheme == "https":
            sock = ssl.wrap_socket(sock)
        sock.connect((socket.gethostbyname(self.host), self.port))
        return sock

    @_authentication
    @_log_duration
    def delete(self, path_segment, owner=None, app=None, sharing=None, **query):
        """Performs a DELETE operation at the REST path segment with the given
        namespace and query.

        This method is named to match the HTTP method. ``delete`` makes at least
        one round trip to the server, one additional round trip for each 303
        status returned, and at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        If *owner*, *app*, and *sharing* are omitted, this method uses the
        default :class:`Context` namespace. All other keyword arguments are
        included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Context`` object is not
             logged in.
        :raises HTTPError: Raised when an error occurred in a GET operation from
             *path_segment*.
        :param path_segment: A REST path segment.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode of the namespace (optional).
        :type sharing: ``string``
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            c = binding.connect(...)
            c.delete('saved/searches/boris') == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '1786'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 16:53:06 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'OK',
                 'status': 200}
            c.delete('nonexistant/path') # raises HTTPError
            c.logout()
            c.delete('apps/local') # raises AuthenticationError
        """
        path = self.authority + self._abspath(path_segment, owner=owner,
                                              app=app, sharing=sharing)
        logging.debug("DELETE request to %s (body: %s)", path, repr(query))
        response = self.http.delete(path, self._auth_headers, **query)
        return response

    @_authentication
    @_log_duration
    def get(self, path_segment, owner=None, app=None, sharing=None, **query):
        """Performs a GET operation from the REST path segment with the given
        namespace and query.

        This method is named to match the HTTP method. ``get`` makes at least
        one round trip to the server, one additional round trip for each 303
        status returned, and at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        If *owner*, *app*, and *sharing* are omitted, this method uses the
        default :class:`Context` namespace. All other keyword arguments are
        included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Context`` object is not
             logged in.
        :raises HTTPError: Raised when an error occurred in a GET operation from
             *path_segment*.
        :param path_segment: A REST path segment.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode of the namespace (optional).
        :type sharing: ``string``
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            c = binding.connect(...)
            c.get('apps/local') == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '26208'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 16:30:35 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'OK',
                 'status': 200}
            c.get('nonexistant/path') # raises HTTPError
            c.logout()
            c.get('apps/local') # raises AuthenticationError
        """
        path = self.authority + self._abspath(path_segment, owner=owner,
                                              app=app, sharing=sharing)
        logging.debug("GET request to %s (body: %s)", path, repr(query))
        response = self.http.get(path, self._auth_headers, **query)
        return response

    @_authentication
    @_log_duration
    def post(self, path_segment, owner=None, app=None, sharing=None, headers=None, **query):
        """Performs a POST operation from the REST path segment with the given
        namespace and query.

        This method is named to match the HTTP method. ``post`` makes at least
        one round trip to the server, one additional round trip for each 303
        status returned, and at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        If *owner*, *app*, and *sharing* are omitted, this method uses the
        default :class:`Context` namespace. All other keyword arguments are
        included in the URL as query parameters.

        Some of Splunk's endpoints, such as ``receivers/simple`` and
        ``receivers/stream``, require unstructured data in the POST body
        and all metadata passed as GET-style arguments. If you provide
        a ``body`` argument to ``post``, it will be used as the POST
        body, and all other keyword arguments will be passed as
        GET-style arguments in the URL.

        :raises AuthenticationError: Raised when the ``Context`` object is not
             logged in.
        :raises HTTPError: Raised when an error occurred in a GET operation from
             *path_segment*.
        :param path_segment: A REST path segment.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode of the namespace (optional).
        :type sharing: ``string``
        :param headers: List of extra HTTP headers to send (optional).
        :type headers: ``list`` of 2-tuples.
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            c = binding.connect(...)
            c.post('saved/searches', name='boris',
                   search='search * earliest=-1m | head 1') == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '10455'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 16:46:06 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'Created',
                 'status': 201}
            c.post('nonexistant/path') # raises HTTPError
            c.logout()
            # raises AuthenticationError:
            c.post('saved/searches', name='boris',
                   search='search * earliest=-1m | head 1')
        """
        if headers is None:
            headers = []

        path = self.authority + self._abspath(path_segment, owner=owner, app=app, sharing=sharing)
        logging.debug("POST request to %s (body: %s)", path, repr(query))
        all_headers = headers + self._auth_headers
        response = self.http.post(path, all_headers, **query)
        return response

    @_authentication
    @_log_duration
    def request(self, path_segment, method="GET", headers=None, body="",
                owner=None, app=None, sharing=None):
        """Issues an arbitrary HTTP request to the REST path segment.

        This method is named to match ``httplib.request``. This function
        makes a single round trip to the server.

        If *owner*, *app*, and *sharing* are omitted, this method uses the
        default :class:`Context` namespace. All other keyword arguments are
        included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Context`` object is not
             logged in.
        :raises HTTPError: Raised when an error occurred in a GET operation from
             *path_segment*.
        :param path_segment: A REST path segment.
        :type path_segment: ``string``
        :param method: The HTTP method to use (optional).
        :type method: ``string``
        :param headers: List of extra HTTP headers to send (optional).
        :type headers: ``list`` of 2-tuples.
        :param body: Content of the HTTP request (optional).
        :type body: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode of the namespace (optional).
        :type sharing: ``string``
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            c = binding.connect(...)
            c.request('saved/searches', method='GET') == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '46722'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 17:24:19 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'OK',
                 'status': 200}
            c.request('nonexistant/path', method='GET') # raises HTTPError
            c.logout()
            c.get('apps/local') # raises AuthenticationError
        """
        if headers is None:
            headers = []

        path = self.authority \
            + self._abspath(path_segment, owner=owner,
                            app=app, sharing=sharing)
        all_headers = headers + self._auth_headers
        logging.debug("%s request to %s (headers: %s, body: %s)",
                      method, path, str(all_headers), repr(body))
        response = self.http.request(path,
                                     {'method': method,
                                     'headers': all_headers,
                                     'body': body})
        return response

    def login(self):
        """Logs into the Splunk instance referred to by the :class:`Context`
        object.

        Unless a ``Context`` is created with an explicit authentication token
        (probably obtained by logging in from a different ``Context`` object)
        you must call :meth:`login` before you can issue requests.
        The authentication token obtained from the server is stored in the
        ``token`` field of the ``Context`` object.

        :raises AuthenticationError: Raised when login fails.
        :returns: The ``Context`` object, so you can chain calls.

        **Example**::

            import splunklib.binding as binding
            c = binding.Context(...).login()
            # Then issue requests...
        """

        if self.has_cookies() and \
                (not self.username and not self.password):
            # If we were passed session cookie(s), but no username or
            # password, then login is a nop, since we're automatically
            # logged in.
            return

        if self.token is not _NoAuthenticationToken and \
                (not self.username and not self.password):
            # If we were passed a session token, but no username or
            # password, then login is a nop, since we're automatically
            # logged in.
            return

        # Only try to get a token and updated cookie if username & password are specified
        try:
            response = self.http.post(
                self.authority + self._abspath("/services/auth/login"),
                username=self.username,
                password=self.password,
                cookie="1") # In Splunk 6.2+, passing "cookie=1" will return the "set-cookie" header

            body = response.body.read()
            session = XML(body).findtext("./sessionKey")
            self.token = "Splunk %s" % session
            return self
        except HTTPError as he:
            if he.status == 401:
                raise AuthenticationError("Login failed.", he)
            else:
                raise

    def logout(self):
        """Forgets the current session token, and cookies."""
        self.token = _NoAuthenticationToken
        self.http._cookies = {}
        return self

    def _abspath(self, path_segment,
                owner=None, app=None, sharing=None):
        """Qualifies *path_segment* into an absolute path for a URL.

        If *path_segment* is already absolute, returns it unchanged.
        If *path_segment* is relative, then qualifies it with either
        the provided namespace arguments or the ``Context``'s default
        namespace. Any forbidden characters in *path_segment* are URL
        encoded. This function has no network activity.

        Named to be consistent with RFC2396_.

        .. _RFC2396: http://www.ietf.org/rfc/rfc2396.txt

        :param path_segment: A relative or absolute URL path segment.
        :type path_segment: ``string``
        :param owner, app, sharing: Components of a namespace (defaults
                                    to the ``Context``'s namespace if all
                                    three are omitted)
        :type owner, app, sharing: ``string``
        :return: A ``UrlEncoded`` (a subclass of ``str``).
        :rtype: ``string``

        **Example**::

            import splunklib.binding as binding
            c = binding.connect(owner='boris', app='search', sharing='user')
            c._abspath('/a/b/c') == '/a/b/c'
            c._abspath('/a/b c/d') == '/a/b%20c/d'
            c._abspath('apps/local/search') == \
                '/servicesNS/boris/search/apps/local/search'
            c._abspath('apps/local/search', sharing='system') == \
                '/servicesNS/nobody/system/apps/local/search'
            url = c.authority + c._abspath('apps/local/sharing')
        """
        skip_encode = isinstance(path_segment, UrlEncoded)
        # If path_segment is absolute, escape all forbidden characters
        # in it and return it.
        if path_segment.startswith('/'):
            return UrlEncoded(path_segment, skip_encode=skip_encode)

        # path_segment is relative, so we need a namespace to build an
        # absolute path.
        if owner or app or sharing:
            ns = namespace(owner=owner, app=app, sharing=sharing)
        else:
            ns = self.namespace

        # If no app or owner are specified, then use the /services
        # endpoint. Otherwise, use /servicesNS with the specified
        # namespace. If only one of app and owner is specified, use
        # '-' for the other.
        if ns.app is None and ns.owner is None:
            return UrlEncoded("/services/%s" % path_segment, skip_encode=skip_encode)

        oname = "nobody" if ns.owner is None else ns.owner
        aname = "system" if ns.app is None else ns.app
        path = UrlEncoded("/servicesNS/%s/%s/%s" % (oname, aname, path_segment),
                          skip_encode=skip_encode)
        return path


def connect(**kwargs):
    """This function returns an authenticated :class:`Context` object.

    This function is a shorthand for calling :meth:`Context.login`.

    This function makes one round trip to the server.

    :param host: The host name (the default is "localhost").
    :type host: ``string``
    :param port: The port number (the default is 8089).
    :type port: ``integer``
    :param scheme: The scheme for accessing the service (the default is "https").
    :type scheme: "https" or "http"
    :param owner: The owner context of the namespace (the default is "None").
    :type owner: ``string``
    :param app: The app context of the namespace (the default is "None").
    :type app: ``string``
    :param sharing: The sharing mode for the namespace (the default is "user").
    :type sharing: "global", "system", "app", or "user"
    :param token: The current session token (optional). Session tokens can be
        shared across multiple service instances.
    :type token: ``string``
    :param cookie: A session cookie. When provided, you don't need to call :meth:`login`.
        This parameter is only supported for Splunk 6.2+.
    :type cookie: ``string``
    :param username: The Splunk account username, which is used to
        authenticate the Splunk instance.
    :type username: ``string``
    :param password: The password for the Splunk account.
    :type password: ``string``
    :param autologin: When ``True``, automatically tries to log in again if the
        session terminates.
    :type autologin: ``Boolean``
    :return: An initialized :class:`Context` instance.

    **Example**::

        import splunklib.binding as binding
        c = binding.connect(...)
        response = c.get("apps/local")
    """
    c = Context(**kwargs)
    c.login()
    return c

# Note: the error response schema supports multiple messages but we only
# return the first, although we do return the body so that an exception
# handler that wants to read multiple messages can do so.
class HTTPError(Exception):
    """This exception is raised for HTTP responses that return an error."""
    def __init__(self, response, _message=None):
        status = response.status
        reason = response.reason
        body = response.body.read()
        try:
            detail = XML(body).findtext("./messages/msg")
        except ParseError as err:
            detail = body
        message = "HTTP %d %s%s" % (
            status, reason, "" if detail is None else " -- %s" % detail)
        Exception.__init__(self, _message or message)
        self.status = status
        self.reason = reason
        self.headers = response.headers
        self.body = body
        self._response = response

class AuthenticationError(HTTPError):
    """Raised when a login request to Splunk fails.

    If your username was unknown or you provided an incorrect password
    in a call to :meth:`Context.login` or :meth:`splunklib.client.Service.login`,
    this exception is raised.
    """
    def __init__(self, message, cause):
        # Put the body back in the response so that HTTPError's constructor can
        # read it again.
        cause._response.body = StringIO(cause.body)

        HTTPError.__init__(self, cause._response, message)

#
# The HTTP interface used by the Splunk binding layer abstracts the underlying
# HTTP library using request & response 'messages' which are implemented as
# dictionaries with the following structure:
#
#   # HTTP request message (only method required)
#   request {
#       method : str,
#       headers? : [(str, str)*],
#       body? : str,
#   }
#
#   # HTTP response message (all keys present)
#   response {
#       status : int,
#       reason : str,
#       headers : [(str, str)*],
#       body : file,
#   }
#

# Encode the given kwargs as a query string. This wrapper will also _encode
# a list value as a sequence of assignemnts to the corresponding arg name,
# for example an argument such as 'foo=[1,2,3]' will be encoded as
# 'foo=1&foo=2&foo=3'.
def _encode(**kwargs):
    items = []
    for key, value in kwargs.iteritems():
        if isinstance(value, list):
            items.extend([(key, item) for item in value])
        else:
            items.append((key, value))
    return urllib.urlencode(items)

# Crack the given url into (scheme, host, port, path)
def _spliturl(url):
    scheme, opaque = urllib.splittype(url)
    netloc, path = urllib.splithost(opaque)
    host, port = urllib.splitport(netloc)
    # Strip brackets if its an IPv6 address
    if host.startswith('[') and host.endswith(']'): host = host[1:-1]
    if port is None: port = DEFAULT_PORT
    return scheme, host, port, path

# Given an HTTP request handler, this wrapper objects provides a related
# family of convenience methods built using that handler.
class HttpLib(object):
    """A set of convenient methods for making HTTP calls.

    ``HttpLib`` provides a general :meth:`request` method, and :meth:`delete`,
    :meth:`post`, and :meth:`get` methods for the three HTTP methods that Splunk
    uses.

    By default, ``HttpLib`` uses Python's built-in ``httplib`` library,
    but you can replace it by passing your own handling function to the
    constructor for ``HttpLib``.

    The handling function should have the type:

        ``handler(`url`, `request_dict`) -> response_dict``

    where `url` is the URL to make the request to (including any query and
    fragment sections) as a dictionary with the following keys:

        - method: The method for the request, typically ``GET``, ``POST``, or ``DELETE``.

        - headers: A list of pairs specifying the HTTP headers (for example: ``[('key': value), ...]``).

        - body: A string containing the body to send with the request (this string
          should default to '').

    and ``response_dict`` is a dictionary with the following keys:

        - status: An integer containing the HTTP status code (such as 200 or 404).

        - reason: The reason phrase, if any, returned by the server.

        - headers: A list of pairs containing the response headers (for example, ``[('key': value), ...]``).

        - body: A stream-like object supporting ``read(size=None)`` and ``close()``
          methods to get the body of the response.

    The response dictionary is returned directly by ``HttpLib``'s methods with
    no further processing. By default, ``HttpLib`` calls the :func:`handler` function
    to get a handler function.
    """
    def __init__(self, custom_handler=None):
        self.handler = handler() if custom_handler is None else custom_handler
        self._cookies = {}

    def delete(self, url, headers=None, **kwargs):
        """Sends a DELETE request to a URL.

        :param url: The URL.
        :type url: ``string``
        :param headers: A list of pairs specifying the headers for the HTTP
            response (for example, ``[('Content-Type': 'text/cthulhu'), ('Token': 'boris')]``).
        :type headers: ``list``
        :param kwargs: Additional keyword arguments (optional). These arguments
            are interpreted as the query part of the URL. The order of keyword
            arguments is not preserved in the request, but the keywords and
            their arguments will be URL encoded.
        :type kwargs: ``dict``
        :returns: A dictionary describing the response (see :class:`HttpLib` for
            its structure).
        :rtype: ``dict``
        """
        if headers is None: headers = []
        if kwargs:
            # url is already a UrlEncoded. We have to manually declare
            # the query to be encoded or it will get automatically URL
            # encoded by being appended to url.
            url = url + UrlEncoded('?' + _encode(**kwargs), skip_encode=True)
        message = {
            'method': "DELETE",
            'headers': headers,
        }
        return self.request(url, message)

    def get(self, url, headers=None, **kwargs):
        """Sends a GET request to a URL.

        :param url: The URL.
        :type url: ``string``
        :param headers: A list of pairs specifying the headers for the HTTP
            response (for example, ``[('Content-Type': 'text/cthulhu'), ('Token': 'boris')]``).
        :type headers: ``list``
        :param kwargs: Additional keyword arguments (optional). These arguments
            are interpreted as the query part of the URL. The order of keyword
            arguments is not preserved in the request, but the keywords and
            their arguments will be URL encoded.
        :type kwargs: ``dict``
        :returns: A dictionary describing the response (see :class:`HttpLib` for
            its structure).
        :rtype: ``dict``
        """
        if headers is None: headers = []
        if kwargs:
            # url is already a UrlEncoded. We have to manually declare
            # the query to be encoded or it will get automatically URL
            # encoded by being appended to url.
            url = url + UrlEncoded('?' + _encode(**kwargs), skip_encode=True)
        return self.request(url, { 'method': "GET", 'headers': headers })

    def post(self, url, headers=None, **kwargs):
        """Sends a POST request to a URL.

        :param url: The URL.
        :type url: ``string``
        :param headers: A list of pairs specifying the headers for the HTTP
            response (for example, ``[('Content-Type': 'text/cthulhu'), ('Token': 'boris')]``).
        :type headers: ``list``
        :param kwargs: Additional keyword arguments (optional). If the argument
            is ``body``, the value is used as the body for the request, and the
            keywords and their arguments will be URL encoded. If there is no
            ``body`` keyword argument, all the keyword arguments are encoded
            into the body of the request in the format ``x-www-form-urlencoded``.
        :type kwargs: ``dict``
        :returns: A dictionary describing the response (see :class:`HttpLib` for
            its structure).
        :rtype: ``dict``
        """
        if headers is None: headers = []
        headers.append(("Content-Type", "application/x-www-form-urlencoded")),
        # We handle GET-style arguments and an unstructured body. This is here
        # to support the receivers/stream endpoint.
        if 'body' in kwargs:
            body = kwargs.pop('body')
            if len(kwargs) > 0:
                url = url + UrlEncoded('?' + _encode(**kwargs), skip_encode=True)
        else:
            body = _encode(**kwargs)
        message = {
            'method': "POST",
            'headers': headers,
            'body': body
        }
        return self.request(url, message)

    def request(self, url, message, **kwargs):
        """Issues an HTTP request to a URL.

        :param url: The URL.
        :type url: ``string``
        :param message: A dictionary with the format as described in
            :class:`HttpLib`.
        :type message: ``dict``
        :param kwargs: Additional keyword arguments (optional). These arguments
            are passed unchanged to the handler.
        :type kwargs: ``dict``
        :returns: A dictionary describing the response (see :class:`HttpLib` for
            its structure).
        :rtype: ``dict``
        """
        response = self.handler(url, message, **kwargs)
        response = record(response)
        if 400 <= response.status:
            raise HTTPError(response)

        # Update the cookie with any HTTP request
        # Initially, assume list of 2-tuples
        key_value_tuples = response.headers
        # If response.headers is a dict, get the key-value pairs as 2-tuples
        # this is the case when using urllib2
        if isinstance(response.headers, dict):
            key_value_tuples = response.headers.items()
        for key, value in key_value_tuples:
            if key.lower() == "set-cookie":
                _parse_cookies(value, self._cookies)

        return response


# Converts an httplib response into a file-like object.
class ResponseReader(io.RawIOBase):
    """This class provides a file-like interface for :class:`httplib` responses.

    The ``ResponseReader`` class is intended to be a layer to unify the different
    types of HTTP libraries used with this SDK. This class also provides a
    preview of the stream and a few useful predicates.
    """
    # For testing, you can use a StringIO as the argument to
    # ``ResponseReader`` instead of an ``httplib.HTTPResponse``. It
    # will work equally well.
    def __init__(self, response):
        self._response = response
        self._buffer = ''

    def __str__(self):
        return self.read()

    @property
    def empty(self):
        """Indicates whether there is any more data in the response."""
        return self.peek(1) == ""

    def peek(self, size):
        """Nondestructively retrieves a given number of characters.

        The next :meth:`read` operation behaves as though this method was never
        called.

        :param size: The number of characters to retrieve.
        :type size: ``integer``
        """
        c = self.read(size)
        self._buffer = self._buffer + c
        return c

    def close(self):
        """Closes this response."""
        self._response.close()

    def read(self, size = None):
        """Reads a given number of characters from the response.

        :param size: The number of characters to read, or "None" to read the
            entire response.
        :type size: ``integer`` or "None"

        """
        r = self._buffer
        self._buffer = ''
        if size is not None:
            size -= len(r)
        r = r + self._response.read(size)
        return r

    def readable(self):
        """ Indicates that the response reader is readable."""
        return True

    def readinto(self, byte_array):
        """ Read data into a byte array, upto the size of the byte array.

        :param byte_array: A byte array/memory view to pour bytes into.
        :type byte_array: ``bytearray`` or ``memoryview``

        """
        max_size = len(byte_array)
        data = self.read(max_size)
        bytes_read = len(data)
        byte_array[:bytes_read] = data
        return bytes_read


def handler(key_file=None, cert_file=None, timeout=None):
    """This class returns an instance of the default HTTP request handler using
    the values you provide.

    :param `key_file`: A path to a PEM (Privacy Enhanced Mail) formatted file containing your private key (optional).
    :type key_file: ``string``
    :param `cert_file`: A path to a PEM (Privacy Enhanced Mail) formatted file containing a certificate chain file (optional).
    :type cert_file: ``string``
    :param `timeout`: The request time-out period, in seconds (optional).
    :type timeout: ``integer`` or "None"
    """

    def connect(scheme, host, port):
        kwargs = {}
        if timeout is not None: kwargs['timeout'] = timeout
        if scheme == "http":
            return httplib.HTTPConnection(host, port, **kwargs)
        if scheme == "https":
            if key_file is not None: kwargs['key_file'] = key_file
            if cert_file is not None: kwargs['cert_file'] = cert_file

            # If running Python 2.7.9+, disable SSL certificate validation
            if sys.version_info >= (2,7,9) and key_file is None and cert_file is None:
                kwargs['context'] = ssl._create_unverified_context()
            return httplib.HTTPSConnection(host, port, **kwargs)
        raise ValueError("unsupported scheme: %s" % scheme)

    def request(url, message, **kwargs):
        scheme, host, port, path = _spliturl(url)
        body = message.get("body", "")
        head = {
            "Content-Length": str(len(body)),
            "Host": host,
            "User-Agent": "splunk-sdk-python/1.5.0",
            "Accept": "*/*",
        } # defaults
        for key, value in message["headers"]:
            head[key] = value
        method = message.get("method", "GET")

        connection = connect(scheme, host, port)
        try:
            connection.request(method, path, body, head)
            if timeout is not None:
                connection.sock.settimeout(timeout)
            response = connection.getresponse()
        finally:
            connection.close()

        return {
            "status": response.status,
            "reason": response.reason,
            "headers": response.getheaders(),
            "body": ResponseReader(response),
        }

    return request
                                                                                                                                                                                                                                                          humanize/bin/splunklib/client.py                                                                    000644  000765  000000  00000410144 12674041006 020262  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# The purpose of this module is to provide a friendlier domain interface to
# various Splunk endpoints. The approach here is to leverage the binding
# layer to capture endpoint context and provide objects and methods that
# offer simplified access their corresponding endpoints. The design avoids
# caching resource state. From the perspective of this module, the 'policy'
# for caching resource state belongs in the application or a higher level
# framework, and its the purpose of this module to provide simplified
# access to that resource state.
#
# A side note, the objects below that provide helper methods for updating eg:
# Entity state, are written so that they may be used in a fluent style.
#

"""The **splunklib.client** module provides a Pythonic interface to the
`Splunk REST API <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTcontents>`_,
allowing you programmatically access Splunk's resources.

**splunklib.client** wraps a Pythonic layer around the wire-level
binding of the **splunklib.binding** module. The core of the library is the
:class:`Service` class, which encapsulates a connection to the server, and
provides access to the various aspects of Splunk's functionality, which are
exposed via the REST API. Typically you connect to a running Splunk instance
with the :func:`connect` function::

    import splunklib.client as client
    service = client.connect(host='localhost', port=8089,
                       username='admin', password='...')
    assert isinstance(service, client.Service)

:class:`Service` objects have fields for the various Splunk resources (such as apps,
jobs, saved searches, inputs, and indexes). All of these fields are
:class:`Collection` objects::

    appcollection = service.apps
    my_app = appcollection.create('my_app')
    my_app = appcollection['my_app']
    appcollection.delete('my_app')

The individual elements of the collection, in this case *applications*,
are subclasses of :class:`Entity`. An ``Entity`` object has fields for its
attributes, and methods that are specific to each kind of entity. For example::

    print my_app['author']  # Or: print my_app.author
    my_app.package()  # Creates a compressed package of this application
"""

import datetime
import json
import urllib
import logging
from time import sleep
from datetime import datetime, timedelta
import socket
import contextlib

from binding import Context, HTTPError, AuthenticationError, namespace, UrlEncoded, _encode, _make_cookie_header
from data import record
import data

__all__ = [
    "connect",
    "NotSupportedError",
    "OperationError",
    "IncomparableException",
    "Service",
    "namespace"
]

PATH_APPS = "apps/local/"
PATH_CAPABILITIES = "authorization/capabilities/"
PATH_CONF = "configs/conf-%s/"
PATH_PROPERTIES = "properties/"
PATH_DEPLOYMENT_CLIENTS = "deployment/client/"
PATH_DEPLOYMENT_TENANTS = "deployment/tenants/"
PATH_DEPLOYMENT_SERVERS = "deployment/server/"
PATH_DEPLOYMENT_SERVERCLASSES = "deployment/serverclass/"
PATH_EVENT_TYPES = "saved/eventtypes/"
PATH_FIRED_ALERTS = "alerts/fired_alerts/"
PATH_INDEXES = "data/indexes/"
PATH_INPUTS = "data/inputs/"
PATH_JOBS = "search/jobs/"
PATH_LOGGER = "/services/server/logger/"
PATH_MESSAGES = "messages/"
PATH_MODULAR_INPUTS = "data/modular-inputs"
PATH_ROLES = "authorization/roles/"
PATH_SAVED_SEARCHES = "saved/searches/"
PATH_STANZA = "configs/conf-%s/%s" # (file, stanza)
PATH_USERS = "authentication/users/"
PATH_RECEIVERS_STREAM = "receivers/stream"
PATH_RECEIVERS_SIMPLE = "receivers/simple"
PATH_STORAGE_PASSWORDS = "storage/passwords"

XNAMEF_ATOM = "{http://www.w3.org/2005/Atom}%s"
XNAME_ENTRY = XNAMEF_ATOM % "entry"
XNAME_CONTENT = XNAMEF_ATOM % "content"

MATCH_ENTRY_CONTENT = "%s/%s/*" % (XNAME_ENTRY, XNAME_CONTENT)


class IllegalOperationException(Exception):
    """Thrown when an operation is not possible on the Splunk instance that a
    :class:`Service` object is connected to."""
    pass


class IncomparableException(Exception):
    """Thrown when trying to compare objects (using ``==``, ``<``, ``>``, and
    so on) of a type that doesn't support it."""
    pass


class AmbiguousReferenceException(ValueError):
    """Thrown when the name used to fetch an entity matches more than one entity."""
    pass


class InvalidNameException(Exception):
    """Thrown when the specified name contains characters that are not allowed
    in Splunk entity names."""
    pass


class NoSuchCapability(Exception):
    """Thrown when the capability that has been referred to doesn't exist."""
    pass


class OperationError(Exception):
    """Raised for a failed operation, such as a time out."""
    pass


class NotSupportedError(Exception):
    """Raised for operations that are not supported on a given object."""
    pass


def _trailing(template, *targets):
    """Substring of *template* following all *targets*.

    **Example**::

        template = "this is a test of the bunnies."
        _trailing(template, "is", "est", "the") == " bunnies"

    Each target is matched successively in the string, and the string
    remaining after the last target is returned. If one of the targets
    fails to match, a ValueError is raised.

    :param template: Template to extract a trailing string from.
    :type template: ``string``
    :param targets: Strings to successively match in *template*.
    :type targets: list of ``string``s
    :return: Trailing string after all targets are matched.
    :rtype: ``string``
    :raises ValueError: Raised when one of the targets does not match.
    """
    s = template
    for t in targets:
        n = s.find(t)
        if n == -1:
            raise ValueError("Target " + t + " not found in template.")
        s = s[n + len(t):]
    return s


# Filter the given state content record according to the given arg list.
def _filter_content(content, *args):
    if len(args) > 0:
        return record((k, content[k]) for k in args)
    return record((k, v) for k, v in content.iteritems()
        if k not in ['eai:acl', 'eai:attributes', 'type'])

# Construct a resource path from the given base path + resource name
def _path(base, name):
    if not base.endswith('/'): base = base + '/'
    return base + name


# Load an atom record from the body of the given response
def _load_atom(response, match=None):
    return data.load(response.body.read(), match)


# Load an array of atom entries from the body of the given response
def _load_atom_entries(response):
    r = _load_atom(response)
    if 'feed' in r:
        # Need this to handle a random case in the REST API
        if r.feed.get('totalResults') in [0, '0']:
            return []
        entries = r.feed.get('entry', None)
        if entries is None: return None
        return entries if isinstance(entries, list) else [entries]
    # Unlike most other endpoints, the jobs endpoint does not return
    # its state wrapped in another element, but at the top level.
    # For example, in XML, it returns <entry>...</entry> instead of
    # <feed><entry>...</entry></feed>.
    else:
        entries = r.get('entry', None)
        if entries is None: return None
        return entries if isinstance(entries, list) else [entries]


# Load the sid from the body of the given response
def _load_sid(response):
    return _load_atom(response).response.sid


# Parse the given atom entry record into a generic entity state record
def _parse_atom_entry(entry):
    title = entry.get('title', None)

    elink = entry.get('link', [])
    elink = elink if isinstance(elink, list) else [elink]
    links = record((link.rel, link.href) for link in elink)

    # Retrieve entity content values
    content = entry.get('content', {})

    # Host entry metadata
    metadata = _parse_atom_metadata(content)

    # Filter some of the noise out of the content record
    content = record((k, v) for k, v in content.iteritems()
                     if k not in ['eai:acl', 'eai:attributes'])

    if 'type' in content:
        if isinstance(content['type'], list):
            content['type'] = [t for t in content['type'] if t != 'text/xml']
            # Unset type if it was only 'text/xml'
            if len(content['type']) == 0:
                content.pop('type', None)
            # Flatten 1 element list
            if len(content['type']) == 1:
                content['type'] = content['type'][0]
        else:
            content.pop('type', None)

    return record({
        'title': title,
        'links': links,
        'access': metadata.access,
        'fields': metadata.fields,
        'content': content,
        'updated': entry.get("updated")
    })


# Parse the metadata fields out of the given atom entry content record
def _parse_atom_metadata(content):
    # Hoist access metadata
    access = content.get('eai:acl', None)

    # Hoist content metadata (and cleanup some naming)
    attributes = content.get('eai:attributes', {})
    fields = record({
        'required': attributes.get('requiredFields', []),
        'optional': attributes.get('optionalFields', []),
        'wildcard': attributes.get('wildcardFields', [])})

    return record({'access': access, 'fields': fields})

# kwargs: scheme, host, port, app, owner, username, password
def connect(**kwargs):
    """This function connects and logs in to a Splunk instance.

    This function is a shorthand for :meth:`Service.login`.
    The ``connect`` function makes one round trip to the server (for logging in).

    :param host: The host name (the default is "localhost").
    :type host: ``string``
    :param port: The port number (the default is 8089).
    :type port: ``integer``
    :param scheme: The scheme for accessing the service (the default is "https").
    :type scheme: "https" or "http"
    :param `owner`: The owner context of the namespace (optional).
    :type owner: ``string``
    :param `app`: The app context of the namespace (optional).
    :type app: ``string``
    :param sharing: The sharing mode for the namespace (the default is "user").
    :type sharing: "global", "system", "app", or "user"
    :param `token`: The current session token (optional). Session tokens can be
                    shared across multiple service instances.
    :type token: ``string``
    :param cookie: A session cookie. When provided, you don't need to call :meth:`login`.
        This parameter is only supported for Splunk 6.2+.
    :type cookie: ``string``
    :param autologin: When ``True``, automatically tries to log in again if the
        session terminates.
    :type autologin: ``boolean``
    :param `username`: The Splunk account username, which is used to
                       authenticate the Splunk instance.
    :type username: ``string``
    :param `password`: The password for the Splunk account.
    :type password: ``string``
    :return: An initialized :class:`Service` connection.

    **Example**::

        import splunklib.client as client
        s = client.connect(...)
        a = s.apps["my_app"]
        ...
    """
    s = Service(**kwargs)
    s.login()
    return s


# In preparation for adding Storm support, we added an
# intermediary class between Service and Context. Storm's
# API is not going to be the same as enterprise Splunk's
# API, so we will derive both Service (for enterprise Splunk)
# and StormService for (Splunk Storm) from _BaseService, and
# put any shared behavior on it.
class _BaseService(Context):
    pass


class Service(_BaseService):
    """A Pythonic binding to Splunk instances.

    A :class:`Service` represents a binding to a Splunk instance on an
    HTTP or HTTPS port. It handles the details of authentication, wire
    formats, and wraps the REST API endpoints into something more
    Pythonic. All of the low-level operations on the instance from
    :class:`splunklib.binding.Context` are also available in case you need
    to do something beyond what is provided by this class.

    After creating a ``Service`` object, you must call its :meth:`login`
    method before you can issue requests to Splunk.
    Alternately, use the :func:`connect` function to create an already
    authenticated :class:`Service` object, or provide a session token
    when creating the :class:`Service` object explicitly (the same
    token may be shared by multiple :class:`Service` objects).

    :param host: The host name (the default is "localhost").
    :type host: ``string``
    :param port: The port number (the default is 8089).
    :type port: ``integer``
    :param scheme: The scheme for accessing the service (the default is "https").
    :type scheme: "https" or "http"
    :param `owner`: The owner context of the namespace (optional; use "-" for wildcard).
    :type owner: ``string``
    :param `app`: The app context of the namespace (optional; use "-" for wildcard).
    :type app: ``string``
    :param `token`: The current session token (optional). Session tokens can be
                    shared across multiple service instances.
    :type token: ``string``
    :param cookie: A session cookie. When provided, you don't need to call :meth:`login`.
        This parameter is only supported for Splunk 6.2+.
    :type cookie: ``string``
    :param `username`: The Splunk account username, which is used to
                       authenticate the Splunk instance.
    :type username: ``string``
    :param `password`: The password, which is used to authenticate the Splunk
                       instance.
    :type password: ``string``
    :return: A :class:`Service` instance.

    **Example**::

        import splunklib.client as client
        s = client.Service(username="boris", password="natasha", ...)
        s.login()
        # Or equivalently
        s = client.connect(username="boris", password="natasha")
        # Or if you already have a session token
        s = client.Service(token="atg232342aa34324a")
        # Or if you already have a valid cookie
        s = client.Service(cookie="splunkd_8089=...")
    """
    def __init__(self, **kwargs):
        super(Service, self).__init__(**kwargs)
        self._splunk_version = None

    @property
    def apps(self):
        """Returns the collection of applications that are installed on this instance of Splunk.

        :return: A :class:`Collection` of :class:`Application` entities.
        """
        return Collection(self, PATH_APPS, item=Application)

    @property
    def confs(self):
        """Returns the collection of configuration files for this Splunk instance.

        :return: A :class:`Configurations` collection of
            :class:`ConfigurationFile` entities.
        """
        return Configurations(self)

    @property
    def capabilities(self):
        """Returns the list of system capabilities.

        :return: A ``list`` of capabilities.
        """
        response = self.get(PATH_CAPABILITIES)
        return _load_atom(response, MATCH_ENTRY_CONTENT).capabilities

    @property
    def event_types(self):
        """Returns the collection of event types defined in this Splunk instance.

        :return: An :class:`Entity` containing the event types.
        """
        return Collection(self, PATH_EVENT_TYPES)

    @property
    def fired_alerts(self):
        """Returns the collection of alerts that have been fired on the Splunk
        instance, grouped by saved search.

        :return: A :class:`Collection` of :class:`AlertGroup` entities.
        """
        return Collection(self, PATH_FIRED_ALERTS, item=AlertGroup)

    @property
    def indexes(self):
        """Returns the collection of indexes for this Splunk instance.

        :return: An :class:`Indexes` collection of :class:`Index` entities.
        """
        return Indexes(self, PATH_INDEXES, item=Index)

    @property
    def info(self):
        """Returns the information about this instance of Splunk.

        :return: The system information, as key-value pairs.
        :rtype: ``dict``
        """
        response = self.get("/services/server/info")
        return _filter_content(_load_atom(response, MATCH_ENTRY_CONTENT))

    @property
    def inputs(self):
        """Returns the collection of inputs configured on this Splunk instance.

        :return: An :class:`Inputs` collection of :class:`Input` entities.
        """
        return Inputs(self)

    def job(self, sid):
        """Retrieves a search job by sid.

        :return: A :class:`Job` object.
        """
        return Job(self, sid).refresh()

    @property
    def jobs(self):
        """Returns the collection of current search jobs.

        :return: A :class:`Jobs` collection of :class:`Job` entities.
        """
        return Jobs(self)

    @property
    def loggers(self):
        """Returns the collection of logging level categories and their status.

        :return: A :class:`Loggers` collection of logging levels.
        """
        return Loggers(self)

    @property
    def messages(self):
        """Returns the collection of service messages.

        :return: A :class:`Collection` of :class:`Message` entities.
        """
        return Collection(self, PATH_MESSAGES, item=Message)

    @property
    def modular_input_kinds(self):
        """Returns the collection of the modular input kinds on this Splunk instance.

        :return: A :class:`ReadOnlyCollection` of :class:`ModularInputKind` entities.
        """
        if self.splunk_version >= (5,):
            return ReadOnlyCollection(self, PATH_MODULAR_INPUTS, item=ModularInputKind)
        else:
            raise IllegalOperationException("Modular inputs are not supported before Splunk version 5.")

    @property
    def storage_passwords(self):
        """Returns the collection of the storage passwords on this Splunk instance.

        :return: A :class:`ReadOnlyCollection` of :class:`StoragePasswords` entities.
        """
        return StoragePasswords(self)

    # kwargs: enable_lookups, reload_macros, parse_only, output_mode
    def parse(self, query, **kwargs):
        """Parses a search query and returns a semantic map of the search.

        :param query: The search query to parse.
        :type query: ``string``
        :param kwargs: Arguments to pass to the ``search/parser`` endpoint
            (optional). Valid arguments are:

            * "enable_lookups" (``boolean``): If ``True``, performs reverse lookups
              to expand the search expression.

            * "output_mode" (``string``): The output format (XML or JSON).

            * "parse_only" (``boolean``): If ``True``, disables the expansion of
              search due to evaluation of subsearches, time term expansion,
              lookups, tags, eventtypes, and sourcetype alias.

            * "reload_macros" (``boolean``): If ``True``, reloads macro
              definitions from macros.conf.

        :type kwargs: ``dict``
        :return: A semantic map of the parsed search query.
        """
        return self.get("search/parser", q=query, **kwargs)

    def restart(self, timeout=None):
        """Restarts this Splunk instance.

        The service is unavailable until it has successfully restarted.

        If a *timeout* value is specified, ``restart`` blocks until the service
        resumes or the timeout period has been exceeded. Otherwise, ``restart`` returns
        immediately.

        :param timeout: A timeout period, in seconds.
        :type timeout: ``integer``
        """
        msg = { "value": "Restart requested by " + self.username + "via the Splunk SDK for Python"}
        # This message will be deleted once the server actually restarts.
        self.messages.create(name="restart_required", **msg)
        result = self.post("/services/server/control/restart")
        if timeout is None: 
            return result
        start = datetime.now()
        diff = timedelta(seconds=timeout)
        while datetime.now() - start < diff:
            try:
                self.login()
                if not self.restart_required:
                    return result
            except Exception, e:
                sleep(1)
        raise Exception, "Operation time out."

    @property
    def restart_required(self):
        """Indicates whether splunkd is in a state that requires a restart.

        :return: A ``boolean`` that indicates whether a restart is required.

        """
        response = self.get("messages").body.read()
        messages = data.load(response)['feed']
        if 'entry' not in messages:
            result = False
        else:
            if isinstance(messages['entry'], dict):
                titles = [messages['entry']['title']]
            else:
                titles = [x['title'] for x in messages['entry']]
            result = 'restart_required' in titles
        return result

    @property
    def roles(self):
        """Returns the collection of user roles.

        :return: A :class:`Roles` collection of :class:`Role` entities.
        """
        return Roles(self)

    def search(self, query, **kwargs):
        """Runs a search using a search query and any optional arguments you
        provide, and returns a `Job` object representing the search.

        :param query: A search query.
        :type query: ``string``
        :param kwargs: Arguments for the search (optional):

            * "output_mode" (``string``): Specifies the output format of the
              results.

            * "earliest_time" (``string``): Specifies the earliest time in the
              time range to
              search. The time string can be a UTC time (with fractional
              seconds), a relative time specifier (to now), or a formatted
              time string.

            * "latest_time" (``string``): Specifies the latest time in the time
              range to
              search. The time string can be a UTC time (with fractional
              seconds), a relative time specifier (to now), or a formatted
              time string.

            * "rf" (``string``): Specifies one or more fields to add to the
              search.

        :type kwargs: ``dict``
        :rtype: class:`Job`
        :returns: An object representing the created job.
        """
        return self.jobs.create(query, **kwargs)

    @property
    def saved_searches(self):
        """Returns the collection of saved searches.

        :return: A :class:`SavedSearches` collection of :class:`SavedSearch`
            entities.
        """
        return SavedSearches(self)

    @property
    def settings(self):
        """Returns the configuration settings for this instance of Splunk.

        :return: A :class:`Settings` object containing configuration settings.
        """
        return Settings(self)

    @property
    def splunk_version(self):
        """Returns the version of the splunkd instance this object is attached
        to.

        The version is returned as a tuple of the version components as
        integers (for example, `(4,3,3)` or `(5,)`).

        :return: A ``tuple`` of ``integers``.
        """
        if self._splunk_version is None:
            self._splunk_version = tuple([int(p) for p in self.info['version'].split('.')])
        return self._splunk_version

    @property
    def users(self):
        """Returns the collection of users.

        :return: A :class:`Users` collection of :class:`User` entities.
        """
        return Users(self)


class Endpoint(object):
    """This class represents individual Splunk resources in the Splunk REST API.

    An ``Endpoint`` object represents a URI, such as ``/services/saved/searches``.
    This class provides the common functionality of :class:`Collection` and
    :class:`Entity` (essentially HTTP GET and POST methods).
    """
    def __init__(self, service, path):
        self.service = service
        self.path = path if path.endswith('/') else path + '/'

    def get(self, path_segment="", owner=None, app=None, sharing=None, **query):
        """Performs a GET operation on the path segment relative to this endpoint.

        This method is named to match the HTTP method. This method makes at least
        one roundtrip to the server, one additional round trip for
        each 303 status returned, plus at most two additional round
        trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        If *owner*, *app*, and *sharing* are omitted, this method takes a
        default namespace from the :class:`Service` object for this :class:`Endpoint`.
        All other keyword arguments are included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Service`` is not logged in.
        :raises HTTPError: Raised when an error in the request occurs.
        :param path_segment: A path segment relative to this endpoint.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode for the namespace (optional).
        :type sharing: "global", "system", "app", or "user"
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            import splunklib.client
            s = client.service(...)
            apps = s.apps
            apps.get() == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '26208'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 16:30:35 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'OK',
                 'status': 200}
            apps.get('nonexistant/path') # raises HTTPError
            s.logout()
            apps.get() # raises AuthenticationError
        """
        # self.path to the Endpoint is relative in the SDK, so passing
        # owner, app, sharing, etc. along will produce the correct
        # namespace in the final request.
        if path_segment.startswith('/'):
            path = path_segment
        else:
            path = self.service._abspath(self.path + path_segment, owner=owner,
                                         app=app, sharing=sharing)
        # ^-- This was "%s%s" % (self.path, path_segment).
        # That doesn't work, because self.path may be UrlEncoded.
        return self.service.get(path,
                                owner=owner, app=app, sharing=sharing,
                                **query)

    def post(self, path_segment="", owner=None, app=None, sharing=None, **query):
        """Performs a POST operation on the path segment relative to this endpoint.

        This method is named to match the HTTP method. This method makes at least
        one roundtrip to the server, one additional round trip for
        each 303 status returned, plus at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        If *owner*, *app*, and *sharing* are omitted, this method takes a
        default namespace from the :class:`Service` object for this :class:`Endpoint`.
        All other keyword arguments are included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Service`` is not logged in.
        :raises HTTPError: Raised when an error in the request occurs.
        :param path_segment: A path segment relative to this endpoint.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode of the namespace (optional).
        :type sharing: ``string``
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        **Example**::

            import splunklib.client
            s = client.service(...)
            apps = s.apps
            apps.post(name='boris') == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '2908'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 18:34:50 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'Created',
                 'status': 201}
            apps.get('nonexistant/path') # raises HTTPError
            s.logout()
            apps.get() # raises AuthenticationError
        """
        if path_segment.startswith('/'):
            path = path_segment
        else:
            path = self.service._abspath(self.path + path_segment, owner=owner, app=app, sharing=sharing)
        return self.service.post(path, owner=owner, app=app, sharing=sharing, **query)


# kwargs: path, app, owner, sharing, state
class Entity(Endpoint):
    """This class is a base class for Splunk entities in the REST API, such as
    saved searches, jobs, indexes, and inputs.

    ``Entity`` provides the majority of functionality required by entities.
    Subclasses only implement the special cases for individual entities.
    For example for deployment serverclasses, the subclass makes whitelists and
    blacklists into Python lists.

    An ``Entity`` is addressed like a dictionary, with a few extensions,
    so the following all work::

        ent['email.action']
        ent['disabled']
        ent['whitelist']

    Many endpoints have values that share a prefix, such as
    ``email.to``, ``email.action``, and ``email.subject``. You can extract
    the whole fields, or use the key ``email`` to get a dictionary of
    all the subelements. That is, ``ent['email']`` returns a
    dictionary with the keys ``to``, ``action``, ``subject``, and so on. If
    there are multiple levels of dots, each level is made into a
    subdictionary, so ``email.body.salutation`` can be accessed at
    ``ent['email']['body']['salutation']`` or
    ``ent['email.body.salutation']``.

    You can also access the fields as though they were the fields of a Python
    object, as in::

        ent.email.action
        ent.disabled
        ent.whitelist

    However, because some of the field names are not valid Python identifiers,
    the dictionary-like syntax is preferrable.

    The state of an :class:`Entity` object is cached, so accessing a field
    does not contact the server. If you think the values on the
    server have changed, call the :meth:`Entity.refresh` method.
    """
    # Not every endpoint in the API is an Entity or a Collection. For
    # example, a saved search at saved/searches/{name} has an additional
    # method saved/searches/{name}/scheduled_times, but this isn't an
    # entity in its own right. In these cases, subclasses should
    # implement a method that uses the get and post methods inherited
    # from Endpoint, calls the _load_atom function (it's elsewhere in
    # client.py, but not a method of any object) to read the
    # information, and returns the extracted data in a Pythonesque form.
    #
    # The primary use of subclasses of Entity is to handle specially
    # named fields in the Entity. If you only need to provide a default
    # value for an optional field, subclass Entity and define a
    # dictionary ``defaults``. For instance,::
    #
    #     class Hypothetical(Entity):
    #         defaults = {'anOptionalField': 'foo',
    #                     'anotherField': 'bar'}
    #
    # If you have to do more than provide a default, such as rename or
    # actually process values, then define a new method with the
    # ``@property`` decorator.
    #
    #     class Hypothetical(Entity):
    #         @property
    #         def foobar(self):
    #             return self.content['foo'] + "-" + self.content["bar"]

    # Subclasses can override defaults the default values for
    # optional fields. See above.
    defaults = {}

    def __init__(self, service, path, **kwargs):
        Endpoint.__init__(self, service, path)
        self._state = None
        if not kwargs.get('skip_refresh', False):
            self.refresh(kwargs.get('state', None))  # "Prefresh"
        return

    def __contains__(self, item):
        try:
            self[item]
            return True
        except KeyError:
            return False

    def __eq__(self, other):
        """Raises IncomparableException.

        Since Entity objects are snapshots of times on the server, no
        simple definition of equality will suffice beyond instance
        equality, and instance equality leads to strange situations
        such as::

            import splunklib.client as client
            c = client.connect(...)
            saved_searches = c.saved_searches
            x = saved_searches['asearch']

        but then ``x != saved_searches['asearch']``.

        whether or not there was a change on the server. Rather than
        try to do something fancy, we simple declare that equality is
        undefined for Entities.

        Makes no roundtrips to the server.
        """
        raise IncomparableException(
            "Equality is undefined for objects of class %s" % \
                self.__class__.__name__)

    def __getattr__(self, key):
        # Called when an attribute was not found by the normal method. In this
        # case we try to find it in self.content and then self.defaults.
        if key in self.state.content:
            return self.state.content[key]
        elif key in self.defaults:
            return self.defaults[key]
        else:
            raise AttributeError(key)

    def __getitem__(self, key):
        # getattr attempts to find a field on the object in the normal way,
        # then calls __getattr__ if it cannot.
        return getattr(self, key)

    # Load the Atom entry record from the given response - this is a method
    # because the "entry" record varies slightly by entity and this allows
    # for a subclass to override and handle any special cases.
    def _load_atom_entry(self, response):
        elem = _load_atom(response, XNAME_ENTRY)
        if isinstance(elem, list):
            raise AmbiguousReferenceException("Fetch from server returned multiple entries for name %s." % self.name)
        else:
            return elem.entry

    # Load the entity state record from the given response
    def _load_state(self, response):
        entry = self._load_atom_entry(response)
        return _parse_atom_entry(entry)

    def _run_action(self, path_segment, **kwargs):
        """Run a method and return the content Record from the returned XML.

        A method is a relative path from an Entity that is not itself
        an Entity. _run_action assumes that the returned XML is an
        Atom field containing one Entry, and the contents of Entry is
        what should be the return value. This is right in enough cases
        to make this method useful.
        """
        response = self.get(path_segment, **kwargs)
        data = self._load_atom_entry(response)
        rec = _parse_atom_entry(data)
        return rec.content

    def _proper_namespace(self, owner=None, app=None, sharing=None):
        """Produce a namespace sans wildcards for use in entity requests.

        This method tries to fill in the fields of the namespace which are `None`
        or wildcard (`'-'`) from the entity's namespace. If that fails, it uses
        the service's namespace.

        :param owner:
        :param app:
        :param sharing:
        :return:
        """
        if owner is None and app is None and sharing is None: # No namespace provided
            if self._state is not None and 'access' in self._state:
                return (self._state.access.owner,
                        self._state.access.app,
                        self._state.access.sharing)
            else:
                return (self.service.namespace['owner'],
                        self.service.namespace['app'],
                        self.service.namespace['sharing'])
        else:
            return (owner,app,sharing)

    def delete(self):
        owner, app, sharing = self._proper_namespace()
        return self.service.delete(self.path, owner=owner, app=app, sharing=sharing)

    def get(self, path_segment="", owner=None, app=None, sharing=None, **query):
        owner, app, sharing = self._proper_namespace(owner, app, sharing)
        return super(Entity, self).get(path_segment, owner=owner, app=app, sharing=sharing, **query)

    def post(self, path_segment="", owner=None, app=None, sharing=None, **query):
        owner, app, sharing = self._proper_namespace(owner, app, sharing)
        return super(Entity, self).post(path_segment, owner=owner, app=app, sharing=sharing, **query)

    def refresh(self, state=None):
        """Refreshes the state of this entity.

        If *state* is provided, load it as the new state for this
        entity. Otherwise, make a roundtrip to the server (by calling
        the :meth:`read` method of ``self``) to fetch an updated state,
        plus at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param state: Entity-specific arguments (optional).
        :type state: ``dict``
        :raises EntityDeletedException: Raised if the entity no longer exists on
            the server.

        **Example**::

            import splunklib.client as client
            s = client.connect(...)
            search = s.apps['search']
            search.refresh()
        """
        if state is not None:
            self._state = state
        else:
            self._state = self.read(self.get())
        return self

    @property
    def access(self):
        """Returns the access metadata for this entity.

        :return: A :class:`splunklib.data.Record` object with three keys:
            ``owner``, ``app``, and ``sharing``.
        """
        return self.state.access

    @property
    def content(self):
        """Returns the contents of the entity.

        :return: A ``dict`` containing values.
        """
        return self.state.content

    def disable(self):
        """Disables the entity at this endpoint."""
        self.post("disable")
        if self.service.restart_required:
            self.service.restart(120)
        return self

    def enable(self):
        """Enables the entity at this endpoint."""
        self.post("enable")
        return self

    @property
    def fields(self):
        """Returns the content metadata for this entity.

        :return: A :class:`splunklib.data.Record` object with three keys:
            ``required``, ``optional``, and ``wildcard``.
        """
        return self.state.fields

    @property
    def links(self):
        """Returns a dictionary of related resources.

        :return: A ``dict`` with keys and corresponding URLs.
        """
        return self.state.links

    @property
    def name(self):
        """Returns the entity name.

        :return: The entity name.
        :rtype: ``string``
        """
        return self.state.title

    def read(self, response):
        """ Reads the current state of the entity from the server. """
        results = self._load_state(response)
        # In lower layers of the SDK, we end up trying to URL encode
        # text to be dispatched via HTTP. However, these links are already
        # URL encoded when they arrive, and we need to mark them as such.
        unquoted_links = dict([(k, UrlEncoded(v, skip_encode=True))
                               for k,v in results['links'].iteritems()])
        results['links'] = unquoted_links
        return results

    def reload(self):
        """Reloads the entity."""
        self.post("_reload")
        return self

    @property
    def state(self):
        """Returns the entity's state record.

        :return: A ``dict`` containing fields and metadata for the entity.
        """
        if self._state is None: self.refresh()
        return self._state

    def update(self, **kwargs):
        """Updates the server with any changes you've made to the current entity
        along with any additional arguments you specify.

            **Note**: You cannot update the ``name`` field of an entity.

        Many of the fields in the REST API are not valid Python
        identifiers, which means you cannot pass them as keyword
        arguments. That is, Python will fail to parse the following::

            # This fails
            x.update(check-new=False, email.to='boris@utopia.net')

        However, you can always explicitly use a dictionary to pass
        such keys::

            # This works
            x.update(**{'check-new': False, 'email.to': 'boris@utopia.net'})

        :param kwargs: Additional entity-specific arguments (optional).
        :type kwargs: ``dict``

        :return: The entity this method is called on.
        :rtype: class:`Entity`
        """
        # The peculiarity in question: the REST API creates a new
        # Entity if we pass name in the dictionary, instead of the
        # expected behavior of updating this Entity. Therefore we
        # check for 'name' in kwargs and throw an error if it is
        # there.
        if 'name' in kwargs:
            raise IllegalOperationException('Cannot update the name of an Entity via the REST API.')
        self.post(**kwargs)
        return self


class ReadOnlyCollection(Endpoint):
    """This class represents a read-only collection of entities in the Splunk
    instance.
    """
    def __init__(self, service, path, item=Entity):
        Endpoint.__init__(self, service, path)
        self.item = item # Item accessor
        self.null_count = -1

    def __contains__(self, name):
        """Is there at least one entry called *name* in this collection?

        Makes a single roundtrip to the server, plus at most two more
        if
        the ``autologin`` field of :func:`connect` is set to ``True``.
        """
        try:
            self[name]
            return True
        except KeyError:
            return False
        except AmbiguousReferenceException:
            return True

    def __getitem__(self, key):
        """Fetch an item named *key* from this collection.

        A name is not a unique identifier in a collection. The unique
        identifier is a name plus a namespace. For example, there can
        be a saved search named ``'mysearch'`` with sharing ``'app'``
        in application ``'search'``, and another with sharing
        ``'user'`` with owner ``'boris'`` and application
        ``'search'``. If the ``Collection`` is attached to a
        ``Service`` that has ``'-'`` (wildcard) as user and app in its
        namespace, then both of these may be visible under the same
        name.

        Where there is no conflict, ``__getitem__`` will fetch the
        entity given just the name. If there is a conflict and you
        pass just a name, it will raise a ``ValueError``. In that
        case, add the namespace as a second argument.

        This function makes a single roundtrip to the server, plus at
        most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param key: The name to fetch, or a tuple (name, namespace).
        :return: An :class:`Entity` object.
        :raises KeyError: Raised if *key* does not exist.
        :raises ValueError: Raised if no namespace is specified and *key*
                            does not refer to a unique name.

        *Example*::

            s = client.connect(...)
            saved_searches = s.saved_searches
            x1 = saved_searches.create(
                'mysearch', 'search * | head 1',
                owner='admin', app='search', sharing='app')
            x2 = saved_searches.create(
                'mysearch', 'search * | head 1',
                owner='admin', app='search', sharing='user')
            # Raises ValueError:
            saved_searches['mysearch']
            # Fetches x1
            saved_searches[
                'mysearch',
                client.namespace(sharing='app', app='search')]
            # Fetches x2
            saved_searches[
                'mysearch',
                client.namespace(sharing='user', owner='boris', app='search')]
        """
        try:
            if isinstance(key, tuple) and len(key) == 2:
                # x[a,b] is translated to x.__getitem__( (a,b) ), so we
                # have to extract values out.
                key, ns = key
                key = UrlEncoded(key, encode_slash=True)
                response = self.get(key, owner=ns.owner, app=ns.app)
            else:
                key = UrlEncoded(key, encode_slash=True)
                response = self.get(key)
            entries = self._load_list(response)
            if len(entries) > 1:
                raise AmbiguousReferenceException("Found multiple entities named '%s'; please specify a namespace." % key)
            elif len(entries) == 0:
                raise KeyError(key)
            else:
                return entries[0]
        except HTTPError as he:
            if he.status == 404: # No entity matching key and namespace.
                raise KeyError(key)
            else:
                raise

    def __iter__(self, **kwargs):
        """Iterate over the entities in the collection.

        :param kwargs: Additional arguments.
        :type kwargs: ``dict``
        :rtype: iterator over entities.

        Implemented to give Collection a listish interface. This
        function always makes a roundtrip to the server, plus at most
        two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        **Example**::

            import splunklib.client as client
            c = client.connect(...)
            saved_searches = c.saved_searches
            for entity in saved_searches:
                print "Saved search named %s" % entity.name
        """

        for item in self.iter(**kwargs):
            yield item

    def __len__(self):
        """Enable ``len(...)`` for ``Collection`` objects.

        Implemented for consistency with a listish interface. No
        further failure modes beyond those possible for any method on
        an Endpoint.

        This function always makes a round trip to the server, plus at
        most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        **Example**::

            import splunklib.client as client
            c = client.connect(...)
            saved_searches = c.saved_searches
            n = len(saved_searches)
        """
        return len(self.list())

    def _entity_path(self, state):
        """Calculate the path to an entity to be returned.

        *state* should be the dictionary returned by
        :func:`_parse_atom_entry`. :func:`_entity_path` extracts the
        link to this entity from *state*, and strips all the namespace
        prefixes from it to leave only the relative path of the entity
        itself, sans namespace.

        :rtype: ``string``
        :return: an absolute path
        """
        # This has been factored out so that it can be easily
        # overloaded by Configurations, which has to switch its
        # entities' endpoints from its own properties/ to configs/.
        raw_path = urllib.unquote(state.links.alternate)
        if 'servicesNS/' in raw_path:
            return _trailing(raw_path, 'servicesNS/', '/', '/')
        elif 'services/' in raw_path:
            return _trailing(raw_path, 'services/')
        else:
            return raw_path

    def _load_list(self, response):
        """Converts *response* to a list of entities.

        *response* is assumed to be a :class:`Record` containing an
        HTTP response, of the form::

            {'status': 200,
             'headers': [('content-length', '232642'),
                         ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                         ('server', 'Splunkd'),
                         ('connection', 'close'),
                         ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                         ('date', 'Tue, 29 May 2012 15:27:08 GMT'),
                         ('content-type', 'text/xml; charset=utf-8')],
             'reason': 'OK',
             'body': ...a stream implementing .read()...}

        The ``'body'`` key refers to a stream containing an Atom feed,
        that is, an XML document with a toplevel element ``<feed>``,
        and within that element one or more ``<entry>`` elements.
        """
        # Some subclasses of Collection have to override this because
        # splunkd returns something that doesn't match
        # <feed><entry></entry><feed>.
        entries = _load_atom_entries(response)
        if entries is None: return []
        entities = []
        for entry in entries:
            state = _parse_atom_entry(entry)
            entity = self.item(
                self.service,
                self._entity_path(state),
                state=state)
            entities.append(entity)

        return entities

    def itemmeta(self):
        """Returns metadata for members of the collection.

        Makes a single roundtrip to the server, plus two more at most if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :return: A :class:`splunklib.data.Record` object containing the metadata.

        **Example**::

            import splunklib.client as client
            import pprint
            s = client.connect(...)
            pprint.pprint(s.apps.itemmeta())
            {'access': {'app': 'search',
                                    'can_change_perms': '1',
                                    'can_list': '1',
                                    'can_share_app': '1',
                                    'can_share_global': '1',
                                    'can_share_user': '1',
                                    'can_write': '1',
                                    'modifiable': '1',
                                    'owner': 'admin',
                                    'perms': {'read': ['*'], 'write': ['admin']},
                                    'removable': '0',
                                    'sharing': 'user'},
             'fields': {'optional': ['author',
                                        'configured',
                                        'description',
                                        'label',
                                        'manageable',
                                        'template',
                                        'visible'],
                                        'required': ['name'], 'wildcard': []}}
        """
        response = self.get("_new")
        content = _load_atom(response, MATCH_ENTRY_CONTENT)
        return _parse_atom_metadata(content)

    def iter(self, offset=0, count=None, pagesize=None, **kwargs):
        """Iterates over the collection.

        This method is equivalent to the :meth:`list` method, but
        it returns an iterator and can load a certain number of entities at a
        time from the server.

        :param offset: The index of the first entity to return (optional).
        :type offset: ``integer``
        :param count: The maximum number of entities to return (optional).
        :type count: ``integer``
        :param pagesize: The number of entities to load (optional).
        :type pagesize: ``integer``
        :param kwargs: Additional arguments (optional):

            - "search" (``string``): The search query to filter responses.

            - "sort_dir" (``string``): The direction to sort returned items:
              "asc" or "desc".

            - "sort_key" (``string``): The field to use for sorting (optional).

            - "sort_mode" (``string``): The collating sequence for sorting
              returned items: "auto", "alpha", "alpha_case", or "num".

        :type kwargs: ``dict``

        **Example**::

            import splunklib.client as client
            s = client.connect(...)
            for saved_search in s.saved_searches.iter(pagesize=10):
                # Loads 10 saved searches at a time from the
                # server.
                ...
        """
        assert pagesize is None or pagesize > 0
        if count is None:
            count = self.null_count
        fetched = 0
        while count == self.null_count or fetched < count:
            response = self.get(count=pagesize or count, offset=offset, **kwargs)
            items = self._load_list(response)
            N = len(items)
            fetched += N
            for item in items:
                yield item
            if pagesize is None or N < pagesize:
                break
            offset += N
            logging.debug("pagesize=%d, fetched=%d, offset=%d, N=%d, kwargs=%s", pagesize, fetched, offset, N, kwargs)

    # kwargs: count, offset, search, sort_dir, sort_key, sort_mode
    def list(self, count=None, **kwargs):
        """Retrieves a list of entities in this collection.

        The entire collection is loaded at once and is returned as a list. This
        function makes a single roundtrip to the server, plus at most two more if
        the ``autologin`` field of :func:`connect` is set to ``True``.
        There is no caching--every call makes at least one round trip.

        :param count: The maximum number of entities to return (optional).
        :type count: ``integer``
        :param kwargs: Additional arguments (optional):

            - "offset" (``integer``): The offset of the first item to return.

            - "search" (``string``): The search query to filter responses.

            - "sort_dir" (``string``): The direction to sort returned items:
              "asc" or "desc".

            - "sort_key" (``string``): The field to use for sorting (optional).

            - "sort_mode" (``string``): The collating sequence for sorting
              returned items: "auto", "alpha", "alpha_case", or "num".

        :type kwargs: ``dict``
        :return: A ``list`` of entities.
        """
        # response = self.get(count=count, **kwargs)
        # return self._load_list(response)
        return list(self.iter(count=count, **kwargs))




class Collection(ReadOnlyCollection):
    """A collection of entities.

    Splunk provides a number of different collections of distinct
    entity types: applications, saved searches, fired alerts, and a
    number of others. Each particular type is available separately
    from the Splunk instance, and the entities of that type are
    returned in a :class:`Collection`.

    The interface for :class:`Collection` does not quite match either
    ``list`` or ``dict`` in Python, because there are enough semantic
    mismatches with either to make its behavior surprising. A unique
    element in a :class:`Collection` is defined by a string giving its
    name plus namespace (although the namespace is optional if the name is
    unique).

    **Example**::

        import splunklib.client as client
        service = client.connect(...)
        mycollection = service.saved_searches
        mysearch = mycollection['my_search', client.namespace(owner='boris', app='natasha', sharing='user')]
        # Or if there is only one search visible named 'my_search'
        mysearch = mycollection['my_search']

    Similarly, ``name`` in ``mycollection`` works as you might expect (though
    you cannot currently pass a namespace to the ``in`` operator), as does
    ``len(mycollection)``.

    However, as an aggregate, :class:`Collection` behaves more like a
    list. If you iterate over a :class:`Collection`, you get an
    iterator over the entities, not the names and namespaces.

    **Example**::

        for entity in mycollection:
            assert isinstance(entity, client.Entity)

    Use the :meth:`create` and :meth:`delete` methods to create and delete
    entities in this collection. To view the access control list and other
    metadata of the collection, use the :meth:`ReadOnlyCollection.itemmeta` method.

    :class:`Collection` does no caching. Each call makes at least one
    round trip to the server to fetch data.
    """

    def create(self, name, **params):
        """Creates a new entity in this collection.

        This function makes either one or two roundtrips to the
        server, depending on the type of entities in this
        collection, plus at most two more if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param name: The name of the entity to create.
        :type name: ``string``
        :param namespace: A namespace, as created by the :func:`splunklib.binding.namespace`
            function (optional).  You can also set ``owner``, ``app``, and
            ``sharing`` in ``params``.
        :type namespace: A :class:`splunklib.data.Record` object with keys ``owner``, ``app``,
            and ``sharing``.
        :param params: Additional entity-specific arguments (optional).
        :type params: ``dict``
        :return: The new entity.
        :rtype: A subclass of :class:`Entity`, chosen by :meth:`Collection.self.item`.

        **Example**::

            import splunklib.client as client
            s = client.connect(...)
            applications = s.apps
            new_app = applications.create("my_fake_app")
        """
        if not isinstance(name, basestring):
            raise InvalidNameException("%s is not a valid name for an entity." % name)
        if 'namespace' in params:
            namespace = params.pop('namespace')
            params['owner'] = namespace.owner
            params['app'] = namespace.app
            params['sharing'] = namespace.sharing
        response = self.post(name=name, **params)
        atom = _load_atom(response, XNAME_ENTRY)
        if atom is None:
            # This endpoint doesn't return the content of the new
            # item. We have to go fetch it ourselves.
            return self[name]
        else:
            entry = atom.entry
            state = _parse_atom_entry(entry)
            entity = self.item(
                self.service,
                self._entity_path(state),
                state=state)
            return entity

    def delete(self, name, **params):
        """Deletes a specified entity from the collection.

        :param name: The name of the entity to delete.
        :type name: ``string``
        :return: The collection.
        :rtype: ``self``

        This method is implemented for consistency with the REST API's DELETE
        method.

        If there is no *name* entity on the server, a ``KeyError`` is
        thrown. This function always makes a roundtrip to the server.

        **Example**::

            import splunklib.client as client
            c = client.connect(...)
            saved_searches = c.saved_searches
            saved_searches.create('my_saved_search',
                                  'search * | head 1')
            assert 'my_saved_search' in saved_searches
            saved_searches.delete('my_saved_search')
            assert 'my_saved_search' not in saved_searches
        """
        name = UrlEncoded(name, encode_slash=True)
        if 'namespace' in params:
            namespace = params.pop('namespace')
            params['owner'] = namespace.owner
            params['app'] = namespace.app
            params['sharing'] = namespace.sharing
        try:
            self.service.delete(_path(self.path, name), **params)
        except HTTPError as he:
            # An HTTPError with status code 404 means that the entity
            # has already been deleted, and we reraise it as a
            # KeyError.
            if he.status == 404:
                raise KeyError("No such entity %s" % name)
            else:
                raise
        return self

    def get(self, name="", owner=None, app=None, sharing=None, **query):
        """Performs a GET request to the server on the collection.

        If *owner*, *app*, and *sharing* are omitted, this method takes a
        default namespace from the :class:`Service` object for this :class:`Endpoint`.
        All other keyword arguments are included in the URL as query parameters.

        :raises AuthenticationError: Raised when the ``Service`` is not logged in.
        :raises HTTPError: Raised when an error in the request occurs.
        :param path_segment: A path segment relative to this endpoint.
        :type path_segment: ``string``
        :param owner: The owner context of the namespace (optional).
        :type owner: ``string``
        :param app: The app context of the namespace (optional).
        :type app: ``string``
        :param sharing: The sharing mode for the namespace (optional).
        :type sharing: "global", "system", "app", or "user"
        :param query: All other keyword arguments, which are used as query
            parameters.
        :type query: ``string``
        :return: The response from the server.
        :rtype: ``dict`` with keys ``body``, ``headers``, ``reason``,
                and ``status``

        Example:
        
        import splunklib.client
            s = client.service(...)
            saved_searches = s.saved_searches
            saved_searches.get("my/saved/search") == \\
                {'body': ...a response reader object...,
                 'headers': [('content-length', '26208'),
                             ('expires', 'Fri, 30 Oct 1998 00:00:00 GMT'),
                             ('server', 'Splunkd'),
                             ('connection', 'close'),
                             ('cache-control', 'no-store, max-age=0, must-revalidate, no-cache'),
                             ('date', 'Fri, 11 May 2012 16:30:35 GMT'),
                             ('content-type', 'text/xml; charset=utf-8')],
                 'reason': 'OK',
                 'status': 200}
            saved_searches.get('nonexistant/search') # raises HTTPError
            s.logout()
            saved_searches.get() # raises AuthenticationError

        """
        name = UrlEncoded(name, encode_slash=True)
        return super(Collection, self).get(name, owner, app, sharing, **query)




class ConfigurationFile(Collection):
    """This class contains all of the stanzas from one configuration file.
    """
    # __init__'s arguments must match those of an Entity, not a
    # Collection, since it is being created as the elements of a
    # Configurations, which is a Collection subclass.
    def __init__(self, service, path, **kwargs):
        Collection.__init__(self, service, path, item=Stanza)
        self.name = kwargs['state']['title']


class Configurations(Collection):
    """This class provides access to the configuration files from this Splunk
    instance. Retrieve this collection using :meth:`Service.confs`.

    Splunk's configuration is divided into files, and each file into
    stanzas. This collection is unusual in that the values in it are
    themselves collections of :class:`ConfigurationFile` objects.
    """
    def __init__(self, service):
        Collection.__init__(self, service, PATH_PROPERTIES, item=ConfigurationFile)
        if self.service.namespace.owner == '-' or self.service.namespace.app == '-':
            raise ValueError("Configurations cannot have wildcards in namespace.")

    def __getitem__(self, key):
        # The superclass implementation is designed for collections that contain
        # entities. This collection (Configurations) contains collections
        # (ConfigurationFile).
        # 
        # The configurations endpoint returns multiple entities when we ask for a single file.
        # This screws up the default implementation of __getitem__ from Collection, which thinks
        # that multiple entities means a name collision, so we have to override it here.
        try:
            response = self.get(key)
            return ConfigurationFile(self.service, PATH_CONF % key, state={'title': key})
        except HTTPError as he:
            if he.status == 404: # No entity matching key
                raise KeyError(key)
            else:
                raise

    def __contains__(self, key):
        # configs/conf-{name} never returns a 404. We have to post to properties/{name}
        # in order to find out if a configuration exists.
        try:
            response = self.get(key)
            return True
        except HTTPError as he:
            if he.status == 404: # No entity matching key
                return False
            else:
                raise

    def create(self, name):
        """ Creates a configuration file named *name*.

        If there is already a configuration file with that name,
        the existing file is returned.

        :param name: The name of the configuration file.
        :type name: ``string``

        :return: The :class:`ConfigurationFile` object.
        """
        # This has to be overridden to handle the plumbing of creating
        # a ConfigurationFile (which is a Collection) instead of some
        # Entity.
        if not isinstance(name, basestring):
            raise ValueError("Invalid name: %s" % repr(name))
        response = self.post(__conf=name)
        if response.status == 303:
            return self[name]
        elif response.status == 201:
            return ConfigurationFile(self.service, PATH_CONF % name, item=Stanza, state={'title': name})
        else:
            raise ValueError("Unexpected status code %s returned from creating a stanza" % response.status)

    def delete(self, key):
        """Raises `IllegalOperationException`."""
        raise IllegalOperationException("Cannot delete configuration files from the REST API.")

    def _entity_path(self, state):
        # Overridden to make all the ConfigurationFile objects
        # returned refer to the configs/ path instead of the
        # properties/ path used by Configrations.
        return PATH_CONF % state['title']


class Stanza(Entity):
    """This class contains a single configuration stanza."""

    def submit(self, stanza):
        """Adds keys to the current configuration stanza as a 
        dictionary of key-value pairs.
        
        :param stanza: A dictionary of key-value pairs for the stanza.
        :type stanza: ``dict``
        :return: The :class:`Stanza` object.
        """
        body = _encode(**stanza)
        self.service.post(self.path, body=body)
        return self

    def __len__(self):
        # The stanza endpoint returns all the keys at the same level in the XML as the eai information
        # and 'disabled', so to get an accurate length, we have to filter those out and have just
        # the stanza keys.
        return len([x for x in self._state.content.keys()
                    if not x.startswith('eai') and x != 'disabled'])


class StoragePassword(Entity):
    """This class contains a storage password.
    """
    def __init__(self, service, path, **kwargs):
        state = kwargs.get('state', None)
        kwargs['skip_refresh'] = kwargs.get('skip_refresh', state is not None)
        super(StoragePassword, self).__init__(service, path, **kwargs)
        self._state = state

    @property
    def clear_password(self):
        return self.content.get('clear_password')

    @property
    def encrypted_password(self):
        return self.content.get('encr_password')

    @property
    def realm(self):
        return self.content.get('realm')

    @property
    def username(self):
        return self.content.get('username')


class StoragePasswords(Collection):
    """This class provides access to the storage passwords from this Splunk
    instance. Retrieve this collection using :meth:`Service.storage_passwords`.
    """
    def __init__(self, service):
        if service.namespace.owner == '-' or service.namespace.app == '-':
            raise ValueError("StoragePasswords cannot have wildcards in namespace.")
        super(StoragePasswords, self).__init__(service, PATH_STORAGE_PASSWORDS, item=StoragePassword)

    def create(self, password, username, realm=None):
        """ Creates a storage password.

        A `StoragePassword` can be identified by <username>, or by <realm>:<username> if the
        optional realm parameter is also provided.

        :param password: The password for the credentials - this is the only part of the credentials that will be stored securely.
        :type name: ``string``
        :param username: The username for the credentials.
        :type name: ``string``
        :param realm: The credential realm. (optional)
        :type name: ``string``

        :return: The :class:`StoragePassword` object created.
        """
        if not isinstance(username, basestring):
            raise ValueError("Invalid name: %s" % repr(username))

        if realm is None:
            response = self.post(password=password, name=username)
        else:
            response = self.post(password=password, realm=realm, name=username)

        if response.status != 201:
            raise ValueError("Unexpected status code %s returned from creating a stanza" % response.status)

        entries = _load_atom_entries(response)
        state = _parse_atom_entry(entries[0])
        storage_password = StoragePassword(self.service, self._entity_path(state), state=state, skip_refresh=True)

        return storage_password

    def delete(self, username, realm=None):
        """Delete a storage password by username and/or realm.

        The identifier can be passed in through the username parameter as
        <username> or <realm>:<username>, but the preferred way is by
        passing in the username and realm parameters.

        :param username: The username for the credentials, or <realm>:<username> if the realm parameter is omitted.
        :type name: ``string``
        :param realm: The credential realm. (optional)
        :type name: ``string``
        :return: The `StoragePassword` collection.
        :rtype: ``self``
        """
        if realm is None:
            # This case makes the username optional, so
            # the full name can be passed in as realm.
            # Assume it's already encoded.
            name = username
        else:
            # Encode each component separately
            name = UrlEncoded(realm, encode_slash=True) + ":" + UrlEncoded(username, encode_slash=True)

        # Append the : expected at the end of the name
        if name[-1] is not ":":
            name = name + ":"
        return Collection.delete(self, name)


class AlertGroup(Entity):
    """This class represents a group of fired alerts for a saved search. Access
    it using the :meth:`alerts` property."""
    def __init__(self, service, path, **kwargs):
        Entity.__init__(self, service, path, **kwargs)

    def __len__(self):
        return self.count

    @property
    def alerts(self):
        """Returns a collection of triggered alerts.

        :return: A :class:`Collection` of triggered alerts.
        """
        return Collection(self.service, self.path)

    @property
    def count(self):
        """Returns the count of triggered alerts.

        :return: The triggered alert count.
        :rtype: ``integer``
        """
        return int(self.content.get('triggered_alert_count', 0))


class Indexes(Collection):
    """This class contains the collection of indexes in this Splunk instance.
    Retrieve this collection using :meth:`Service.indexes`.
    """
    def get_default(self):
        """ Returns the name of the default index.

        :return: The name of the default index.

        """
        index = self['_audit']
        return index['defaultDatabase']

    def delete(self, name):
        """ Deletes a given index.

        **Note**: This method is only supported in Splunk 5.0 and later.

        :param name: The name of the index to delete.
        :type name: ``string``
        """
        if self.service.splunk_version >= (5,):
            Collection.delete(self, name)
        else:
            raise IllegalOperationException("Deleting indexes via the REST API is "
                                            "not supported before Splunk version 5.")


class Index(Entity):
    """This class represents an index and provides different operations, such as
    cleaning the index, writing to the index, and so forth."""
    def __init__(self, service, path, **kwargs):
        Entity.__init__(self, service, path, **kwargs)

    def attach(self, host=None, source=None, sourcetype=None):
        """Opens a stream (a writable socket) for writing events to the index.

        :param host: The host value for events written to the stream.
        :type host: ``string``
        :param source: The source value for events written to the stream.
        :type source: ``string``
        :param sourcetype: The sourcetype value for events written to the
            stream.
        :type sourcetype: ``string``

        :return: A writable socket.
        """
        args = { 'index': self.name }
        if host is not None: args['host'] = host
        if source is not None: args['source'] = source
        if sourcetype is not None: args['sourcetype'] = sourcetype
        path = UrlEncoded(PATH_RECEIVERS_STREAM + "?" + urllib.urlencode(args), skip_encode=True)

        cookie_or_auth_header = "Authorization: %s\r\n" % self.service.token

        # If we have cookie(s), use them instead of "Authorization: ..."
        if self.service.has_cookies():
            cookie_or_auth_header = "Cookie: %s\r\n" % _make_cookie_header(self.service.get_cookies().items())

        # Since we need to stream to the index connection, we have to keep
        # the connection open and use the Splunk extension headers to note
        # the input mode
        sock = self.service.connect()
        headers = ["POST %s HTTP/1.1\r\n" % self.service._abspath(path),
                   "Host: %s:%s\r\n" % (self.service.host, int(self.service.port)),
                   "Accept-Encoding: identity\r\n",
                   cookie_or_auth_header,
                   "X-Splunk-Input-Mode: Streaming\r\n",
                   "\r\n"]
        
        for h in headers:
            sock.write(h)
        return sock

    @contextlib.contextmanager
    def attached_socket(self, *args, **kwargs):
        """Opens a raw socket in a ``with`` block to write data to Splunk.

        The arguments are identical to those for :meth:`attach`. The socket is
        automatically closed at the end of the ``with`` block, even if an
        exception is raised in the block.

        :param host: The host value for events written to the stream.
        :type host: ``string``
        :param source: The source value for events written to the stream.
        :type source: ``string``
        :param sourcetype: The sourcetype value for events written to the
            stream.
        :type sourcetype: ``string``

        :returns: Nothing.

        **Example**::

            import splunklib.client as client
            s = client.connect(...)
            index = s.indexes['some_index']
            with index.attached_socket(sourcetype='test') as sock:
                sock.send('Test event\\r\\n')

        """
        try:
            sock = self.attach(*args, **kwargs)
            yield sock
        finally:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()

    def clean(self, timeout=60):
        """Deletes the contents of the index.

        This method blocks until the index is empty, because it needs to restore
        values at the end of the operation.

        :param timeout: The time-out period for the operation, in seconds (the
            default is 60).
        :type timeout: ``integer``

        :return: The :class:`Index`.
        """
        self.refresh()

        tds = self['maxTotalDataSizeMB']
        ftp = self['frozenTimePeriodInSecs']
        was_disabled_initially = self.disabled
        try:
            if (not was_disabled_initially and \
                self.service.splunk_version < (5,)):
                # Need to disable the index first on Splunk 4.x,
                # but it doesn't work to disable it on 5.0.
                self.disable()
            self.update(maxTotalDataSizeMB=1, frozenTimePeriodInSecs=1)
            self.roll_hot_buckets()

            # Wait until event count goes to 0.
            start = datetime.now()
            diff = timedelta(seconds=timeout)
            while self.content.totalEventCount != '0' and datetime.now() < start+diff:
                sleep(1)
                self.refresh()

            if self.content.totalEventCount != '0':
                raise OperationError, "Cleaning index %s took longer than %s seconds; timing out." %\
                                      (self.name, timeout)
        finally:
            # Restore original values
            self.update(maxTotalDataSizeMB=tds, frozenTimePeriodInSecs=ftp)
            if (not was_disabled_initially and \
                self.service.splunk_version < (5,)):
                # Re-enable the index if it was originally enabled and we messed with it.
                self.enable()

        return self

    def roll_hot_buckets(self):
        """Performs rolling hot buckets for this index.

        :return: The :class:`Index`.
        """
        self.post("roll-hot-buckets")
        return self

    def submit(self, event, host=None, source=None, sourcetype=None):
        """Submits a single event to the index using ``HTTP POST``.

        :param event: The event to submit.
        :type event: ``string``
        :param `host`: The host value of the event.
        :type host: ``string``
        :param `source`: The source value of the event.
        :type source: ``string``
        :param `sourcetype`: The sourcetype value of the event.
        :type sourcetype: ``string``

        :return: The :class:`Index`.
        """
        args = { 'index': self.name }
        if host is not None: args['host'] = host
        if source is not None: args['source'] = source
        if sourcetype is not None: args['sourcetype'] = sourcetype

        # The reason we use service.request directly rather than POST
        # is that we are not sending a POST request encoded using
        # x-www-form-urlencoded (as we do not have a key=value body),
        # because we aren't really sending a "form".
        self.service.post(PATH_RECEIVERS_SIMPLE, body=event, **args)
        return self

    # kwargs: host, host_regex, host_segment, rename-source, sourcetype
    def upload(self, filename, **kwargs):
        """Uploads a file for immediate indexing.

        **Note**: The file must be locally accessible from the server.

        :param filename: The name of the file to upload. The file can be a
            plain, compressed, or archived file.
        :type filename: ``string``
        :param kwargs: Additional arguments (optional). For more about the
            available parameters, see `Index parameters <http://dev.splunk.com/view/SP-CAAAEE6#indexparams>`_ on Splunk Developer Portal.
        :type kwargs: ``dict``

        :return: The :class:`Index`.
        """
        kwargs['index'] = self.name
        path = 'data/inputs/oneshot'
        self.service.post(path, name=filename, **kwargs)
        return self


class Input(Entity):
    """This class represents a Splunk input. This class is the base for all
    typed input classes and is also used when the client does not recognize an
    input kind.
    """
    def __init__(self, service, path, kind=None, **kwargs):
        # kind can be omitted (in which case it is inferred from the path)
        # Otherwise, valid values are the paths from data/inputs ("udp",
        # "monitor", "tcp/raw"), or two special cases: "tcp" (which is "tcp/raw")
        # and "splunktcp" (which is "tcp/cooked").
        Entity.__init__(self, service, path, **kwargs)
        if kind is None:
            path_segments = path.split('/')
            i = path_segments.index('inputs') + 1
            if path_segments[i] == 'tcp':
                self.kind = path_segments[i] + '/' + path_segments[i+1]
            else:
                self.kind = path_segments[i]
        else:
            self.kind = kind

        # Handle old input kind names.
        if self.kind == 'tcp':
            self.kind = 'tcp/raw'
        if self.kind == 'splunktcp':
            self.kind = 'tcp/cooked'

    def update(self, **kwargs):
        """Updates the server with any changes you've made to the current input
        along with any additional arguments you specify.

        :param kwargs: Additional arguments (optional). For more about the
            available parameters, see `Input parameters <http://dev.splunk.com/view/SP-CAAAEE6#inputparams>`_ on Splunk Developer Portal.
        :type kwargs: ``dict``

        :return: The input this method was called on.
        :rtype: class:`Input`
        """
        # UDP and TCP inputs require special handling due to their restrictToHost
        # field. For all other inputs kinds, we can dispatch to the superclass method.
        if self.kind not in ['tcp', 'splunktcp', 'tcp/raw', 'tcp/cooked', 'udp']:
            return super(Input, self).update(**kwargs)
        else:
            # The behavior of restrictToHost is inconsistent across input kinds and versions of Splunk.
            # In Splunk 4.x, the name of the entity is only the port, independent of the value of
            # restrictToHost. In Splunk 5.0 this changed so the name will be of the form <restrictToHost>:<port>.
            # In 5.0 and 5.0.1, if you don't supply the restrictToHost value on every update, it will
            # remove the host restriction from the input. As of 5.0.2 you simply can't change restrictToHost
            # on an existing input.

            # The logic to handle all these cases:
            # - Throw an exception if the user tries to set restrictToHost on an existing input
            #   for *any* version of Splunk.
            # - Set the existing restrictToHost value on the update args internally so we don't
            #   cause it to change in Splunk 5.0 and 5.0.1.
            to_update = kwargs.copy()

            if 'restrictToHost' in kwargs:
                raise IllegalOperationException("Cannot set restrictToHost on an existing input with the SDK.")
            elif 'restrictToHost' in self._state.content:
                to_update['restrictToHost'] = self._state.content['restrictToHost']

            # Do the actual update operation.
            return super(Input, self).update(**to_update)


# Inputs is a "kinded" collection, which is a heterogenous collection where
# each item is tagged with a kind, that provides a single merged view of all
# input kinds.
class Inputs(Collection):
    """This class represents a collection of inputs. The collection is
    heterogeneous and each member of the collection contains a *kind* property
    that indicates the specific type of input.
    Retrieve this collection using :meth:`Service.inputs`."""

    def __init__(self, service, kindmap=None):
        Collection.__init__(self, service, PATH_INPUTS, item=Input)

    def __getitem__(self, key):
        # The key needed to retrieve the input needs it's parenthesis to be URL encoded
        # based on the REST API for input
        # <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTinput>
        if isinstance(key, tuple) and len(key) == 2:
            # Fetch a single kind
            key, kind = key
            key = UrlEncoded(key, encode_slash=True)
            try:
                response = self.get(self.kindpath(kind) + "/" + key)
                entries = self._load_list(response)
                if len(entries) > 1:
                    raise AmbiguousReferenceException("Found multiple inputs of kind %s named %s." % (kind, key))
                elif len(entries) == 0:
                    raise KeyError((key, kind))
                else:
                    return entries[0]
            except HTTPError as he:
                if he.status == 404: # No entity matching kind and key
                    raise KeyError((key, kind))
                else:
                    raise
        else:
            # Iterate over all the kinds looking for matches.
            kind = None
            candidate = None
            key = UrlEncoded(key, encode_slash=True)
            for kind in self.kinds:
                try:
                    response = self.get(kind + "/" + key)
                    entries = self._load_list(response)
                    if len(entries) > 1:
                        raise AmbiguousReferenceException("Found multiple inputs of kind %s named %s." % (kind, key))
                    elif len(entries) == 0:
                        pass
                    else:
                        if candidate is not None: # Already found at least one candidate
                            raise AmbiguousReferenceException("Found multiple inputs named %s, please specify a kind" % key)
                        candidate = entries[0]
                except HTTPError as he:
                    if he.status == 404:
                        pass # Just carry on to the next kind.
                    else:
                        raise
            if candidate is None:
                raise KeyError(key) # Never found a match.
            else:
                return candidate

    def __contains__(self, key):
        if isinstance(key, tuple) and len(key) == 2:
            # If we specify a kind, this will shortcut properly
            try:
                self.__getitem__(key)
                return True
            except KeyError:
                return False
        else:
            # Without a kind, we want to minimize the number of round trips to the server, so we
            # reimplement some of the behavior of __getitem__ in order to be able to stop searching
            # on the first hit.
            for kind in self.kinds:
                try:
                    response = self.get(self.kindpath(kind) + "/" + key)
                    entries = self._load_list(response)
                    if len(entries) > 0:
                        return True
                    else:
                        pass
                except HTTPError as he:
                    if he.status == 404:
                        pass # Just carry on to the next kind.
                    else:
                        raise
            return False

    def create(self, name, kind, **kwargs):
        """Creates an input of a specific kind in this collection, with any
        arguments you specify.

        :param `name`: The input name.
        :type name: ``string``
        :param `kind`: The kind of input:

            - "ad": Active Directory

            - "monitor": Files and directories

            - "registry": Windows Registry

            - "script": Scripts

            - "splunktcp": TCP, processed

            - "tcp": TCP, unprocessed

            - "udp": UDP

            - "win-event-log-collections": Windows event log

            - "win-perfmon": Performance monitoring

            - "win-wmi-collections": WMI

        :type kind: ``string``
        :param `kwargs`: Additional arguments (optional). For more about the
            available parameters, see `Input parameters <http://dev.splunk.com/view/SP-CAAAEE6#inputparams>`_ on Splunk Developer Portal.

        :type kwargs: ``dict``

        :return: The new :class:`Input`.
        """
        kindpath = self.kindpath(kind)
        self.post(kindpath, name=name, **kwargs)

        # If we created an input with restrictToHost set, then
        # its path will be <restrictToHost>:<name>, not just <name>,
        # and we have to adjust accordingly.

        # Url encodes the name of the entity.
        name = UrlEncoded(name, encode_slash=True)
        path = _path(
            self.path + kindpath,
            '%s:%s' % (kwargs['restrictToHost'], name) \
                if kwargs.has_key('restrictToHost') else name
                )
        return Input(self.service, path, kind)

    def delete(self, name, kind=None):
        """Removes an input from the collection.

        :param `kind`: The kind of input:

            - "ad": Active Directory

            - "monitor": Files and directories

            - "registry": Windows Registry

            - "script": Scripts

            - "splunktcp": TCP, processed

            - "tcp": TCP, unprocessed

            - "udp": UDP

            - "win-event-log-collections": Windows event log

            - "win-perfmon": Performance monitoring

            - "win-wmi-collections": WMI

        :type kind: ``string``
        :param name: The name of the input to remove.
        :type name: ``string``

        :return: The :class:`Inputs` collection.
        """
        if kind is None:
            self.service.delete(self[name].path)
        else:
            self.service.delete(self[name, kind].path)
        return self

    def itemmeta(self, kind):
        """Returns metadata for the members of a given kind.

        :param `kind`: The kind of input:

            - "ad": Active Directory

            - "monitor": Files and directories

            - "registry": Windows Registry

            - "script": Scripts

            - "splunktcp": TCP, processed

            - "tcp": TCP, unprocessed

            - "udp": UDP

            - "win-event-log-collections": Windows event log

            - "win-perfmon": Performance monitoring

            - "win-wmi-collections": WMI

        :type kind: ``string``

        :return: The metadata.
        :rtype: class:``splunklib.data.Record``
        """
        response = self.get("%s/_new" % self._kindmap[kind])
        content = _load_atom(response, MATCH_ENTRY_CONTENT)
        return _parse_atom_metadata(content)

    def _get_kind_list(self, subpath=None):
        if subpath is None:
            subpath = []

        kinds = []
        response = self.get('/'.join(subpath))
        content = _load_atom_entries(response)
        for entry in content:
            this_subpath = subpath + [entry.title]
            # The "all" endpoint doesn't work yet.
            # The "tcp/ssl" endpoint is not a real input collection.
            if entry.title == 'all' or this_subpath == ['tcp','ssl']:
                continue
            elif 'create' in [x.rel for x in entry.link]:
                path = '/'.join(subpath + [entry.title])
                kinds.append(path)
            else:
                subkinds = self._get_kind_list(subpath + [entry.title])
                kinds.extend(subkinds)
        return kinds

    @property
    def kinds(self):
        """Returns the input kinds on this Splunk instance.

        :return: The list of input kinds.
        :rtype: ``list``
        """
        return self._get_kind_list()

    def kindpath(self, kind):
        """Returns a path to the resources for a given input kind.

        :param `kind`: The kind of input:

            - "ad": Active Directory

            - "monitor": Files and directories

            - "registry": Windows Registry

            - "script": Scripts

            - "splunktcp": TCP, processed

            - "tcp": TCP, unprocessed

            - "udp": UDP

            - "win-event-log-collections": Windows event log

            - "win-perfmon": Performance monitoring

            - "win-wmi-collections": WMI

        :type kind: ``string``

        :return: The relative endpoint path.
        :rtype: ``string``
        """
        if kind in self.kinds:
            return UrlEncoded(kind, skip_encode=True)
        # Special cases
        elif kind == 'tcp':
            return UrlEncoded('tcp/raw', skip_encode=True)
        elif kind == 'splunktcp':
            return UrlEncoded('tcp/cooked', skip_encode=True)
        else:
            raise ValueError("No such kind on server: %s" % kind)

    def list(self, *kinds, **kwargs):
        """Returns a list of inputs that are in the :class:`Inputs` collection.
        You can also filter by one or more input kinds.

        This function iterates over all possible inputs, regardless of any arguments you
        specify. Because the :class:`Inputs` collection is the union of all the inputs of each
        kind, this method implements parameters such as "count", "search", and so
        on at the Python level once all the data has been fetched. The exception
        is when you specify a single input kind, and then this method makes a single request
        with the usual semantics for parameters.

        :param kinds: The input kinds to return (optional).

            - "ad": Active Directory

            - "monitor": Files and directories

            - "registry": Windows Registry

            - "script": Scripts

            - "splunktcp": TCP, processed

            - "tcp": TCP, unprocessed

            - "udp": UDP

            - "win-event-log-collections": Windows event log

            - "win-perfmon": Performance monitoring

            - "win-wmi-collections": WMI

        :type kinds: ``string``
        :param kwargs: Additional arguments (optional):

            - "count" (``integer``): The maximum number of items to return.

            - "offset" (``integer``): The offset of the first item to return.

            - "search" (``string``): The search query to filter responses.

            - "sort_dir" (``string``): The direction to sort returned items:
              "asc" or "desc".

            - "sort_key" (``string``): The field to use for sorting (optional).

            - "sort_mode" (``string``): The collating sequence for sorting
              returned items: "auto", "alpha", "alpha_case", or "num".

        :type kwargs: ``dict``

        :return: A list of input kinds.
        :rtype: ``list``
        """
        if len(kinds) == 0:
            kinds = self.kinds
        if len(kinds) == 1:
            kind = kinds[0]
            logging.debug("Inputs.list taking short circuit branch for single kind.")
            path = self.kindpath(kind)
            logging.debug("Path for inputs: %s", path)
            try:
                path = UrlEncoded(path, skip_encode=True)
                response = self.get(path, **kwargs)
            except HTTPError, he:
                if he.status == 404: # No inputs of this kind
                    return []
            entities = []
            entries = _load_atom_entries(response)
            if entries is None:
                return [] # No inputs in a collection comes back with no feed or entry in the XML
            for entry in entries:
                state = _parse_atom_entry(entry)
                # Unquote the URL, since all URL encoded in the SDK
                # should be of type UrlEncoded, and all str should not
                # be URL encoded.
                path = urllib.unquote(state.links.alternate)
                entity = Input(self.service, path, kind, state=state)
                entities.append(entity)
            return entities

        search = kwargs.get('search', '*')

        entities = []
        for kind in kinds:
            response = None
            try:
                kind = UrlEncoded(kind, skip_encode=True)
                response = self.get(self.kindpath(kind), search=search)
            except HTTPError as e:
                if e.status == 404:
                    continue # No inputs of this kind
                else:
                    raise

            entries = _load_atom_entries(response)
            if entries is None: continue # No inputs to process
            for entry in entries:
                state = _parse_atom_entry(entry)
                # Unquote the URL, since all URL encoded in the SDK
                # should be of type UrlEncoded, and all str should not
                # be URL encoded.
                path = urllib.unquote(state.links.alternate)
                entity = Input(self.service, path, kind, state=state)
                entities.append(entity)
        if 'offset' in kwargs:
            entities = entities[kwargs['offset']:]
        if 'count' in kwargs:
            entities = entities[:kwargs['count']]
        if kwargs.get('sort_mode', None) == 'alpha':
            sort_field = kwargs.get('sort_field', 'name')
            if sort_field == 'name':
                f = lambda x: x.name.lower()
            else:
                f = lambda x: x[sort_field].lower()
            entities = sorted(entities, key=f)
        if kwargs.get('sort_mode', None) == 'alpha_case':
            sort_field = kwargs.get('sort_field', 'name')
            if sort_field == 'name':
                f = lambda x: x.name
            else:
                f = lambda x: x[sort_field]
            entities = sorted(entities, key=f)
        if kwargs.get('sort_dir', 'asc') == 'desc':
            entities = list(reversed(entities))
        return entities

    def __iter__(self, **kwargs):
        for item in self.iter(**kwargs):
            yield item

    def iter(self, **kwargs):
        """ Iterates over the collection of inputs.

        :param kwargs: Additional arguments (optional):

            - "count" (``integer``): The maximum number of items to return.

            - "offset" (``integer``): The offset of the first item to return.

            - "search" (``string``): The search query to filter responses.

            - "sort_dir" (``string``): The direction to sort returned items:
              "asc" or "desc".

            - "sort_key" (``string``): The field to use for sorting (optional).

            - "sort_mode" (``string``): The collating sequence for sorting
              returned items: "auto", "alpha", "alpha_case", or "num".

        :type kwargs: ``dict``
        """
        for item in self.list(**kwargs):
            yield item

    def oneshot(self, path, **kwargs):
        """ Creates a oneshot data input, which is an upload of a single file
        for one-time indexing.

        :param path: The path and filename.
        :type path: ``string``
        :param kwargs: Additional arguments (optional). For more about the
            available parameters, see `Input parameters <http://dev.splunk.com/view/SP-CAAAEE6#inputparams>`_ on Splunk Developer Portal.
        :type kwargs: ``dict``
        """
        self.post('oneshot', name=path, **kwargs)


class Job(Entity):
    """This class represents a search job."""
    def __init__(self, service, sid, **kwargs):
        path = PATH_JOBS + sid
        Entity.__init__(self, service, path, skip_refresh=True, **kwargs)
        self.sid = sid

    # The Job entry record is returned at the root of the response
    def _load_atom_entry(self, response):
        return _load_atom(response).entry

    def cancel(self):
        """Stops the current search and deletes the results cache.

        :return: The :class:`Job`.
        """
        try:
            self.post("control", action="cancel")
        except HTTPError as he:
            if he.status == 404:
                # The job has already been cancelled, so
                # cancelling it twice is a nop.
                pass
            else:
                raise
        return self

    def disable_preview(self):
        """Disables preview for this job.

        :return: The :class:`Job`.
        """
        self.post("control", action="disablepreview")
        return self

    def enable_preview(self):
        """Enables preview for this job.

        **Note**: Enabling preview might slow search considerably.

        :return: The :class:`Job`.
        """
        self.post("control", action="enablepreview")
        return self

    def events(self, **kwargs):
        """Returns a streaming handle to this job's events.

        :param kwargs: Additional parameters (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/events
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Fevents>`_
            in the REST API documentation.
        :type kwargs: ``dict``

        :return: The ``InputStream`` IO handle to this job's events.
        """
        kwargs['segmentation'] = kwargs.get('segmentation', 'none')
        return self.get("events", **kwargs).body

    def finalize(self):
        """Stops the job and provides intermediate results for retrieval.

        :return: The :class:`Job`.
        """
        self.post("control", action="finalize")
        return self

    def is_done(self):
        """Indicates whether this job finished running.

        :return: ``True`` if the job is done, ``False`` if not.
        :rtype: ``boolean``
        """
        if not self.is_ready():
            return False
        done = (self._state.content['isDone'] == '1')
        return done

    def is_ready(self):
        """Indicates whether this job is ready for querying.

        :return: ``True`` if the job is ready, ``False`` if not.
        :rtype: ``boolean``

        """
        response = self.get()
        if response.status == 204:
            return False
        self._state = self.read(response)
        ready = self._state.content['dispatchState'] not in ['QUEUED', 'PARSING']
        return ready

    @property
    def name(self):
        """Returns the name of the search job, which is the search ID (SID).

        :return: The search ID.
        :rtype: ``string``
        """
        return self.sid

    def pause(self):
        """Suspends the current search.

        :return: The :class:`Job`.
        """
        self.post("control", action="pause")
        return self

    def results(self, **query_params):
        """Returns a streaming handle to this job's search results. To get a
        nice, Pythonic iterator, pass the handle to :class:`splunklib.results.ResultsReader`,
        as in::

            import splunklib.client as client
            import splunklib.results as results
            from time import sleep
            service = client.connect(...)
            job = service.jobs.create("search * | head 5")
            while not job.is_done():
                sleep(.2)
            rr = results.ResultsReader(job.results())
            for result in rr:
                if isinstance(result, results.Message):
                    # Diagnostic messages may be returned in the results
                    print '%s: %s' % (result.type, result.message)
                elif isinstance(result, dict):
                    # Normal events are returned as dicts
                    print result
            assert rr.is_preview == False

        Results are not available until the job has finished. If called on
        an unfinished job, the result is an empty event set.

        This method makes a single roundtrip
        to the server, plus at most two additional round trips if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param query_params: Additional parameters (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/results
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Fresults>`_.
        :type query_params: ``dict``

        :return: The ``InputStream`` IO handle to this job's results.
        """
        query_params['segmentation'] = query_params.get('segmentation', 'none')
        return self.get("results", **query_params).body

    def preview(self, **query_params):
        """Returns a streaming handle to this job's preview search results.

        Unlike :class:`splunklib.results.ResultsReader`, which requires a job to
        be finished to
        return any results, the ``preview`` method returns any results that have
        been generated so far, whether the job is running or not. The
        returned search results are the raw data from the server. Pass
        the handle returned to :class:`splunklib.results.ResultsReader` to get a
        nice, Pythonic iterator over objects, as in::

            import splunklib.client as client
            import splunklib.results as results
            service = client.connect(...)
            job = service.jobs.create("search * | head 5")
            rr = results.ResultsReader(job.preview())
            for result in rr:
                if isinstance(result, results.Message):
                    # Diagnostic messages may be returned in the results
                    print '%s: %s' % (result.type, result.message)
                elif isinstance(result, dict):
                    # Normal events are returned as dicts
                    print result
            if rr.is_preview:
                print "Preview of a running search job."
            else:
                print "Job is finished. Results are final."

        This method makes one roundtrip to the server, plus at most
        two more if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param query_params: Additional parameters (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/results_preview
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Fresults_preview>`_
            in the REST API documentation.
        :type query_params: ``dict``

        :return: The ``InputStream`` IO handle to this job's preview results.
        """
        query_params['segmentation'] = query_params.get('segmentation', 'none')
        return self.get("results_preview", **query_params).body

    def searchlog(self, **kwargs):
        """Returns a streaming handle to this job's search log.

        :param `kwargs`: Additional parameters (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/search.log
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Fsearch.log>`_
            in the REST API documentation.
        :type kwargs: ``dict``

        :return: The ``InputStream`` IO handle to this job's search log.
        """
        return self.get("search.log", **kwargs).body

    def set_priority(self, value):
        """Sets this job's search priority in the range of 0-10.

        Higher numbers indicate higher priority. Unless splunkd is
        running as *root*, you can only decrease the priority of a running job.

        :param `value`: The search priority.
        :type value: ``integer``

        :return: The :class:`Job`.
        """
        self.post('control', action="setpriority", priority=value)
        return self

    def summary(self, **kwargs):
        """Returns a streaming handle to this job's summary.

        :param `kwargs`: Additional parameters (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/summary
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Fsummary>`_
            in the REST API documentation.
        :type kwargs: ``dict``

        :return: The ``InputStream`` IO handle to this job's summary.
        """
        return self.get("summary", **kwargs).body

    def timeline(self, **kwargs):
        """Returns a streaming handle to this job's timeline results.

        :param `kwargs`: Additional timeline arguments (optional). For a list of valid
            parameters, see `GET search/jobs/{search_id}/timeline
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#GET_search.2Fjobs.2F.7Bsearch_id.7D.2Ftimeline>`_
            in the REST API documentation.
        :type kwargs: ``dict``

        :return: The ``InputStream`` IO handle to this job's timeline.
        """
        return self.get("timeline", **kwargs).body

    def touch(self):
        """Extends the expiration time of the search to the current time (now) plus
        the time-to-live (ttl) value.

        :return: The :class:`Job`.
        """
        self.post("control", action="touch")
        return self

    def set_ttl(self, value):
        """Set the job's time-to-live (ttl) value, which is the time before the
        search job expires and is still available.

        :param `value`: The ttl value, in seconds.
        :type value: ``integer``

        :return: The :class:`Job`.
        """
        self.post("control", action="setttl", ttl=value)
        return self

    def unpause(self):
        """Resumes the current search, if paused.

        :return: The :class:`Job`.
        """
        self.post("control", action="unpause")
        return self


class Jobs(Collection):
    """This class represents a collection of search jobs. Retrieve this
    collection using :meth:`Service.jobs`."""
    def __init__(self, service):
        Collection.__init__(self, service, PATH_JOBS, item=Job)
        # The count value to say list all the contents of this
        # Collection is 0, not -1 as it is on most.
        self.null_count = 0

    def _load_list(self, response):
        # Overridden because Job takes a sid instead of a path.
        entries = _load_atom_entries(response)
        if entries is None: return []
        entities = []
        for entry in entries:
            state = _parse_atom_entry(entry)
            entity = self.item(
                self.service,
                entry['content']['sid'],
                state=state)
            entities.append(entity)
        return entities

    def create(self, query, **kwargs):
        """ Creates a search using a search query and any additional parameters
        you provide.

        :param query: The search query.
        :type query: ``string``
        :param kwargs: Additiona parameters (optional). For a list of available
            parameters, see `Search job parameters
            <http://dev.splunk.com/view/SP-CAAAEE5#searchjobparams>`_
            on Splunk Developer Portal.
        :type kwargs: ``dict``

        :return: The :class:`Job`.
        """
        if kwargs.get("exec_mode", None) == "oneshot":
            raise TypeError("Cannot specify exec_mode=oneshot; use the oneshot method instead.")
        response = self.post(search=query, **kwargs)
        sid = _load_sid(response)
        return Job(self.service, sid)

    def export(self, query, **params):
        """Runs a search and immediately starts streaming preview events.
        This method returns a streaming handle to this job's events as an XML
        document from the server. To parse this stream into usable Python objects,
        pass the handle to :class:`splunklib.results.ResultsReader`::

            import splunklib.client as client
            import splunklib.results as results
            service = client.connect(...)
            rr = results.ResultsReader(service.jobs.export("search * | head 5"))
            for result in rr:
                if isinstance(result, results.Message):
                    # Diagnostic messages may be returned in the results
                    print '%s: %s' % (result.type, result.message)
                elif isinstance(result, dict):
                    # Normal events are returned as dicts
                    print result
            assert rr.is_preview == False

        Running an export search is more efficient as it streams the results
        directly to you, rather than having to write them out to disk and make
        them available later. As soon as results are ready, you will receive
        them.

        The ``export`` method makes a single roundtrip to the server (as opposed
        to two for :meth:`create` followed by :meth:`preview`), plus at most two
        more if the ``autologin`` field of :func:`connect` is set to ``True``.

        :raises `ValueError`: Raised for invalid queries.
        :param query: The search query.
        :type query: ``string``
        :param params: Additional arguments (optional). For a list of valid
            parameters, see `GET search/jobs/export
            <http://docs/Documentation/Splunk/latest/RESTAPI/RESTsearch#search.2Fjobs.2Fexport>`_
            in the REST API documentation.
        :type params: ``dict``

        :return: The ``InputStream`` IO handle to raw XML returned from the server.
        """
        if "exec_mode" in params:
            raise TypeError("Cannot specify an exec_mode to export.")
        params['segmentation'] = params.get('segmentation', 'none')
        return self.post(path_segment="export",
                         search=query,
                         **params).body

    def itemmeta(self):
        """There is no metadata available for class:``Jobs``.

        Any call to this method raises a class:``NotSupportedError``.

        :raises: class:``NotSupportedError``
        """
        raise NotSupportedError()

    def oneshot(self, query, **params):
        """Run a oneshot search and returns a streaming handle to the results.

        The ``InputStream`` object streams XML fragments from the server. To
        parse this stream into usable Python objects,
        pass the handle to :class:`splunklib.results.ResultsReader`::

            import splunklib.client as client
            import splunklib.results as results
            service = client.connect(...)
            rr = results.ResultsReader(service.jobs.oneshot("search * | head 5"))
            for result in rr:
                if isinstance(result, results.Message):
                    # Diagnostic messages may be returned in the results
                    print '%s: %s' % (result.type, result.message)
                elif isinstance(result, dict):
                    # Normal events are returned as dicts
                    print result
            assert rr.is_preview == False

        The ``oneshot`` method makes a single roundtrip to the server (as opposed
        to two for :meth:`create` followed by :meth:`results`), plus at most two more
        if the ``autologin`` field of :func:`connect` is set to ``True``.

        :raises ValueError: Raised for invalid queries.

        :param query: The search query.
        :type query: ``string``
        :param params: Additional arguments (optional):

            - "output_mode": Specifies the output format of the results (XML,
              JSON, or CSV).

            - "earliest_time": Specifies the earliest time in the time range to
              search. The time string can be a UTC time (with fractional seconds),
              a relative time specifier (to now), or a formatted time string.

            - "latest_time": Specifies the latest time in the time range to
              search. The time string can be a UTC time (with fractional seconds),
              a relative time specifier (to now), or a formatted time string.

            - "rf": Specifies one or more fields to add to the search.

        :type params: ``dict``

        :return: The ``InputStream`` IO handle to raw XML returned from the server.
        """
        if "exec_mode" in params:
            raise TypeError("Cannot specify an exec_mode to oneshot.")
        params['segmentation'] = params.get('segmentation', 'none')
        return self.post(search=query,
                         exec_mode="oneshot",
                         **params).body


class Loggers(Collection):
    """This class represents a collection of service logging categories.
    Retrieve this collection using :meth:`Service.loggers`."""
    def __init__(self, service):
        Collection.__init__(self, service, PATH_LOGGER)

    def itemmeta(self):
        """There is no metadata available for class:``Loggers``.

        Any call to this method raises a class:``NotSupportedError``.

        :raises: class:``NotSupportedError``
        """
        raise NotSupportedError()


class Message(Entity):
    def __init__(self, service, path, **kwargs):
        Entity.__init__(self, service, path, **kwargs)

    @property
    def value(self):
        """Returns the message value.

        :return: The message value.
        :rtype: ``string``
        """
        return self[self.name]


class ModularInputKind(Entity):
    """This class contains the different types of modular inputs. Retrieve this
    collection using :meth:`Service.modular_input_kinds`.
    """
    def __contains__(self, name):
        args = self.state.content['endpoints']['args']
        if name in args:
            return True
        else:
            return Entity.__contains__(self, name)

    def __getitem__(self, name):
        args = self.state.content['endpoint']['args']
        if name in args:
            return args['item']
        else:
            return Entity.__getitem__(self, name)

    @property
    def arguments(self):
        """A dictionary of all the arguments supported by this modular input kind.

        The keys in the dictionary are the names of the arguments. The values are
        another dictionary giving the metadata about that argument. The possible
        keys in that dictionary are ``"title"``, ``"description"``, ``"required_on_create``",
        ``"required_on_edit"``, ``"data_type"``. Each value is a string. It should be one
        of ``"true"`` or ``"false"`` for ``"required_on_create"`` and ``"required_on_edit"``,
        and one of ``"boolean"``, ``"string"``, or ``"number``" for ``"data_type"``.

        :return: A dictionary describing the arguments this modular input kind takes.
        :rtype: ``dict``
        """
        return self.state.content['endpoint']['args']

    def update(self, **kwargs):
        """Raises an error. Modular input kinds are read only."""
        raise IllegalOperationException("Modular input kinds cannot be updated via the REST API.")


class SavedSearch(Entity):
    """This class represents a saved search."""
    def __init__(self, service, path, **kwargs):
        Entity.__init__(self, service, path, **kwargs)

    def acknowledge(self):
        """Acknowledges the suppression of alerts from this saved search and
        resumes alerting.

        :return: The :class:`SavedSearch`.
        """
        self.post("acknowledge")
        return self

    @property
    def alert_count(self):
        """Returns the number of alerts fired by this saved search.

        :return: The number of alerts fired by this saved search.
        :rtype: ``integer``
        """
        return int(self._state.content.get('triggered_alert_count', 0))

    def dispatch(self, **kwargs):
        """Runs the saved search and returns the resulting search job.

        :param `kwargs`: Additional dispatch arguments (optional). For details,
                         see the `POST saved/searches/{name}/dispatch
                         <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsearch#POST_saved.2Fsearches.2F.7Bname.7D.2Fdispatch>`_
                         endpoint in the REST API documentation.
        :type kwargs: ``dict``
        :return: The :class:`Job`.
        """
        response = self.post("dispatch", **kwargs)
        sid = _load_sid(response)
        return Job(self.service, sid)

    @property
    def fired_alerts(self):
        """Returns the collection of fired alerts (a fired alert group)
        corresponding to this saved search's alerts.

        :raises IllegalOperationException: Raised when the search is not scheduled.

        :return: A collection of fired alerts.
        :rtype: :class:`AlertGroup`
        """
        if self['is_scheduled'] == '0':
            raise IllegalOperationException('Unscheduled saved searches have no alerts.')
        c = Collection(
            self.service,
            self.service._abspath(PATH_FIRED_ALERTS + self.name,
                                  owner=self._state.access.owner,
                                  app=self._state.access.app,
                                  sharing=self._state.access.sharing),
            item=AlertGroup)
        return c

    def history(self):
        """Returns a list of search jobs corresponding to this saved search.

        :return: A list of :class:`Job` objects.
        """
        response = self.get("history")
        entries = _load_atom_entries(response)
        if entries is None: return []
        jobs = []
        for entry in entries:
            job = Job(self.service, entry.title)
            jobs.append(job)
        return jobs

    def update(self, search=None, **kwargs):
        """Updates the server with any changes you've made to the current saved
        search along with any additional arguments you specify.

        :param `search`: The search query (optional).
        :type search: ``string``
        :param `kwargs`: Additional arguments (optional). For a list of available
            parameters, see `Saved search parameters
            <http://dev.splunk.com/view/SP-CAAAEE5#savedsearchparams>`_
            on Splunk Developer Portal.
        :type kwargs: ``dict``

        :return: The :class:`SavedSearch`.
        """
        # Updates to a saved search *require* that the search string be
        # passed, so we pass the current search string if a value wasn't
        # provided by the caller.
        if search is None: search = self.content.search
        Entity.update(self, search=search, **kwargs)
        return self

    def scheduled_times(self, earliest_time='now', latest_time='+1h'):
        """Returns the times when this search is scheduled to run.

        By default this method returns the times in the next hour. For different
        time ranges, set *earliest_time* and *latest_time*. For example,
        for all times in the last day use "earliest_time=-1d" and
        "latest_time=now".

        :param earliest_time: The earliest time.
        :type earliest_time: ``string``
        :param latest_time: The latest time.
        :type latest_time: ``string``

        :return: The list of search times.
        """
        response = self.get("scheduled_times",
                            earliest_time=earliest_time,
                            latest_time=latest_time)
        data = self._load_atom_entry(response)
        rec = _parse_atom_entry(data)
        times = [datetime.fromtimestamp(int(t))
                 for t in rec.content.scheduled_times]
        return times

    def suppress(self, expiration):
        """Skips any scheduled runs of this search in the next *expiration*
        number of seconds.

        :param expiration: The expiration period, in seconds.
        :type expiration: ``integer``

        :return: The :class:`SavedSearch`.
        """
        self.post("suppress", expiration=expiration)
        return self

    @property
    def suppressed(self):
        """Returns the number of seconds that this search is blocked from running
        (possibly 0).

        :return: The number of seconds.
        :rtype: ``integer``
        """
        r = self._run_action("suppress")
        if r.suppressed == "1":
            return int(r.expiration)
        else:
            return 0

    def unsuppress(self):
        """Cancels suppression and makes this search run as scheduled.

        :return: The :class:`SavedSearch`.
        """
        self.post("suppress", expiration="0")
        return self


class SavedSearches(Collection):
    """This class represents a collection of saved searches. Retrieve this
    collection using :meth:`Service.saved_searches`."""
    def __init__(self, service):
        Collection.__init__(
            self, service, PATH_SAVED_SEARCHES, item=SavedSearch)

    def create(self, name, search, **kwargs):
        """ Creates a saved search.

        :param name: The name for the saved search.
        :type name: ``string``
        :param search: The search query.
        :type search: ``string``
        :param kwargs: Additional arguments (optional). For a list of available
            parameters, see `Saved search parameters
            <http://dev.splunk.com/view/SP-CAAAEE5#savedsearchparams>`_
            on Splunk Developer Portal.
        :type kwargs: ``dict``
        :return: The :class:`SavedSearches` collection.
        """
        return Collection.create(self, name, search=search, **kwargs)


class Settings(Entity):
    """This class represents configuration settings for a Splunk service.
    Retrieve this collection using :meth:`Service.settings`."""
    def __init__(self, service, **kwargs):
        Entity.__init__(self, service, "/services/server/settings", **kwargs)

    # Updates on the settings endpoint are POSTed to server/settings/settings.
    def update(self, **kwargs):
        """Updates the settings on the server using the arguments you provide.

        :param kwargs: Additional arguments. For a list of valid arguments, see
            `POST server/settings/{name}
            <http://docs.splunk.com/Documentation/Splunk/latest/RESTAPI/RESTsystem#POST_server.2Fsettings.2F.7Bname.7D>`_
            in the REST API documentation.
        :type kwargs: ``dict``
        :return: The :class:`Settings` collection.
        """
        self.service.post("/services/server/settings/settings", **kwargs)
        return self


class User(Entity):
    """This class represents a Splunk user.
    """
    @property
    def role_entities(self):
        """Returns a list of roles assigned to this user.

        :return: The list of roles.
        :rtype: ``list``
        """
        return [self.service.roles[name] for name in self.content.roles]


# Splunk automatically lowercases new user names so we need to match that
# behavior here to ensure that the subsequent member lookup works correctly.
class Users(Collection):
    """This class represents the collection of Splunk users for this instance of
    Splunk. Retrieve this collection using :meth:`Service.users`.
    """
    def __init__(self, service):
        Collection.__init__(self, service, PATH_USERS, item=User)

    def __getitem__(self, key):
        return Collection.__getitem__(self, key.lower())

    def __contains__(self, name):
        return Collection.__contains__(self, name.lower())

    def create(self, username, password, roles, **params):
        """Creates a new user.

        This function makes two roundtrips to the server, plus at most
        two more if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param username: The username.
        :type username: ``string``
        :param password: The password.
        :type password: ``string``
        :param roles: A single role or list of roles for the user.
        :type roles: ``string`` or  ``list``
        :param params: Additional arguments (optional). For a list of available
            parameters, see `User authentication parameters
            <http://dev.splunk.com/view/SP-CAAAEJ6#userauthparams>`_
            on Splunk Developer Portal.
        :type params: ``dict``

        :return: The new user.
        :rtype: :class:`User`

        **Example**::

            import splunklib.client as client
            c = client.connect(...)
            users = c.users
            boris = users.create("boris", "securepassword", roles="user")
            hilda = users.create("hilda", "anotherpassword", roles=["user","power"])
        """
        if not isinstance(username, basestring):
            raise ValueError("Invalid username: %s" % str(username))
        username = username.lower()
        self.post(name=username, password=password, roles=roles, **params)
        # splunkd doesn't return the user in the POST response body,
        # so we have to make a second round trip to fetch it.
        response = self.get(username)
        entry = _load_atom(response, XNAME_ENTRY).entry
        state = _parse_atom_entry(entry)
        entity = self.item(
            self.service,
            urllib.unquote(state.links.alternate),
            state=state)
        return entity

    def delete(self, name):
        """ Deletes the user and returns the resulting collection of users.

        :param name: The name of the user to delete.
        :type name: ``string``

        :return:
        :rtype: :class:`Users`
        """
        return Collection.delete(self, name.lower())


class Role(Entity):
    """This class represents a user role.
    """
    def grant(self, *capabilities_to_grant):
        """Grants additional capabilities to this role.

        :param capabilities_to_grant: Zero or more capabilities to grant this
            role. For a list of capabilities, see
            `Capabilities <http://dev.splunk.com/view/SP-CAAAEJ6#capabilities>`_
            on Splunk Developer Portal.
        :type capabilities_to_grant: ``string`` or ``list``
        :return: The :class:`Role`.

        **Example**::

            service = client.connect(...)
            role = service.roles['somerole']
            role.grant('change_own_password', 'search')
        """
        possible_capabilities = self.service.capabilities
        for capability in capabilities_to_grant:
            if capability not in possible_capabilities:
                raise NoSuchCapability(capability)
        new_capabilities = self['capabilities'] + list(capabilities_to_grant)
        self.post(capabilities=new_capabilities)
        return self

    def revoke(self, *capabilities_to_revoke):
        """Revokes zero or more capabilities from this role.

        :param capabilities_to_revoke: Zero or more capabilities to grant this
            role. For a list of capabilities, see
            `Capabilities <http://dev.splunk.com/view/SP-CAAAEJ6#capabilities>`_
            on Splunk Developer Portal.
        :type capabilities_to_revoke: ``string`` or ``list``

        :return: The :class:`Role`.

        **Example**::

            service = client.connect(...)
            role = service.roles['somerole']
            role.revoke('change_own_password', 'search')
        """
        possible_capabilities = self.service.capabilities
        for capability in capabilities_to_revoke:
            if capability not in possible_capabilities:
                raise NoSuchCapability(capability)
        old_capabilities = self['capabilities']
        new_capabilities = []
        for c in old_capabilities:
            if c not in capabilities_to_revoke:
                new_capabilities.append(c)
        if new_capabilities == []:
            new_capabilities = '' # Empty lists don't get passed in the body, so we have to force an empty argument.
        self.post(capabilities=new_capabilities)
        return self


class Roles(Collection):
    """This class represents the collection of roles in the Splunk instance.
    Retrieve this collection using :meth:`Service.roles`."""
    def __init__(self, service):
        return Collection.__init__(self, service, PATH_ROLES, item=Role)

    def __getitem__(self, key):
        return Collection.__getitem__(self, key.lower())

    def __contains__(self, name):
        return Collection.__contains__(self, name.lower())

    def create(self, name, **params):
        """Creates a new role.

        This function makes two roundtrips to the server, plus at most
        two more if
        the ``autologin`` field of :func:`connect` is set to ``True``.

        :param name: Name for the role.
        :type name: ``string``
        :param params: Additional arguments (optional). For a list of available
            parameters, see `Roles parameters
            <http://dev.splunk.com/view/SP-CAAAEJ6#rolesparams>`_
            on Splunk Developer Portal.
        :type params: ``dict``

        :return: The new role.
        :rtype: :class:`Role`

        **Example**::

            import splunklib.client as client
            c = client.connect(...)
            roles = c.roles
            paltry = roles.create("paltry", imported_roles="user", defaultApp="search")
        """
        if not isinstance(name, basestring):
            raise ValueError("Invalid role name: %s" % str(name))
        name = name.lower()
        self.post(name=name, **params)
        # splunkd doesn't return the user in the POST response body,
        # so we have to make a second round trip to fetch it.
        response = self.get(name)
        entry = _load_atom(response, XNAME_ENTRY).entry
        state = _parse_atom_entry(entry)
        entity = self.item(
            self.service,
            urllib.unquote(state.links.alternate),
            state=state)
        return entity

    def delete(self, name):
        """ Deletes the role and returns the resulting collection of roles.

        :param name: The name of the role to delete.
        :type name: ``string``

        :rtype: The :class:`Roles`
        """
        return Collection.delete(self, name.lower())


class Application(Entity):
    """Represents a locally-installed Splunk app."""
    @property
    def setupInfo(self):
        """Returns the setup information for the app.

        :return: The setup information.
        """
        return self.content.get('eai:setup', None)

    def package(self):
        """ Creates a compressed package of the app for archiving."""
        return self._run_action("package")

    def updateInfo(self):
        """Returns any update information that is available for the app."""
        return self._run_action("update")
                                                                                                                                                                                                                                                                                                                                                                                                                            humanize/bin/splunklib/data.py                                                                      000644  000765  000000  00000020110 12674041006 017703  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""The **splunklib.data** module reads the responses from splunkd in Atom Feed 
format, which is the format used by most of the REST API.
"""

from xml.etree.ElementTree import XML

__all__ = ["load"]

# LNAME refers to element names without namespaces; XNAME is the same
# name, but with an XML namespace.
LNAME_DICT = "dict"
LNAME_ITEM = "item"
LNAME_KEY = "key"
LNAME_LIST = "list"

XNAMEF_REST = "{http://dev.splunk.com/ns/rest}%s"
XNAME_DICT = XNAMEF_REST % LNAME_DICT
XNAME_ITEM = XNAMEF_REST % LNAME_ITEM
XNAME_KEY = XNAMEF_REST % LNAME_KEY
XNAME_LIST = XNAMEF_REST % LNAME_LIST

# Some responses don't use namespaces (eg: search/parse) so we look for
# both the extended and local versions of the following names.

def isdict(name):
    return name == XNAME_DICT or name == LNAME_DICT

def isitem(name):
    return name == XNAME_ITEM or name == LNAME_ITEM

def iskey(name):
    return name == XNAME_KEY or name == LNAME_KEY

def islist(name):
    return name == XNAME_LIST or name == LNAME_LIST

def hasattrs(element):
    return len(element.attrib) > 0

def localname(xname):
    rcurly = xname.find('}')
    return xname if rcurly == -1 else xname[rcurly+1:]

def load(text, match=None):
    """This function reads a string that contains the XML of an Atom Feed, then 
    returns the 
    data in a native Python structure (a ``dict`` or ``list``). If you also 
    provide a tag name or path to match, only the matching sub-elements are 
    loaded.

    :param text: The XML text to load.
    :type text: ``string``
    :param match: A tag name or path to match (optional).
    :type match: ``string``
    """
    if text is None: return None
    text = text.strip()
    if len(text) == 0: return None
    nametable = {
        'namespaces': [],
        'names': {}
    }
    root = XML(text)
    items = [root] if match is None else root.findall(match)
    count = len(items)
    if count == 0: 
        return None
    elif count == 1: 
        return load_root(items[0], nametable)
    else:
        return [load_root(item, nametable) for item in items]

# Load the attributes of the given element.
def load_attrs(element):
    if not hasattrs(element): return None
    attrs = record()
    for key, value in element.attrib.iteritems(): 
        attrs[key] = value
    return attrs

# Parse a <dict> element and return a Python dict
def load_dict(element, nametable = None):
    value = record()
    children = list(element)
    for child in children:
        assert iskey(child.tag)
        name = child.attrib["name"]
        value[name] = load_value(child, nametable)
    return value

# Loads the given elements attrs & value into single merged dict.
def load_elem(element, nametable=None):
    name = localname(element.tag)
    attrs = load_attrs(element)
    value = load_value(element, nametable)
    if attrs is None: return name, value
    if value is None: return name, attrs
    # If value is simple, merge into attrs dict using special key
    if isinstance(value, str):
        attrs["$text"] = value
        return name, attrs
    # Both attrs & value are complex, so merge the two dicts, resolving collisions.
    collision_keys = []
    for key, val in attrs.iteritems():
        if key in value and key in collision_keys:
            value[key].append(val)
        elif key in value and key not in collision_keys:
            value[key] = [value[key], val]
            collision_keys.append(key)
        else:
            value[key] = val
    return name, value

# Parse a <list> element and return a Python list
def load_list(element, nametable=None):
    assert islist(element.tag)
    value = []
    children = list(element)
    for child in children:
        assert isitem(child.tag)
        value.append(load_value(child, nametable))
    return value

# Load the given root element.
def load_root(element, nametable=None):
    tag = element.tag
    if isdict(tag): return load_dict(element, nametable)
    if islist(tag): return load_list(element, nametable)
    k, v = load_elem(element, nametable)
    return Record.fromkv(k, v)

# Load the children of the given element.
def load_value(element, nametable=None):
    children = list(element)
    count = len(children)

    # No children, assume a simple text value
    if count == 0:
        text = element.text
        if text is None: 
            return None
        text = text.strip()
        if len(text) == 0: 
            return None
        return text

    # Look for the special case of a single well-known structure
    if count == 1:
        child = children[0]
        tag = child.tag
        if isdict(tag): return load_dict(child, nametable)
        if islist(tag): return load_list(child, nametable)

    value = record()
    for child in children:
        name, item = load_elem(child, nametable)
        # If we have seen this name before, promote the value to a list
        if value.has_key(name):
            current = value[name]
            if not isinstance(current, list): 
                value[name] = [current]
            value[name].append(item)
        else:
            value[name] = item

    return value

# A generic utility that enables "dot" access to dicts
class Record(dict):
    """This generic utility class enables dot access to members of a Python 
    dictionary.

    Any key that is also a valid Python identifier can be retrieved as a field. 
    So, for an instance of ``Record`` called ``r``, ``r.key`` is equivalent to 
    ``r['key']``. A key such as ``invalid-key`` or ``invalid.key`` cannot be 
    retrieved as a field, because ``-`` and ``.`` are not allowed in 
    identifiers.

    Keys of the form ``a.b.c`` are very natural to write in Python as fields. If 
    a group of keys shares a prefix ending in ``.``, you can retrieve keys as a 
    nested dictionary by calling only the prefix. For example, if ``r`` contains
    keys ``'foo'``, ``'bar.baz'``, and ``'bar.qux'``, ``r.bar`` returns a record
    with the keys ``baz`` and ``qux``. If a key contains multiple ``.``, each 
    one is placed into a nested dictionary, so you can write ``r.bar.qux`` or 
    ``r['bar.qux']`` interchangeably.
    """
    sep = '.'

    def __call__(self, *args):
        if len(args) == 0: return self
        return Record((key, self[key]) for key in args)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError: 
            raise AttributeError(name)

    def __delattr__(self, name):
        del self[name]

    def __setattr__(self, name, value):
        self[name] = value

    @staticmethod
    def fromkv(k, v):
        result = record()
        result[k] = v
        return result

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        key += self.sep
        result = record()
        for k,v in self.iteritems():
            if not k.startswith(key):
                continue
            suffix = k[len(key):]
            if '.' in suffix:
                ks = suffix.split(self.sep)
                z = result
                for x in ks[:-1]:
                    if x not in z:
                        z[x] = record()
                    z = z[x]
                z[ks[-1]] = v
            else:
                result[suffix] = v
        if len(result) == 0:
            raise KeyError("No key or prefix: %s" % key)
        return result
    

def record(value=None): 
    """This function returns a :class:`Record` instance constructed with an 
    initial value that you provide.
    
    :param `value`: An initial record value.
    :type `value`: ``dict``
    """
    if value is None: value = {}
    return Record(value)

                                                                                                                                                                                                                                                                                                                                                                                                                                                        humanize/bin/splunklib/modularinput/                                                                000755  000765  000000  00000000000 12674041006 021151  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/splunklib/ordereddict.py                                                               000644  000765  000000  00000010177 12674041006 021276  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin


class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other
                                                                                                                                                                                                                                                                                                                                                                                                 humanize/bin/splunklib/results.py                                                                   000644  000765  000000  00000024670 12674041006 020512  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""The **splunklib.results** module provides a streaming XML reader for Splunk
search results.

Splunk search results can be returned in a variety of formats including XML,
JSON, and CSV. To make it easier to stream search results in XML format, they
are returned as a stream of XML *fragments*, not as a single XML document. This
module supports incrementally reading one result record at a time from such a
result stream. This module also provides a friendly iterator-based interface for
accessing search results while avoiding buffering the result set, which can be
very large.

To use the reader, instantiate :class:`ResultsReader` on a search result stream
as follows:::

    reader = ResultsReader(result_stream)
    for item in reader:
        print(item)
    print "Results are a preview: %s" % reader.is_preview
"""

try:
    import xml.etree.cElementTree as et
except:
    import xml.etree.ElementTree as et

try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

__all__ = [
    "ResultsReader",
    "Message"
]

class Message(object):
    """This class represents informational messages that Splunk interleaves in the results stream.

    ``Message`` takes two arguments: a string giving the message type (e.g., "DEBUG"), and
    a string giving the message itself.

    **Example**::

        m = Message("DEBUG", "There's something in that variable...")
    """
    def __init__(self, type_, message):
        self.type = type_
        self.message = message

    def __repr__(self):
        return "%s: %s" % (self.type, self.message)

    def __eq__(self, other):
        return (self.type, self.message) == (other.type, other.message)

    def __hash__(self):
        return hash((self.type, self.message))

class _ConcatenatedStream(object):
    """Lazily concatenate zero or more streams into a stream.

    As you read from the concatenated stream, you get characters from
    each stream passed to ``_ConcatenatedStream``, in order.

    **Example**::

        from StringIO import StringIO
        s = _ConcatenatedStream(StringIO("abc"), StringIO("def"))
        assert s.read() == "abcdef"
    """
    def __init__(self, *streams):
        self.streams = list(streams)

    def read(self, n=None):
        """Read at most *n* characters from this stream.

        If *n* is ``None``, return all available characters.
        """
        response = ""
        while len(self.streams) > 0 and (n is None or n > 0):
            txt = self.streams[0].read(n)
            response += txt
            if n is not None:
                n -= len(txt)
            if n > 0 or n is None:
                del self.streams[0]
        return response

class _XMLDTDFilter(object):
    """Lazily remove all XML DTDs from a stream.

    All substrings matching the regular expression <?[^>]*> are
    removed in their entirety from the stream. No regular expressions
    are used, however, so everything still streams properly.

    **Example**::

        from StringIO import StringIO
        s = _XMLDTDFilter("<?xml abcd><element><?xml ...></element>")
        assert s.read() == "<element></element>"
    """
    def __init__(self, stream):
        self.stream = stream

    def read(self, n=None):
        """Read at most *n* characters from this stream.

        If *n* is ``None``, return all available characters.
        """
        response = ""
        while n is None or n > 0:
            c = self.stream.read(1)
            if c == "":
                break
            elif c == "<":
                c += self.stream.read(1)
                if c == "<?":
                    while True:
                        q = self.stream.read(1)
                        if q == ">":
                            break
                else:
                    response += c
                    if n is not None:
                        n -= len(c)
            else:
                response += c
                if n is not None:
                    n -= 1
        return response

class ResultsReader(object):
    """This class returns dictionaries and Splunk messages from an XML results
    stream.

    ``ResultsReader`` is iterable, and returns a ``dict`` for results, or a
    :class:`Message` object for Splunk messages. This class has one field,
    ``is_preview``, which is ``True`` when the results are a preview from a
    running search, or ``False`` when the results are from a completed search.

    This function has no network activity other than what is implicit in the
    stream it operates on.

    :param `stream`: The stream to read from (any object that supports
        ``.read()``).

    **Example**::

        import results
        response = ... # the body of an HTTP response
        reader = results.ResultsReader(response)
        for result in reader:
            if isinstance(result, dict):
                print "Result: %s" % result
            elif isinstance(result, results.Message):
                print "Message: %s" % result
        print "is_preview = %s " % reader.is_preview
    """
    # Be sure to update the docstrings of client.Jobs.oneshot,
    # client.Job.results_preview and client.Job.results to match any
    # changes made to ResultsReader.
    #
    # This wouldn't be a class, just the _parse_results function below,
    # except that you cannot get the current generator inside the
    # function creating that generator. Thus it's all wrapped up for
    # the sake of one field.
    def __init__(self, stream):
        # The search/jobs/exports endpoint, when run with
        # earliest_time=rt and latest_time=rt streams a sequence of
        # XML documents, each containing a result, as opposed to one
        # results element containing lots of results. Python's XML
        # parsers are broken, and instead of reading one full document
        # and returning the stream that follows untouched, they
        # destroy the stream and throw an error. To get around this,
        # we remove all the DTD definitions inline, then wrap the
        # fragments in a fiction <doc> element to make the parser happy.
        stream = _XMLDTDFilter(stream)
        stream = _ConcatenatedStream(StringIO("<doc>"), stream, StringIO("</doc>"))
        self.is_preview = None
        self._gen = self._parse_results(stream)

    def __iter__(self):
        return self

    def next(self):
        return self._gen.next()

    def _parse_results(self, stream):
        """Parse results and messages out of *stream*."""
        result = None
        values = None
        try:
            for event, elem in et.iterparse(stream, events=('start', 'end')):
                if elem.tag == 'results' and event == 'start':
                    # The wrapper element is a <results preview="0|1">. We
                    # don't care about it except to tell is whether these
                    # are preview results, or the final results from the
                    # search.
                    is_preview = elem.attrib['preview'] == '1'
                    self.is_preview = is_preview
                if elem.tag == 'result':
                    if event == 'start':
                        result = OrderedDict()
                    elif event == 'end':
                        yield result
                        result = None
                        elem.clear()

                elif elem.tag == 'field' and result is not None:
                    # We need the 'result is not None' check because
                    # 'field' is also the element name in the <meta>
                    # header that gives field order, which is not what we
                    # want at all.
                    if event == 'start':
                        values = []
                    elif event == 'end':
                        field_name = elem.attrib['k'].encode('utf8')
                        if len(values) == 1:
                            result[field_name] = values[0]
                        else:
                            result[field_name] = values
                        # Calling .clear() is necessary to let the
                        # element be garbage collected. Otherwise
                        # arbitrarily large results sets will use
                        # arbitrarily large memory intead of
                        # streaming.
                        elem.clear()

                elif elem.tag in ('text', 'v') and event == 'end':
                    try:
                        text = "".join(elem.itertext())
                    except AttributeError:
                        # Assume we're running in Python < 2.7, before itertext() was added
                        # So we'll define it here

                        def __itertext(self):
                          tag = self.tag
                          if not isinstance(tag, basestring) and tag is not None:
                              return
                          if self.text:
                              yield self.text
                          for e in self:
                              for s in __itertext(e):
                                  yield s
                              if e.tail:
                                  yield e.tail

                        text = "".join(__itertext(elem))
                    values.append(text.encode('utf8'))
                    elem.clear()

                elif elem.tag == 'msg':
                    if event == 'start':
                        msg_type = elem.attrib['type']
                    elif event == 'end':
                        text = elem.text if elem.text is not None else ""
                        yield Message(msg_type, text.encode('utf8'))
                        elem.clear()
        except SyntaxError as pe:
            # This is here to handle the same incorrect return from
            # splunk that is described in __init__.
            if 'no element found' in pe.msg:
                return
            else:
                raise




                                                                        humanize/bin/splunklib/searchcommands/                                                              000755  000765  000000  00000000000 12674546615 021435  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/splunklib/searchcommands/__init__.py                                                   000644  000765  000000  00000013623 12674041006 023533  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""

.. topic:: Design Notes

  1. Commands are constrained to this ABNF grammar::

        command       = command-name *[wsp option] *[wsp [dquote] field-name [dquote]]
        command-name  = alpha *( alpha / digit )
        option        = option-name [wsp] "=" [wsp] option-value
        option-name   = alpha *( alpha / digit / "_" )
        option-value  = word / quoted-string
        word          = 1*( %01-%08 / %0B / %0C / %0E-1F / %21 / %23-%FF ) ; Any character but DQUOTE and WSP
        quoted-string = dquote *( word / wsp / "\" dquote / dquote dquote ) dquote
        field-name    = ( "_" / alpha ) *( alpha / digit / "_" / "." / "-" )

     It does not show that :code:`field-name` values may be comma-separated. This is because Splunk strips commas from
    the command line. A search command will never see them.

  2. Search commands targeting versions of Splunk prior to 6.3 must be statically configured as follows:

     .. code-block:: text
        :linenos:

        [command_name]
        filename = command_name.py
        supports_getinfo = true
        supports_rawargs = true

     No other static configuration is required or expected and may interfere with command execution.

  3. Commands support dynamic probing for settings.

     Splunk probes for settings dynamically when :code:`supports_getinfo=true`.
     You must add this line to the commands.conf stanza for each of your search
     commands.

  4. Commands do not support parsed arguments on the command line.

     Splunk parses arguments when :code:`supports_rawargs=false`. The
     :code:`SearchCommand` class sets this value unconditionally. You cannot
     override it.

     **Rationale**

     Splunk parses arguments by stripping quotes, nothing more. This may be useful
     in some cases, but doesn't work well with our chosen grammar.

  5. Commands consume input headers.

     An input header is provided by Splunk when :code:`enableheader=true`. The
     :class:`SearchCommand` class sets this value unconditionally. You cannot
     override it.

  6. Commands produce an output messages header.

     Splunk expects a command to produce an output messages header when
     :code:`outputheader=true`. The :class:`SearchCommand` class sets this value
     unconditionally. You cannot override it.

  7. Commands support multi-value fields.

     Multi-value fields are provided and consumed by Splunk when
     :code:`supports_multivalue=true`. This value is fixed. You cannot override
     it.

  8. This module represents all fields on the output stream in multi-value
     format.

     Splunk recognizes two kinds of data: :code:`value` and :code:`list(value)`.
     The multi-value format represents these data in field pairs. Given field
     :code:`name` the multi-value format calls for the creation of this pair of
     fields.

     ================= =========================================================
     Field name         Field data
     ================= =========================================================
     :code:`name`      Value or text from which a list of values was derived.

     :code:`__mv_name` Empty, if :code:`field` represents a :code:`value`;
                       otherwise, an encoded :code:`list(value)`. Values in the
                       list are wrapped in dollar signs ($) and separated by
                       semi-colons (;). Dollar signs ($) within a value are
                       represented by a pair of dollar signs ($$).
     ================= =========================================================

     Serializing data in this format enables streaming and reduces a command's
     memory footprint at the cost of one extra byte of data per field per record
     and a small amount of extra processing time by the next command in the
     pipeline.

  9. A :class:`ReportingCommand` must override :meth:`~ReportingCommand.reduce`
     and may override :meth:`~ReportingCommand.map`. Map/reduce commands on the
     Splunk processing pipeline are distinguished as this example illustrates.

     **Splunk command**

     .. code-block:: text

         sum total=total_date_hour date_hour

     **Map command line**

     .. code-block:: text

        sum __GETINFO__ __map__ total=total_date_hour date_hour
        sum __EXECUTE__ __map__ total=total_date_hour date_hour

     **Reduce command line**

     .. code-block:: text

        sum __GETINFO__ total=total_date_hour date_hour
        sum __EXECUTE__ total=total_date_hour date_hour

     The :code:`__map__` argument is introduced by
     :meth:`ReportingCommand._execute`. Search command authors cannot influence
     the contents of the command line in this release.

.. topic:: References

  1. `Search command style guide <http://docs.splunk.com/Documentation/Splunk/6.0/Search/Searchcommandstyleguide>`_

  2. `Commands.conf.spec <http://docs.splunk.com/Documentation/Splunk/5.0.5/Admin/Commandsconf>`_

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from .environment import *
from .decorators import *
from .validators import *

from .generating_command import GeneratingCommand
from .streaming_command import StreamingCommand
from .eventing_command import EventingCommand
from .reporting_command import ReportingCommand

from .external_search_command import execute, ExternalSearchCommand
from .search_command import dispatch, SearchMetric
                                                                                                             humanize/bin/splunklib/searchcommands/decorators.py                                                 000644  000765  000000  00000036255 12674041006 024147  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict  # must be python 2.7
from inspect import getmembers, isclass, isfunction
from itertools import imap

from .internals import ConfigurationSettingsType, json_encode_string
from .validators import OptionName


class Configuration(object):
    """ Defines the configuration settings for a search command.

    Documents, validates, and ensures that only relevant configuration settings are applied. Adds a :code:`name` class
    variable to search command classes that don't have one. The :code:`name` is derived from the name of the class.
    By convention command class names end with the word "Command". To derive :code:`name` the word "Command" is removed
    from the end of the class name and then converted to lower case for conformance with the `Search command style guide
    <http://docs.splunk.com/Documentation/Splunk/latest/Search/Searchcommandstyleguide>`_

    """
    def __init__(self, o=None, **kwargs):
        #
        # The o argument enables the configuration decorator to be used with or without parentheses. For example, it
        # enables you to write code that looks like this:
        #
        #   @Configuration
        #   class Foo(SearchCommand):
        #       ...
        #
        #   @Configuration()
        #   class Bar(SearchCommand):
        #       ...
        #
        # Without the o argument, the Python compiler will complain about the first form. With the o argument, both
        # forms work. The first form provides a value for o: Foo. The second form does does not provide a value for o.
        # The class or method decorated is not passed to the constructor. A value of None is passed instead.
        #
        self.settings = kwargs

    def __call__(self, o):

        if isfunction(o):
            # We must wait to finalize configuration as the class containing this function is under construction
            # at the time this call to decorate a member function. This will be handled in the call to
            # o.ConfigurationSettings.fix_up(o) in the elif clause of this code block.
            o._settings = self.settings
        elif isclass(o):

            # Set command name

            name = o.__name__
            if name.endswith(b'Command'):
                name = name[:-len(b'Command')]
            o.name = unicode(name.lower())

            # Construct ConfigurationSettings instance for the command class

            o.ConfigurationSettings = ConfigurationSettingsType(
                module=o.__module__ + b'.' + o.__name__,
                name=b'ConfigurationSettings',
                bases=(o.ConfigurationSettings,))

            ConfigurationSetting.fix_up(o.ConfigurationSettings, self.settings)
            o.ConfigurationSettings.fix_up(o)
            Option.fix_up(o)
        else:
            raise TypeError('Incorrect usage: Configuration decorator applied to {0}'.format(type(o), o.__name__))

        return o


class ConfigurationSetting(property):
    """ Generates a :class:`property` representing the named configuration setting

    This is a convenience function designed to reduce the amount of boiler-plate code you must write; most notably for
    property setters.

    :param name: Configuration setting name.
    :type name: str or unicode

    :param doc: A documentation string.
    :type doc: bytes, unicode or NoneType

    :param readonly: If true, specifies that the configuration setting is fixed.
    :type name: bool or NoneType

    :param value: Configuration setting value.

    :return: A :class:`property` instance representing the configuration setting.
    :rtype: property

    """
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, name=None, readonly=None, value=None):
        property.__init__(self, fget=fget, fset=fset, fdel=fdel, doc=doc)
        self._readonly = readonly
        self._value = value
        self._name = name

    def __call__(self, function):
        return self.getter(function)

    def deleter(self, function):
        return self._copy_extra_attributes(property.deleter(self, function))

    def getter(self, function):
        return self._copy_extra_attributes(property.getter(self, function))

    def setter(self, function):
        return self._copy_extra_attributes(property.setter(self, function))

    @staticmethod
    def fix_up(cls, values):

        is_configuration_setting = lambda attribute: isinstance(attribute, ConfigurationSetting)
        definitions = getmembers(cls, is_configuration_setting)
        i = 0

        for name, setting in definitions:

            if setting._name is None:
                setting._name = name = unicode(name)
            else:
                name = setting._name

            validate, specification = setting._get_specification()
            backing_field_name = '_' + name

            if setting.fget is None and setting.fset is None and setting.fdel is None:

                value = setting._value

                if setting._readonly or value is not None:
                    validate(specification, name, value)

                def fget(bfn, value):
                    return lambda this: getattr(this, bfn, value)

                setting = setting.getter(fget(backing_field_name, value))

                if not setting._readonly:

                    def fset(bfn, validate, specification, name):
                        return lambda this, value: setattr(this, bfn, validate(specification, name, value))

                    setting = setting.setter(fset(backing_field_name, validate, specification, name))

                setattr(cls, name, setting)

            def is_supported_by_protocol(supporting_protocols):

                def is_supported_by_protocol(version):
                    return version in supporting_protocols

                return is_supported_by_protocol

            del setting._name, setting._value, setting._readonly

            setting.is_supported_by_protocol = is_supported_by_protocol(specification.supporting_protocols)
            setting.supporting_protocols = specification.supporting_protocols
            setting.backing_field_name = backing_field_name
            definitions[i] = setting
            setting.name = name

            i += 1

            try:
                value = values[name]
            except KeyError:
                continue

            if setting.fset is None:
                raise ValueError('The value of configuration setting {} is fixed'.format(name))

            setattr(cls, backing_field_name, validate(specification, name, value))
            del values[name]

        if len(values) > 0:
            settings = sorted(list(values.iteritems()))
            settings = imap(lambda (n, v): '{}={}'.format(n, repr(v)), settings)
            raise AttributeError('Inapplicable configuration settings: ' + ', '.join(settings))

        cls.configuration_setting_definitions = definitions

    def _copy_extra_attributes(self, other):
        other._readonly = self._readonly
        other._value = self._value
        other._name = self._name
        return other

    def _get_specification(self):

        name = self._name

        try:
            specification = ConfigurationSettingsType.specification_matrix[name]
        except KeyError:
            raise AttributeError('Unknown configuration setting: {}={}'.format(name, repr(self._value)))

        return ConfigurationSettingsType.validate_configuration_setting, specification


class Option(property):
    """ Represents a search command option.

    Required options must be specified on the search command line.

    **Example:**

    Short form (recommended). When you are satisfied with built-in or custom validation behaviors.

    .. code-block:: python
        :linenos:
        from splunklib.searchcommands.decorators import Option
        from splunklib.searchcommands.validators import Fieldname

        total = Option(
            doc=''' **Syntax:** **total=***<fieldname>*
            **Description:** Name of the field that will hold the computed
            sum''',
            require=True, validate=Fieldname())

    **Example:**

    Long form. Useful when you wish to manage the option value and its deleter/getter/setter side-effects yourself. You
    must provide a getter and a setter. If your :code:`Option` requires `destruction <http://goo.gl/4VSm1c>`_ you must
    also provide a deleter. You must be prepared to accept a value of :const:`None` which indicates that your
    :code:`Option` is unset.

    .. code-block:: python
        :linenos:
        from splunklib.searchcommands import Option

        @Option()
        def logging_configuration(self):
            \""" **Syntax:** logging_configuration=<path>
            **Description:** Loads an alternative logging configuration file for a command invocation. The logging
            configuration file must be in Python ConfigParser-format. The *<path>* name and all path names specified in
            configuration are relative to the app root directory.

            \"""
            return self._logging_configuration

        @logging_configuration.setter
        def logging_configuration(self, value):
            if value is not None
                logging.configure(value)
                self._logging_configuration = value

        def __init__(self)
            self._logging_configuration = None

    """
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, name=None, default=None, require=None, validate=None):
        property.__init__(self, fget, fset, fdel, doc)
        self.name = name
        self.default = default
        self.validate = validate
        self.require = bool(require)

    def __call__(self, function):
        return self.getter(function)

    # region Methods

    def deleter(self, function):
        return self._copy_extra_attributes(property.deleter(self, function))

    def getter(self, function):
        return self._copy_extra_attributes(property.getter(self, function))

    def setter(self, function):
        return self._copy_extra_attributes(property.setter(self, function))

    @classmethod
    def fix_up(cls, command_class):

        is_option = lambda attribute: isinstance(attribute, Option)
        definitions = getmembers(command_class, is_option)
        validate_option_name = OptionName()
        i = 0

        for name, option in definitions:

            if option.name is None:
                option.name = name  # no validation required
            else:
                validate_option_name(option.name)

            if option.fget is None and option.fset is None and option.fdel is None:
                backing_field_name = '_' + name

                def fget(bfn):
                    return lambda this: getattr(this, bfn, None)

                option = option.getter(fget(backing_field_name))

                def fset(bfn, validate):
                    if validate is None:
                        return lambda this, value: setattr(this, bfn, value)
                    return lambda this, value: setattr(this, bfn, validate(value))

                option = option.setter(fset(backing_field_name, option.validate))
                setattr(command_class, name, option)

            elif option.validate is not None:

                def fset(function, validate):
                    return lambda this, value: function(this, validate(value))

                option = option.setter(fset(option.fset, option.validate))
                setattr(command_class, name, option)

            definitions[i] = name, option
            i += 1

        command_class.option_definitions = definitions

    def _copy_extra_attributes(self, other):
        other.name = self.name
        other.default = self.default
        other.require = self.require
        other.validate = self.validate
        return other

    # endregion

    # region Types

    class Item(object):
        """ Presents an instance/class view over a search command `Option`.

        This class is used by SearchCommand.process to parse and report on option values.

        """
        def __init__(self, command, option):
            self._command = command
            self._option = option
            self._is_set = False
            validator = self.validator
            self._format = unicode if validator is None else validator.format

        def __repr__(self):
            return '(' + repr(self.name) + ', ' + repr(self._format(self.value)) + ')'

        def __str__(self):
            value = self.value
            value = 'None' if value is None else json_encode_string(self._format(value))
            return self.name + '=' + value

        # region Properties

        @property
        def is_required(self):
            return bool(self._option.require)

        @property
        def is_set(self):
            """ Indicates whether an option value was provided as argument.

            """
            return self._is_set

        @property
        def name(self):
            return self._option.name

        @property
        def validator(self):
            return self._option.validate

        @property
        def value(self):
            return self._option.__get__(self._command)

        @value.setter
        def value(self, value):
            self._option.__set__(self._command, value)
            self._is_set = True

        # endregion

        # region Methods

        def reset(self):
            self._option.__set__(self._command, self._option.default)
            self._is_set = False

        pass
        # endregion

    class View(OrderedDict):
        """ Presents an ordered dictionary view of the set of :class:`Option` arguments to a search command.

        This class is used by SearchCommand.process to parse and report on option values.

        """
        def __init__(self, command):
            definitions = type(command).option_definitions
            item_class = Option.Item
            OrderedDict.__init__(self, imap(lambda (name, option): (option.name, item_class(command, option)), definitions))

        def __repr__(self):
            text = 'Option.View([' + ','.join(imap(lambda item: repr(item), self.itervalues())) + '])'
            return text

        def __str__(self):
            text = ' '.join([str(item) for item in self.itervalues() if item.is_set])
            return text

        # region Methods

        def get_missing(self):
            missing = [item.name for item in self.itervalues() if item.is_required and not item.is_set]
            return missing if len(missing) > 0 else None

        def reset(self):
            for value in self.itervalues():
                value.reset()

        pass
        # endregion

    pass
    # endregion


__all__ = ['Configuration', 'Option']
                                                                                                                                                                                                                                                                                                                                                   humanize/bin/splunklib/searchcommands/environment.py                                                000644  000765  000000  00000010764 12674041006 024343  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, root, StreamHandler
from logging.config import fileConfig
from os import chdir, environ, getcwdu, path

import sys


def configure_logging(logger_name, filename=None):
    """ Configure logging and return the named logger and the location of the logging configuration file loaded.

    This function expects a Splunk app directory structure::

        <app-root>
            bin
                ...
            default
                ...
            local
                ...

    This function looks for a logging configuration file at each of these locations, loading the first, if any,
    logging configuration file that it finds::

        local/{name}.logging.conf
        default/{name}.logging.conf
        local/logging.conf
        default/logging.conf

    The current working directory is set to *<app-root>* before the logging configuration file is loaded. Hence, paths
    in the logging configuration file are relative to *<app-root>*. The current directory is reset before return.

    You may short circuit the search for a logging configuration file by providing an alternative file location in
    `path`. Logging configuration files must be in `ConfigParser format`_.

    #Arguments:

    :param logger_name: Logger name
    :type logger_name: bytes, unicode

    :param filename: Location of an alternative logging configuration file or `None`.
    :type filename: bytes, unicode or NoneType

    :returns: The named logger and the location of the logging configuration file loaded.
    :rtype: tuple

    .. _ConfigParser format: http://goo.gl/K6edZ8

    """
    if filename is None:
        if logger_name is None:
            probing_paths = [path.join('local', 'logging.conf'), path.join('default', 'logging.conf')]
        else:
            probing_paths = [
                path.join('local', logger_name + '.logging.conf'),
                path.join('default', logger_name + '.logging.conf'),
                path.join('local', 'logging.conf'),
                path.join('default', 'logging.conf')]
        for relative_path in probing_paths:
            configuration_file = path.join(app_root, relative_path)
            if path.exists(configuration_file):
                filename = configuration_file
                break
    elif not path.isabs(filename):
        found = False
        for conf in 'local', 'default':
            configuration_file = path.join(app_root, conf, filename)
            if path.exists(configuration_file):
                filename = configuration_file
                found = True
                break
        if not found:
            raise ValueError('Logging configuration file "{}" not found in local or default directory'.format(filename))
    elif not path.exists(filename):
        raise ValueError('Logging configuration file "{}" not found'.format(filename))

    if filename is not None:
        global _current_logging_configuration_file
        filename = path.realpath(filename)

        if filename != _current_logging_configuration_file:
            working_directory = getcwdu()
            chdir(app_root)
            try:
                fileConfig(filename, {'SPLUNK_HOME': splunk_home})
            finally:
                chdir(working_directory)
            _current_logging_configuration_file = filename

    if len(root.handlers) == 0:
        root.addHandler(StreamHandler())

    return None if logger_name is None else getLogger(logger_name), filename


_current_logging_configuration_file = None

splunk_home = path.abspath(path.join(getcwdu(), environ.get('SPLUNK_HOME', '')))
app_file = getattr(sys.modules['__main__'], '__file__', sys.executable)
app_root = path.dirname(path.abspath(path.dirname(app_file)))

splunklib_logger, logging_configuration = configure_logging('splunklib')


__all__ = ['app_file', 'app_root', 'logging_configuration', 'splunk_home', 'splunklib_logger']
            humanize/bin/splunklib/searchcommands/eventing_command.py                                           000644  000765  000000  00000011774 12674041006 025316  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import imap

from .decorators import ConfigurationSetting
from .search_command import SearchCommand


class EventingCommand(SearchCommand):
    """ Applies a transformation to search results as they travel through the events pipeline.

    Eventing commands typically filter, group, order, and/or or augment event records. Examples of eventing commands
    from Splunk's built-in command set include sort_, dedup_, and cluster_. Each execution of an eventing command
    should produce a set of event records that is independently usable by downstream processors.

    .. _sort: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Sort
    .. _dedup: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Dedup
    .. _cluster: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Cluster

    EventingCommand configuration
    ==============================

    You can configure your command for operation under Search Command Protocol (SCP) version 1 or 2. SCP 2 requires
    Splunk 6.3 or later.

    """
    # region Methods

    def transform(self, records):
        """ Generator function that processes and yields event records to the Splunk events pipeline.

        You must override this method.

        """
        raise NotImplementedError('EventingCommand.transform(self, records)')

    def _execute(self, ifile, process):
        SearchCommand._execute(self, ifile, self.transform)

    # endregion

    class ConfigurationSettings(SearchCommand.ConfigurationSettings):
        """ Represents the configuration settings that apply to a :class:`EventingCommand`.

        """
        # region SCP v1/v2 properties

        required_fields = ConfigurationSetting(doc='''
            List of required fields for this search which back-propagates to the generating search.

            Setting this value enables selected fields mode under SCP 2. Under SCP 1 you must also specify
            :code:`clear_required_fields=True` to enable selected fields mode. To explicitly select all fields,
            specify a value of :const:`['*']`. No error is generated if a specified field is missing.

            Default: :const:`None`, which implicitly selects all fields.

            ''')

        # endregion

        # region SCP v1 properties

        clear_required_fields = ConfigurationSetting(doc='''
            :const:`True`, if required_fields represent the *only* fields required.

            If :const:`False`, required_fields are additive to any fields that may be required by subsequent commands.
            In most cases, :const:`False` is appropriate for eventing commands.

            Default: :const:`False`

            ''')

        retainsevents = ConfigurationSetting(readonly=True, value=True, doc='''
            :const:`True`, if the command retains events the way the sort/dedup/cluster commands do.

            If :const:`False`, the command transforms events the way the stats command does.

            Fixed: :const:`True`

            ''')

        # endregion

        # region SCP v2 properties

        maxinputs = ConfigurationSetting(doc='''
            Specifies the maximum number of events that can be passed to the command for each invocation.

            This limit cannot exceed the value of `maxresultrows` as defined in limits.conf_. Under SCP 1 you must
            specify this value in commands.conf_.

            Default: The value of `maxresultrows`.

            Supported by: SCP 2

            .. _limits.conf: http://docs.splunk.com/Documentation/Splunk/latest/admin/Limitsconf

            ''')

        type = ConfigurationSetting(readonly=True, value='eventing', doc='''
            Command type

            Fixed: :const:`'eventing'`.

            Supported by: SCP 2

            ''')

        # endregion

        # region Methods

        @classmethod
        def fix_up(cls, command):
            """ Verifies :code:`command` class structure.

            """
            if command.transform == EventingCommand.transform:
                raise AttributeError('No EventingCommand.transform override')
            SearchCommand.ConfigurationSettings.fix_up(command)

        def iteritems(self):
            iteritems = SearchCommand.ConfigurationSettings.iteritems(self)
            return imap(lambda (name, value): (name, 'events' if name == 'type' else value), iteritems)

        # endregion
    humanize/bin/splunklib/searchcommands/external_search_command.py                                    000644  000765  000000  00000017135 12674041006 026643  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
import sys
import traceback

if sys.platform == 'win32':
    from signal import signal, CTRL_BREAK_EVENT, SIGBREAK, SIGINT, SIGTERM
    from subprocess import Popen
    import atexit

from . import splunklib_logger as logger

# P1 [ ] TODO: Add ExternalSearchCommand class documentation


class ExternalSearchCommand(object):
    """
    """
    def __init__(self, path, argv=None, environ=None):

        if not isinstance(path, (bytes, unicode)):
            raise ValueError('Expected a string value for path, not {}'.format(repr(path)))

        self._logger = getLogger(self.__class__.__name__)
        self._path = unicode(path)
        self._argv = None
        self._environ = None

        self.argv = argv
        self.environ = environ

    # region Properties

    @property
    def argv(self):
        return getattr(self, '_argv')

    @argv.setter
    def argv(self, value):
        if not (value is None or isinstance(value, (list, tuple))):
            raise ValueError('Expected a list, tuple or value of None for argv, not {}'.format(repr(value)))
        self._argv = value

    @property
    def environ(self):
        return getattr(self, '_environ')

    @environ.setter
    def environ(self, value):
        if not (value is None or isinstance(value, dict)):
            raise ValueError('Expected a dictionary value for environ, not {}'.format(repr(value)))
        self._environ = value

    @property
    def logger(self):
        return self._logger

    @property
    def path(self):
        return self._path

    # endregion

    # region Methods

    def execute(self):
        # noinspection PyBroadException
        try:
            if self._argv is None:
                self._argv = os.path.splitext(os.path.basename(self._path))[0]
            self._execute(self._path, self._argv, self._environ)
        except:
            error_type, error, tb = sys.exc_info()
            message = 'Command execution failed: ' + unicode(error)
            self._logger.error(message + '\nTraceback:\n' + ''.join(traceback.format_tb(tb)))
            sys.exit(1)

    if sys.platform == 'win32':

        @staticmethod
        def _execute(path, argv=None, environ=None):
            """ Executes an external search command.

            :param path: Path to the external search command.
            :type path: unicode

            :param argv: Argument list.
            :type argv: list or tuple
            The arguments to the child process should start with the name of the command being run, but this is not
            enforced. A value of :const:`None` specifies that the base name of path name :param:`path` should be used.

            :param environ: A mapping which is used to define the environment variables for the new process.
            :type environ: dict or None.
            This mapping is used instead of the current process’s environment. A value of :const:`None` specifies that
            the :data:`os.environ` mapping should be used.

            :return: None

            """
            search_path = os.getenv('PATH') if environ is None else environ.get('PATH')
            found = ExternalSearchCommand._search_path(path, search_path)

            if found is None:
                raise ValueError('Cannot find command on path: {}'.format(path))

            path = found
            logger.debug('starting command="%s", arguments=%s', path, argv)

            def terminate(signal_number, frame):
                sys.exit('External search command is terminating on receipt of signal={}.'.format(signal_number))

            def terminate_child():
                if p.pid is not None and p.returncode is None:
                    logger.debug('terminating command="%s", arguments=%d, pid=%d', path, argv, p.pid)
                    os.kill(p.pid, CTRL_BREAK_EVENT)

            p = Popen(argv, executable=path, env=environ, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
            atexit.register(terminate_child)
            signal(SIGBREAK, terminate)
            signal(SIGINT, terminate)
            signal(SIGTERM, terminate)

            logger.debug('started command="%s", arguments=%s, pid=%d', path, argv, p.pid)
            p.wait()

            logger.debug('finished command="%s", arguments=%s, pid=%d, returncode=%d', path, argv, p.pid, p.returncode)
            sys.exit(p.returncode)

        @staticmethod
        def _search_path(executable, paths):
            """ Locates an executable program file.

            :param executable: The name of the executable program to locate.
            :type executable: unicode

            :param paths: A list of one or more directory paths where executable programs are located.
            :type paths: unicode

            :return:
            :rtype: Path to the executable program located or :const:`None`.

            """
            directory, filename = os.path.split(executable)
            extension = os.path.splitext(filename)[1].upper()
            executable_extensions = ExternalSearchCommand._executable_extensions

            if directory:
                if len(extension) and extension in executable_extensions:
                    return None
                for extension in executable_extensions:
                    path = executable + extension
                    if os.path.isfile(path):
                        return path
                return None

            if not paths:
                return None

            directories = [directory for directory in paths.split(';') if len(directory)]

            if len(directories) == 0:
                return None

            if len(extension) and extension in executable_extensions:
                for directory in directories:
                    path = os.path.join(directory, executable)
                    if os.path.isfile(path):
                        return path
                return None

            for directory in directories:
                path_without_extension = os.path.join(directory, executable)
                for extension in executable_extensions:
                    path = path_without_extension + extension
                    if os.path.isfile(path):
                        return path

            return None

        _executable_extensions = ('.COM', '.EXE')
    else:
        @staticmethod
        def _execute(path, argv, environ):
            if environ is None:
                os.execvp(path, argv)
            else:
                os.execvpe(path, argv, environ)
            return

    # endregion


def execute(path, argv=None, environ=None, command_class=ExternalSearchCommand):
    """
    :param path:
    :type path: basestring
    :param argv:
    :type: argv: list, tuple, or None
    :param environ:
    :type environ: dict
    :param command_class: External search command class to instantiate and execute.
    :type command_class: type
    :return:
    :rtype: None
    """
    assert issubclass(command_class, ExternalSearchCommand)
    command_class(path, argv, environ).execute()
                                                                                                                                                                                                                                                                                                                                                                                                                                   humanize/bin/splunklib/searchcommands/generating_command.py                                         000644  000765  000000  00000037634 12674041006 025625  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from .decorators import ConfigurationSetting
from .search_command import SearchCommand

from itertools import imap, ifilter

# P1 [O] TODO: Discuss generates_timeorder in the class-level documentation for GeneratingCommand


class GeneratingCommand(SearchCommand):
    """ Generates events based on command arguments.

    Generating commands receive no input and must be the first command on a pipeline. There are three pipelines:
    streams, events, and reports. The streams pipeline generates or processes time-ordered event records on an
    indexer or search head.

    Streaming commands filter, modify, or augment event records and can be applied to subsets of index data in a
    parallel manner. An example of a streaming command from Splunk's built-in command set is rex_ which extracts and
    adds fields to event records at search time. Records that pass through the streams pipeline move on to the events
    pipeline.

    The events pipeline generates or processes records on a search head. Eventing commands typically filter, group,
    order, or augment event records. Examples of eventing commands from Splunk's built-in command set include sort_,
    dedup_, and cluster_. Each execution of an eventing command should produce a set of event records that is
    independently usable by downstream processors. Records that pass through the events pipeline move on to the reports
    pipeline.

    The reports pipeline also runs on a search head, but yields data structures for presentation, not event records.
    Examples of streaming from Splunk's built-in command set include chart_, stats_, and contingency_.

    GeneratingCommand configuration
    ===============================

    Configure your generating command based on the pipeline that it targets. How you configure your command depends on
    the Search Command Protocol (SCP) version.

    +----------+-------------------------------------+--------------------------------------------+
    | Pipeline | SCP 1                               | SCP 2                                      |
    +==========+=====================================+============================================+
    | streams  | streaming=True[,local=[True|False]] | type='streaming'[,distributed=[true|false] |
    +----------+-------------------------------------+--------------------------------------------+
    | events   | retainsevents=True, streaming=False | type='eventing'                            |
    +----------+-------------------------------------+--------------------------------------------+
    | reports  | streaming=False                     | type='reporting'                           |
    +----------+-------------------------------------+--------------------------------------------+

    Only streaming commands may be distributed to indexers. By default generating commands are configured to run
    locally in the streams pipeline and will run under either SCP 1 or SCP 2.

    .. code-block:: python

        @Configuration()
        class StreamingGeneratingCommand(GeneratingCommand)
            ...

    How you configure your command to run on a different pipeline or in a distributed fashion depends on what SCP
    protocol versions you wish to support. You must be sure to configure your command consistently for each protocol,
    if you wish to support both protocol versions correctly.

    .. _chart: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Chart
    .. _cluster: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Cluster
    .. _contingency: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Contingency
    .. _dedup: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Dedup
    .. _rex: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Rex
    .. _sort: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Sort
    .. _stats: http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Stats

    Distributed Generating command
    ==============================

    Commands configured like this will run as the first command on search heads and/or indexers on the streams pipeline.

    +----------+---------------------------------------------------+---------------------------------------------------+
    | Pipeline | SCP 1                                             | SCP 2                                             |
    +==========+===================================================+===================================================+
    | streams  | 1. Add this line to your command's stanza in      | 1. Add this configuration setting to your code:   |
    |          |                                                   |                                                   |
    |          |    default/commands.conf.                         |    .. code-block:: python                         |
    |          |    .. code-block:: python                         |        @Configuration(distributed=True)           |
    |          |        local = false                              |        class SomeCommand(GeneratingCommand)       |
    |          |                                                   |            ...                                    |
    |          | 2. Restart splunk                                 |                                                   |
    |          |                                                   | 2. You are good to go; no need to restart Splunk  |
    +----------+---------------------------------------------------+---------------------------------------------------+

    Eventing Generating command
    ===========================

    Generating commands configured like this will run as the first command on a search head on the events pipeline.

    +----------+---------------------------------------------------+---------------------------------------------------+
    | Pipeline | SCP 1                                             | SCP 2                                             |
    +==========+===================================================+===================================================+
    | events   | You have a choice. Add these configuration        | Add this configuration setting to your command    |
    |          | settings to your command class:                   | setting to your command class:                    |
    |          |                                                   |                                                   |
    |          | .. code-block:: python                            | .. code-block:: python                            |
    |          |     @Configuration(                               |     @Configuration(type='eventing')               |
    |          |         retainsevents=True, streaming=False)      |     class SomeCommand(GeneratingCommand)          |
    |          |     class SomeCommand(GeneratingCommand)          |         ...                                       |
    |          |         ...                                       |                                                   |
    |          |                                                   |                                                   |
    |          | Or add these lines to default/commands.conf:      |                                                   |
    |          |                                                   |                                                   |
    |          | .. code-block::                                   |                                                   |
    |          |     retains events = true                         |                                                   |
    |          |     streaming = false                             |                                                   |
    +----------+---------------------------------------------------+---------------------------------------------------+

    Configure your command class like this, if you wish to support both protocols:

    .. code-block:: python
        @Configuration(type='eventing', retainsevents=True, streaming=False)
        class SomeCommand(GeneratingCommand)
            ...

    You might also consider adding these lines to commands.conf instead of adding them to your command class:

    .. code-block:: python
        retains events = false
        streaming = false

    Reporting Generating command
    ============================

    Commands configured like this will run as the first command on a search head on the reports pipeline.

    +----------+---------------------------------------------------+---------------------------------------------------+
    | Pipeline | SCP 1                                             | SCP 2                                             |
    +==========+===================================================+===================================================+
    | events   | You have a choice. Add these configuration        | Add this configuration setting to your command    |
    |          | settings to your command class:                   | setting to your command class:                    |
    |          |                                                   |                                                   |
    |          | .. code-block:: python                            | .. code-block:: python                            |
    |          |     @Configuration(retainsevents=False)           |     @Configuration(type='reporting')              |
    |          |     class SomeCommand(GeneratingCommand)          |     class SomeCommand(GeneratingCommand)          |
    |          |         ...                                       |         ...                                       |
    |          |                                                   |                                                   |
    |          | Or add this lines to default/commands.conf:       |                                                   |
    |          |                                                   |                                                   |
    |          | .. code-block::                                   |                                                   |
    |          |     retains events = false                        |                                                   |
    |          |     streaming = false                             |                                                   |
    +----------+---------------------------------------------------+---------------------------------------------------+

    Configure your command class like this, if you wish to support both protocols:

    .. code-block:: python
        @Configuration(type='reporting', streaming=False)
        class SomeCommand(GeneratingCommand)
            ...

    You might also consider adding these lines to commands.conf instead of adding them to your command class:

    .. code-block:: python
        retains events = false
        streaming = false

    """
    # region Methods

    def generate(self):
        """ A generator that yields records to the Splunk processing pipeline

        You must override this method.

        """
        raise NotImplementedError('GeneratingCommand.generate(self)')

    def _execute(self, ifile, process):
        """ Execution loop

        :param ifile: Input file object. Unused.
        :type ifile: file

        :return: `None`.

        """
        self._record_writer.write_records(self.generate())
        self.finish()

    # endregion

    # region Types

    class ConfigurationSettings(SearchCommand.ConfigurationSettings):
        """ Represents the configuration settings for a :code:`GeneratingCommand` class.

        """
        # region SCP v1/v2 Properties

        generating = ConfigurationSetting(readonly=True, value=True, doc='''
            Tells Splunk that this command generates events, but does not process inputs.

            Generating commands must appear at the front of the search pipeline identified by :meth:`type`.

            Fixed: :const:`True`

            Supported by: SCP 1, SCP 2

            ''')

        # endregion

        # region SCP v1 Properties

        generates_timeorder = ConfigurationSetting(value=False, doc='''
            :const:`True`, if the command generates new events.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        local = ConfigurationSetting(value=False, doc='''
            :const:`True`, if the command should run locally on the search head.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        retainsevents = ConfigurationSetting(value=False, doc='''
            :const:`True`, if the command retains events the way the sort, dedup, and cluster commands do, or whether it
            transforms them the way the stats command does.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        streaming = ConfigurationSetting(value=True, doc='''
            :const:`True`, if the command is streamable.

            Default: :const:`True`

            Supported by: SCP 1

            ''')

        # endregion

        # region SCP v2 Properties

        distributed = ConfigurationSetting(value=False, doc='''
            True, if this command should be distributed to indexers.

            This value is ignored unless :meth:`type` is equal to :const:`streaming`. It is only this command type that
            may be distributed.

            Default: :const:`False`

            Supported by: SCP 2

            ''')

        type = ConfigurationSetting(value='streaming', doc='''
            A command type name.

            ====================  ======================================================================================
            Value                 Description
            --------------------  --------------------------------------------------------------------------------------
            :const:`'eventing'`   Runs as the first command in the Splunk events pipeline. Cannot be distributed.
            :const:`'reporting'`  Runs as the first command in the Splunk reports pipeline. Cannot be distributed.
            :const:`'streaming'`  Runs as the first command in the Splunk streams pipeline. May be distributed.
            ====================  ======================================================================================

            Default: :const:`'streaming'`

            Supported by: SCP 2

            ''')

        # endregion

        # region Methods

        @classmethod
        def fix_up(cls, command):
            """ Verifies :code:`command` class structure.

            """
            if command.generate == GeneratingCommand.generate:
                raise AttributeError('No GeneratingCommand.generate override')

        def iteritems(self):
            iteritems = SearchCommand.ConfigurationSettings.iteritems(self)
            version = self.command.protocol_version
            if version == 2:
                iteritems = ifilter(lambda (name, value): name != 'distributed', iteritems)
                if self.distributed and self.type == 'streaming':
                    iteritems = imap(
                        lambda (name, value): (name, 'stateful') if name == 'type' else (name, value), iteritems)
            return iteritems

        pass
        # endregion

    pass
    # endregion
                                                                                                    humanize/bin/splunklib/searchcommands/internals.py                                                  000644  000765  000000  00000064027 12674041006 023777  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import deque, namedtuple, OrderedDict
from cStringIO import StringIO
from itertools import chain, imap
from json import JSONDecoder, JSONEncoder
from json.encoder import encode_basestring_ascii as json_encode_string
from urllib import unquote

import csv
import gzip
import os
import re
import sys

from . import environment

csv.field_size_limit(10485760)  # The default value is 128KB; upping to 10MB. See SPL-12117 for background on this issue

if sys.platform == 'win32':
    # Work around the fact that on Windows '\n' is mapped to '\r\n'. The typical solution is to simply open files in
    # binary mode, but stdout is already open, thus this hack. 'CPython' and 'PyPy' work differently. We assume that
    # all other Python implementations are compatible with 'CPython'. This might or might not be a valid assumption.
    from platform import python_implementation
    implementation = python_implementation()
    fileno = sys.stdout.fileno()
    if implementation == 'PyPy':
        sys.stdout = os.fdopen(fileno, 'wb', 0)
    else:
        from msvcrt import setmode
        setmode(fileno, os.O_BINARY)


class CommandLineParser(object):
    """ Parses the arguments to a search command.

    A search command line is described by the following syntax.

    **Syntax**::

       command       = command-name *[wsp option] *[wsp [dquote] field-name [dquote]]
       command-name  = alpha *( alpha / digit )
       option        = option-name [wsp] "=" [wsp] option-value
       option-name   = alpha *( alpha / digit / "_" )
       option-value  = word / quoted-string
       word          = 1*( %01-%08 / %0B / %0C / %0E-1F / %21 / %23-%FF ) ; Any character but DQUOTE and WSP
       quoted-string = dquote *( word / wsp / "\" dquote / dquote dquote ) dquote
       field-name    = ( "_" / alpha ) *( alpha / digit / "_" / "." / "-" )

    **Note:**

    This syntax is constrained to an 8-bit character set.

    **Note:**

    This syntax does not show that `field-name` values may be comma-separated when in fact they can be. This is
    because Splunk strips commas from the command line. A custom search command will never see them.

    **Example:**

    countmatches fieldname = word_count pattern = \w+ some_text_field

    Option names are mapped to properties in the targeted ``SearchCommand``. It is the responsibility of the property
    setters to validate the values they receive. Property setters may also produce side effects. For example,
    setting the built-in `log_level` immediately changes the `log_level`.

    """
    @classmethod
    def parse(cls, command, argv):
        """ Splits an argument list into an options dictionary and a fieldname
        list.

        The argument list, `argv`, must be of the form::

            *[option]... *[<field-name>]

        Options are validated and assigned to items in `command.options`. Field names are validated and stored in the
        list of `command.fieldnames`.

        #Arguments:

        :param command: Search command instance.
        :type command: ``SearchCommand``
        :param argv: List of search command arguments.
        :type argv: ``list``
        :return: ``None``

        #Exceptions:

        ``SyntaxError``: Argument list is incorrectly formed.
        ``ValueError``: Unrecognized option/field name, or an illegal field value.

        """
        debug = environment.splunklib_logger.debug
        command_class = type(command).__name__

        # Prepare

        debug('Parsing %s command line: %r', command_class, argv)
        command.fieldnames = None
        command.options.reset()
        argv = ' '.join(argv)

        command_args = cls._arguments_re.match(argv)

        if command_args is None:
            raise SyntaxError('Syntax error: {}'.format(argv))

        # Parse options

        for option in cls._options_re.finditer(command_args.group('options')):
            name, value = option.group('name'), option.group('value')
            if name not in command.options:
                raise ValueError(
                    'Unrecognized {} command option: {}={}'.format(command.name, name, json_encode_string(value)))
            command.options[name].value = cls.unquote(value)

        missing = command.options.get_missing()

        if missing is not None:
            if len(missing) > 1:
                raise ValueError(
                    'Values for these {} command options are required: {}'.format(command.name, ', '.join(missing)))
            raise ValueError('A value for {} command option {} is required'.format(command.name, missing[0]))

        # Parse field names

        fieldnames = command_args.group('fieldnames')

        if fieldnames is None:
            command.fieldnames = []
        else:
            command.fieldnames = [cls.unquote(value.group(0)) for value in cls._fieldnames_re.finditer(fieldnames)]

        debug('  %s: %s', command_class, command)

    @classmethod
    def unquote(cls, string):
        """ Removes quotes from a quoted string.

        Splunk search command quote rules are applied. The enclosing double-quotes, if present, are removed. Escaped
        double-quotes ('\"' or '""') are replaced by a single double-quote ('"').

        **NOTE**

        We are not using a json.JSONDecoder because Splunk quote rules are different than JSON quote rules. A
        json.JSONDecoder does not recognize a pair of double-quotes ('""') as an escaped quote ('"') and will
        decode single-quoted strings ("'") in addition to double-quoted ('"') strings.

        """
        if len(string) == 0:
            return ''

        if string[0] == '"':
            if len(string) == 1 or string[-1] != '"':
                raise SyntaxError('Poorly formed string literal: ' + string)
            string = string[1:-1]

        if len(string) == 0:
            return ''

        def replace(match):
            value = match.group(0)
            if value == '""':
                return '"'
            if len(value) < 2:
                raise SyntaxError('Poorly formed string literal: ' + string)
            return value[1]

        result = re.sub(cls._escaped_character_re, replace, string)
        return result

    # region Class variables

    _arguments_re = re.compile(r"""
        ^\s*
        (?P<options>     # Match a leading set of name/value pairs
            (?:
                (?:(?=\w)[^\d]\w*)                         # name
                \s*=\s*                                    # =
                (?:"(?:\\.|""|[^"])*"|(?:\\.|[^\s"])+)\s*  # value
            )*
        )\s*
        (?P<fieldnames>  # Match a trailing set of field names
            (?:
                (?:"(?:\\.|""|[^"])*"|(?:\\.|[^\s"])+)\s*
            )*
        )\s*$
        """, re.VERBOSE | re.UNICODE)

    _escaped_character_re = re.compile(r'(\\.|""|[\\"])')

    _fieldnames_re = re.compile(r"""("(?:\\.|""|[^"])+"|(?:\\.|[^\s"])+)""")

    _options_re = re.compile(r"""
        # Captures a set of name/value pairs when used with re.finditer
        (?P<name>(?:(?=\w)[^\d]\w*))                   # name
        \s*=\s*                                        # =
        (?P<value>"(?:\\.|""|[^"])*"|(?:\\.|[^\s"])+)  # value
        """, re.VERBOSE | re.UNICODE)

    # endregion


class ConfigurationSettingsType(type):
    """ Metaclass for constructing ConfigurationSettings classes.

    Instances of :class:`ConfigurationSettingsType` construct :class:`ConfigurationSettings` classes from classes from
    a base :class:`ConfigurationSettings` class and a dictionary of configuration settings. The settings in the
    dictionary are validated against the settings in the base class. You cannot add settings, you can only change their
    backing-field values and you cannot modify settings without backing-field values. These are considered fixed
    configuration setting values.

    This is an internal class used in two places:

    + :meth:`decorators.Configuration.__call__`

      Adds a ConfigurationSettings attribute to a :class:`SearchCommand` class.

    + :meth:`reporting_command.ReportingCommand.fix_up`

      Adds a ConfigurationSettings attribute to a :meth:`ReportingCommand.map` method, if there is one.

    """
    def __new__(mcs, module, name, bases):
        mcs = super(ConfigurationSettingsType, mcs).__new__(mcs, name, bases, {})
        return mcs

    def __init__(cls, module, name, bases):

        super(ConfigurationSettingsType, cls).__init__(name, bases, None)
        cls.__module__ = module

    @staticmethod
    def validate_configuration_setting(specification, name, value):
        if not isinstance(value, specification.type):
            if isinstance(specification.type, type):
                type_names = specification.type.__name__
            else:
                type_names = ', '.join(imap(lambda t: t.__name__, specification.type))
            raise ValueError('Expected {} value, not {}={}'.format(type_names, name, repr(value)))
        if specification.constraint and not specification.constraint(value):
            raise ValueError('Illegal value: {}={}'.format(name, repr(value)))
        return value

    specification = namedtuple(
        b'ConfigurationSettingSpecification', (
            b'type',
            b'constraint',
            b'supporting_protocols'))

    # P1 [ ] TODO: Review ConfigurationSettingsType.specification_matrix for completeness and correctness

    specification_matrix = {
        'clear_required_fields': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'distributed': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[2]),
        'generates_timeorder': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'generating': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1, 2]),
        'local': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'maxinputs': specification(
            type=int,
            constraint=lambda value: 0 <= value <= sys.maxint,
            supporting_protocols=[2]),
        'overrides_timeorder': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'required_fields': specification(
            type=(list, set, tuple),
            constraint=None,
            supporting_protocols=[1, 2]),
        'requires_preop': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'retainsevents': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'run_in_preview': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[2]),
        'streaming': specification(
            type=bool,
            constraint=None,
            supporting_protocols=[1]),
        'streaming_preop': specification(
            type=(bytes, unicode),
            constraint=None,
            supporting_protocols=[1, 2]),
        'type': specification(
            type=(bytes, unicode),
            constraint=lambda value: value in ('eventing', 'reporting', 'streaming'),
            supporting_protocols=[2])}


class CsvDialect(csv.Dialect):
    """ Describes the properties of Splunk CSV streams """
    delimiter = b','
    quotechar = b'"'
    doublequote = True
    skipinitialspace = False
    lineterminator = b'\r\n'
    quoting = csv.QUOTE_MINIMAL


class InputHeader(dict):
    """ Represents a Splunk input header as a collection of name/value pairs.

    """
    def __str__(self):
        return '\n'.join([name + ':' + value for name, value in self.iteritems()])

    def read(self, ifile):
        """ Reads an input header from an input file.

        The input header is read as a sequence of *<name>***:***<value>* pairs separated by a newline. The end of the
        input header is signalled by an empty line or an end-of-file.

        :param ifile: File-like object that supports iteration over lines.

        """
        name, value = None, None

        for line in ifile:
            if line == '\n':
                break
            item = line.split(':', 1)
            if len(item) == 2:
                # start of a new item
                if name is not None:
                    self[name] = value[:-1]  # value sans trailing newline
                name, value = item[0], unquote(item[1])
            elif name is not None:
                # continuation of the current item
                value += unquote(line)

        if name is not None: self[name] = value[:-1] if value[-1] == '\n' else value


Message = namedtuple(b'Message', (b'type', b'text'))


class MetadataDecoder(JSONDecoder):

    def __init__(self):
        JSONDecoder.__init__(self, object_hook=self._object_hook)

    @staticmethod
    def _object_hook(dictionary):

        object_view = ObjectView(dictionary)
        stack = deque()
        stack.append((None, None, dictionary))

        while len(stack):
            instance, member_name, dictionary = stack.popleft()

            for name, value in dictionary.iteritems():
                if isinstance(value, dict):
                    stack.append((dictionary, name, value))

            if instance is not None:
                instance[member_name] = ObjectView(dictionary)

        return object_view


class MetadataEncoder(JSONEncoder):

    def __init__(self):
        JSONEncoder.__init__(self, separators=MetadataEncoder._separators)

    def default(self, o):
        return o.__dict__ if isinstance(o, ObjectView) else JSONEncoder.default(self, o)

    _separators = (',', ':')


class ObjectView(object):

    def __init__(self, dictionary):
        self.__dict__ = dictionary

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return str(self.__dict__)


class Recorder(object):

    def __init__(self, path, f):
        self._recording = gzip.open(path + '.gz', 'wb')
        self._file = f

    def __getattr__(self, name):
        return getattr(self._file, name)

    def __iter__(self):
        for line in self._file:
            self._recording.write(line)
            self._recording.flush()
            yield line

    def read(self, size=None):
        value = self._file.read() if size is None else self._file.read(size)
        self._recording.write(value)
        self._recording.flush()
        return value

    def readline(self, size=None):
        value = self._file.readline() if size is None else self._file.readline(size)
        if len(value) > 0:
            self._recording.write(value)
            self._recording.flush()
        return value

    def record(self, *args):
        for arg in args:
            self._recording.write(arg)

    def write(self, text):
        self._recording.write(text)
        self._file.write(text)
        self._recording.flush()


class RecordWriter(object):

    def __init__(self, ofile, maxresultrows=None):
        self._maxresultrows = 50000 if maxresultrows is None else maxresultrows

        self._ofile = ofile
        self._fieldnames = None
        self._buffer = StringIO()

        self._writer = csv.writer(self._buffer, dialect=CsvDialect)
        self._writerow = self._writer.writerow
        self._finished = False
        self._flushed = False

        self._inspector = OrderedDict()
        self._chunk_count = 0
        self._record_count = 0
        self._total_record_count = 0L

    @property
    def is_flushed(self):
        return self._flushed

    @is_flushed.setter
    def is_flushed(self, value):
        self._flushed = True if value else False

    @property
    def ofile(self):
        return self._ofile

    @ofile.setter
    def ofile(self, value):
        self._ofile = value

    def flush(self, finished=None, partial=None):
        assert finished is None or isinstance(finished, bool)
        assert partial is None or isinstance(partial, bool)
        assert not (finished is None and partial is None)
        assert finished is None or partial is None
        self._ensure_validity()

    def write_message(self, message_type, message_text, *args, **kwargs):
        self._ensure_validity()
        self._inspector.setdefault('messages', []).append((message_type, message_text.format(*args, **kwargs)))

    def write_record(self, record):
        self._ensure_validity()
        self._write_record(record)

    def write_records(self, records):
        self._ensure_validity()
        write_record = self._write_record
        for record in records:
            write_record(record)

    def _clear(self):
        self._buffer.reset()
        self._buffer.truncate()
        self._inspector.clear()
        self._record_count = 0
        self._flushed = False

    def _ensure_validity(self):
        if self._finished is True:
            assert self._record_count == 0 and len(self._inspector) == 0
            raise RuntimeError('I/O operation on closed record writer')

    def _write_record(self, record):

        fieldnames = self._fieldnames

        if fieldnames is None:
            self._fieldnames = fieldnames = record.keys()
            value_list = imap(lambda fn: unicode(fn).encode('utf-8'), fieldnames)
            value_list = imap(lambda fn: (fn, b'__mv_' + fn), value_list)
            self._writerow(list(chain.from_iterable(value_list)))

        get_value = record.get
        values = []

        for fieldname in fieldnames:
            value = get_value(fieldname, None)

            if value is None:
                values += (None, None)
                continue

            value_t = type(value)

            if issubclass(value_t, (list, tuple)):

                if len(value) == 0:
                    values += (None, None)
                    continue

                if len(value) > 1:
                    value_list = value
                    sv = b''
                    mv = b'$'

                    for value in value_list:

                        if value is None:
                            sv += b'\n'
                            mv += b'$;$'
                            continue

                        value_t = type(value)

                        if value_t is not bytes:

                            if value_t is bool:
                                value = str(value.real)
                            elif value_t is unicode:
                                value = value.encode('utf-8', errors='backslashreplace')
                            elif value_t is int or value_t is long or value_t is float or value_t is complex:
                                value = str(value)
                            elif issubclass(value_t, (dict, list, tuple)):
                                value = str(''.join(RecordWriter._iterencode_json(value, 0)))
                            else:
                                value = repr(value).encode('utf-8', errors='backslashreplace')

                        sv += value + b'\n'
                        mv += value.replace(b'$', b'$$') + b'$;$'

                    values += (sv[:-1], mv[:-2])
                    continue

                value = value[0]
                value_t = type(value)

            if value_t is bool:
                values += (str(value.real), None)
                continue

            if value_t is bytes:
                values += (value, None)
                continue

            if value_t is unicode:
                values += (value.encode('utf-8', errors='backslashreplace'), None)
                continue

            if value_t is int or value_t is long or value_t is float or value_t is complex:
                values += (str(value), None)
                continue

            if issubclass(value_t, dict):
                values += (str(''.join(RecordWriter._iterencode_json(value, 0))), None)
                continue

            values += (repr(value).encode('utf-8', errors='backslashreplace'), None)

        self._writerow(values)
        self._record_count += 1

        if self._record_count >= self._maxresultrows:
            self.flush(partial=True)

    try:
        # noinspection PyUnresolvedReferences
        from _json import make_encoder
    except ImportError:
        # We may be running under PyPy 2.5 which does not include the _json module
        _iterencode_json = JSONEncoder(separators=(',', ':')).iterencode
    else:
        # Creating _iterencode_json this way yields a two-fold performance improvement on Python 2.7.9 and 2.7.10
        from json.encoder import encode_basestring_ascii

        @staticmethod
        def _default(o):
            raise TypeError(repr(o) + ' is not JSON serializable')

        _iterencode_json = make_encoder(
            {},                       # markers (for detecting circular references)
            _default,                 # object_encoder
            encode_basestring_ascii,  # string_encoder
            None,                     # indent
            ':', ',',                 # separators
            False,                    # sort_keys
            False,                    # skip_keys
            True                      # allow_nan
        )

        del make_encoder


class RecordWriterV1(RecordWriter):

    def flush(self, finished=None, partial=None):

        RecordWriter.flush(self, finished, partial)  # validates arguments and the state of this instance

        if self._record_count > 0 or (self._chunk_count == 0 and 'messages' in self._inspector):

            messages = self._inspector.get('messages')
            write = self._ofile.write

            if self._chunk_count == 0:

                # Messages are written to the messages header when we write the first chunk of data
                # Guarantee: These messages are displayed by splunkweb and the job inspector

                if messages is not None:

                    message_level = RecordWriterV1._message_level.get

                    for level, text in messages:
                        write(message_level(level, level))
                        write('=')
                        write(text)
                        write('\r\n')

                write('\r\n')

            elif messages is not None:

                # Messages are written to the messages header when we write subsequent chunks of data
                # Guarantee: These messages are displayed by splunkweb and the job inspector, if and only if the
                # command is configured with
                #
                #       stderr_dest = message
                #
                # stderr_dest is a static configuration setting. This means that it can only be set in commands.conf.
                # It cannot be set in code.

                stderr = sys.stderr

                for level, text in messages:
                    print(level, text, file=stderr)

            write(self._buffer.getvalue())
            self._clear()
            self._chunk_count += 1
            self._total_record_count += self._record_count

        self._finished = finished is True

    _message_level = {
        'DEBUG': 'debug_message',
        'ERROR': 'error_message',
        'FATAL': 'error_message',
        'INFO': 'info_message',
        'WARN': 'warn_message'
    }


class RecordWriterV2(RecordWriter):

    def flush(self, finished=None, partial=None):

        RecordWriter.flush(self, finished, partial)  # validates arguments and the state of this instance
        inspector = self._inspector

        if self._flushed is False:

            self._total_record_count += self._record_count
            self._chunk_count += 1

            # TODO: DVPL-6448: splunklib.searchcommands | Add support for partial: true when it is implemented in
            # ChunkedExternProcessor (See SPL-103525)
            #
            # We will need to replace the following block of code with this block:
            #
            # metadata = [
            #     ('inspector', self._inspector if len(self._inspector) else None),
            #     ('finished', finished),
            #     ('partial', partial)]

            if len(inspector) == 0:
                inspector = None

            if partial is True:
                finished = False

            metadata = [item for item in ('inspector', inspector), ('finished', finished)]
            self._write_chunk(metadata, self._buffer.getvalue())
            self._clear()

        elif finished is True:
            self._write_chunk((('finished', True),), '')

        self._finished = finished is True

    def write_metadata(self, configuration):
        self._ensure_validity()

        metadata = chain(configuration.iteritems(), (('inspector', self._inspector if self._inspector else None),))
        self._write_chunk(metadata, '')
        self._ofile.write('\n')
        self._clear()

    def write_metric(self, name, value):
        self._ensure_validity()
        self._inspector['metric.' + name] = value

    def _clear(self):
        RecordWriter._clear(self)
        self._fieldnames = None

    def _write_chunk(self, metadata, body):

        if metadata:
            metadata = str(''.join(self._iterencode_json({n: v for n, v in metadata if v is not None}, 0)))
            metadata_length = len(metadata)
        else:
            metadata_length = 0

        body_length = len(body)

        if not (metadata_length > 0 or body_length > 0):
            return

        start_line = b'chunked 1.0,' + bytes(metadata_length) + b',' + bytes(body_length) + b'\n'
        write = self._ofile.write
        write(start_line)
        write(metadata)
        write(body)
        self._ofile.flush()
        self._flushed = False
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         humanize/bin/splunklib/searchcommands/reporting_command.py                                          000644  000765  000000  00000022606 12674041006 025504  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain

from .internals import ConfigurationSettingsType, json_encode_string
from .decorators import ConfigurationSetting, Option
from .streaming_command import StreamingCommand
from .search_command import SearchCommand
from .validators import Set


class ReportingCommand(SearchCommand):
    """ Processes search result records and generates a reporting data structure.

    Reporting search commands run as either reduce or map/reduce operations. The reduce part runs on a search head and
    is responsible for processing a single chunk of search results to produce the command's reporting data structure.
    The map part is called a streaming preop. It feeds the reduce part with partial results and by default runs on the
    search head and/or one or more indexers.

    You must implement a :meth:`reduce` method as a generator function that iterates over a set of event records and
    yields a reporting data structure. You may implement a :meth:`map` method as a generator function that iterates
    over a set of event records and yields :class:`dict` or :class:`list(dict)` instances.

    ReportingCommand configuration
    ==============================

    Configure the :meth:`map` operation using a Configuration decorator on your :meth:`map` method. Configure it like
    you would a :class:`StreamingCommand`. Configure the :meth:`reduce` operation using a Configuration decorator on
    your :meth:`ReportingCommand` class.

    You can configure your command for operation under Search Command Protocol (SCP) version 1 or 2. SCP 2 requires
    Splunk 6.3 or later.

    """
    # region Special methods

    def __init__(self):
        SearchCommand.__init__(self)

    # endregion

    # region Options

    phase = Option(doc='''
        **Syntax:** phase=[map|reduce]

        **Description:** Identifies the phase of the current map-reduce operation.

    ''', default='reduce', validate=Set('map', 'reduce'))

    # endregion

    # region Methods

    def map(self, records):
        """ Override this method to compute partial results.

        :param records:
        :type records:

        You must override this method, if :code:`requires_preop=True`.

        """
        return NotImplemented

    def prepare(self):

        phase = self.phase

        if phase == 'map':
            # noinspection PyUnresolvedReferences
            self._configuration = self.map.ConfigurationSettings(self)
            return

        if phase == 'reduce':
            streaming_preop = chain((self.name, 'phase="map"', str(self._options)), self.fieldnames)
            self._configuration.streaming_preop = ' '.join(streaming_preop)
            return

        raise RuntimeError('Unrecognized reporting command phase: {}'.format(json_encode_string(unicode(phase))))

    def reduce(self, records):
        """ Override this method to produce a reporting data structure.

        You must override this method.

        """
        raise NotImplementedError('reduce(self, records)')

    def _execute(self, ifile, process):
        SearchCommand._execute(self, ifile, getattr(self, self.phase))

    # endregion

    # region Types

    class ConfigurationSettings(SearchCommand.ConfigurationSettings):
        """ Represents the configuration settings for a :code:`ReportingCommand`.

        """
        # region SCP v1/v2 Properties

        required_fields = ConfigurationSetting(doc='''
            List of required fields for this search which back-propagates to the generating search.

            Setting this value enables selected fields mode under SCP 2. Under SCP 1 you must also specify
            :code:`clear_required_fields=True` to enable selected fields mode. To explicitly select all fields,
            specify a value of :const:`['*']`. No error is generated if a specified field is missing.

            Default: :const:`None`, which implicitly selects all fields.

            Supported by: SCP 1, SCP 2

            ''')

        requires_preop = ConfigurationSetting(doc='''
            Indicates whether :meth:`ReportingCommand.map` is required for proper command execution.

            If :const:`True`, :meth:`ReportingCommand.map` is guaranteed to be called. If :const:`False`, Splunk
            considers it to be an optimization that may be skipped.

            Default: :const:`False`

            Supported by: SCP 1, SCP 2

            ''')

        streaming_preop = ConfigurationSetting(doc='''
            Denotes the requested streaming preop search string.

            Computed.

            Supported by: SCP 1, SCP 2

            ''')

        # endregion

        # region SCP v1 Properties

        clear_required_fields = ConfigurationSetting(doc='''
            :const:`True`, if required_fields represent the *only* fields required.

            If :const:`False`, required_fields are additive to any fields that may be required by subsequent commands.
            In most cases, :const:`True` is appropriate for reporting commands.

            Default: :const:`True`

            Supported by: SCP 1

            ''')

        retainsevents = ConfigurationSetting(readonly=True, value=False, doc='''
            Signals that :meth:`ReportingCommand.reduce` transforms _raw events to produce a reporting data structure.

            Fixed: :const:`False`

            Supported by: SCP 1

            ''')

        streaming = ConfigurationSetting(readonly=True, value=False, doc='''
            Signals that :meth:`ReportingCommand.reduce` runs on the search head.

            Fixed: :const:`False`

            Supported by: SCP 1

            ''')

        # endregion

        # region SCP v2 Properties

        maxinputs = ConfigurationSetting(doc='''
            Specifies the maximum number of events that can be passed to the command for each invocation.

            This limit cannot exceed the value of `maxresultrows` in limits.conf_. Under SCP 1 you must specify this
            value in commands.conf_.

            Default: The value of `maxresultrows`.

            Supported by: SCP 2

            .. _limits.conf: http://docs.splunk.com/Documentation/Splunk/latest/admin/Limitsconf

            ''')

        run_in_preview = ConfigurationSetting(doc='''
            :const:`True`, if this command should be run to generate results for preview; not wait for final output.

            This may be important for commands that have side effects (e.g., outputlookup).

            Default: :const:`True`

            Supported by: SCP 2

            ''')

        type = ConfigurationSetting(readonly=True, value='reporting', doc='''
            Command type name.

            Fixed: :const:`'reporting'`.

            Supported by: SCP 2

            ''')

        # endregion

        # region Methods

        @classmethod
        def fix_up(cls, command):
            """ Verifies :code:`command` class structure and configures the :code:`command.map` method.

            Verifies that :code:`command` derives from :class:`ReportingCommand` and overrides
            :code:`ReportingCommand.reduce`. It then configures :code:`command.reduce`, if an overriding implementation
            of :code:`ReportingCommand.reduce` has been provided.

            :param command: :code:`ReportingCommand` class

            Exceptions:

            :code:`TypeError` :code:`command` class is not derived from :code:`ReportingCommand`
            :code:`AttributeError` No :code:`ReportingCommand.reduce` override

            """
            if not issubclass(command, ReportingCommand):
                raise TypeError('{} is not a ReportingCommand'.format( command))

            if command.reduce == ReportingCommand.reduce:
                raise AttributeError('No ReportingCommand.reduce override')

            if command.map == ReportingCommand.map:
                cls._requires_preop = False
                return

            f = vars(command)[b'map']   # Function backing the map method

            # EXPLANATION OF PREVIOUS STATEMENT: There is no way to add custom attributes to methods. See [Why does
            # setattr fail on a method](http://goo.gl/aiOsqh) for a discussion of this issue.

            try:
                settings = f._settings
            except AttributeError:
                f.ConfigurationSettings = StreamingCommand.ConfigurationSettings
                return

            # Create new StreamingCommand.ConfigurationSettings class

            module = command.__module__ + b'.' + command.__name__ + b'.map'
            name = b'ConfigurationSettings'
            bases = (StreamingCommand.ConfigurationSettings,)

            f.ConfigurationSettings = ConfigurationSettingsType(module, name, bases)
            ConfigurationSetting.fix_up(f.ConfigurationSettings, settings)
            del f._settings

        pass
        # endregion

    pass
    # endregion
                                                                                                                          humanize/bin/splunklib/searchcommands/search_command.py                                             000644  000765  000000  00000112341 12674041006 024734  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

# Absolute imports

from splunklib.client import Service

from collections import namedtuple, OrderedDict
from copy import deepcopy
from cStringIO import StringIO
from itertools import chain, ifilter, imap, islice, izip
from logging import _levelNames, getLevelName, getLogger
from shutil import make_archive
from time import time
from urllib import unquote
from urlparse import urlsplit
from warnings import warn
from xml.etree import ElementTree

import os
import sys
import re
import csv
import tempfile
import traceback

# Relative imports

from . internals import (
    CommandLineParser,
    CsvDialect,
    InputHeader,
    Message,
    MetadataDecoder,
    MetadataEncoder,
    ObjectView,
    Recorder,
    RecordWriterV1,
    RecordWriterV2,
    json_encode_string)

from . import Boolean, Option, environment

# ----------------------------------------------------------------------------------------------------------------------

# P1 [ ] TODO: Log these issues against ChunkedExternProcessor
#
# 1. Implement requires_preop configuration setting.
#    This configuration setting is currently rejected by ChunkedExternProcessor.
#
# 2. Rename type=events as type=eventing for symmetry with type=reporting and type=streaming
#    Eventing commands process records on the events pipeline. This change effects ChunkedExternProcessor.cpp,
#    eventing_command.py, and generating_command.py.
#
# 3. For consistency with SCPV1, commands.conf should not require filename setting when chunked = true
#    The SCPV1 processor uses <stanza-name>.py as the default filename. The ChunkedExternProcessor should do the same.

# P1 [ ] TODO: Verify that ChunkedExternProcessor complains if a streaming_preop has a type other than 'streaming'
# It once looked like sending type='reporting' for the streaming_preop was accepted.

# ----------------------------------------------------------------------------------------------------------------------

# P2 [ ] TODO: Consider bumping None formatting up to Option.Item.__str__


class SearchCommand(object):
    """ Represents a custom search command.

    """
    def __init__(self):

        # Variables that may be used, but not altered by derived classes

        class_name = self.__class__.__name__

        self._logger, self._logging_configuration = getLogger(class_name), environment.logging_configuration

        # Variables backing option/property values

        self._configuration = self.ConfigurationSettings(self)
        self._input_header = InputHeader()
        self._fieldnames = None
        self._finished = None
        self._metadata = None
        self._options = None
        self._protocol_version = None
        self._search_results_info = None
        self._service = None

        # Internal variables

        self._default_logging_level = self._logger.level
        self._record_writer = None
        self._records = None

    def __str__(self):
        text = ' '.join(chain((type(self).name, str(self.options)), [] if self.fieldnames is None else self.fieldnames))
        return text

    # region Options

    @Option
    def logging_configuration(self):
        """ **Syntax:** logging_configuration=<path>

        **Description:** Loads an alternative logging configuration file for
        a command invocation. The logging configuration file must be in Python
        ConfigParser-format. Path names are relative to the app root directory.

        """
        return self._logging_configuration

    @logging_configuration.setter
    def logging_configuration(self, value):
        self._logger, self._logging_configuration = environment.configure_logging(self.__class__.__name__, value)

    @Option
    def logging_level(self):
        """ **Syntax:** logging_level=[CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET]

        **Description:** Sets the threshold for the logger of this command invocation. Logging messages less severe than
        `logging_level` will be ignored.

        """
        return getLevelName(self._logger.getEffectiveLevel())

    @logging_level.setter
    def logging_level(self, value):
        if value is None:
            value = self._default_logging_level
        if isinstance(value, (bytes, unicode)):
            try:
                level = _levelNames[value.upper()]
            except KeyError:
                raise ValueError('Unrecognized logging level: {}'.format(value))
        else:
            try:
                level = int(value)
            except ValueError:
                raise ValueError('Unrecognized logging level: {}'.format(value))
        self._logger.setLevel(level)

    record = Option(doc='''
        **Syntax: record=<bool>

        **Description:** When `true`, records the interaction between the command and splunkd. Defaults to `false`.

        ''', default=False, validate=Boolean())

    show_configuration = Option(doc='''
        **Syntax:** show_configuration=<bool>

        **Description:** When `true`, reports command configuration as an informational message. Defaults to `false`.

        ''', default=False, validate=Boolean())

    # endregion

    # region Properties

    @property
    def configuration(self):
        """ Returns the configuration settings for this command.

        """
        return self._configuration

    @property
    def fieldnames(self):
        """ Returns the fieldnames specified as argument to this command.

        """
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, value):
        self._fieldnames = value

    @property
    def input_header(self):
        """ Returns the input header for this command.

        :return: The input header for this command.
        :rtype: InputHeader

        """
        warn(
            'SearchCommand.input_header is deprecated and will be removed in a future release. '
            'Please use SearchCommand.metadata instead.', DeprecationWarning, 2)
        return self._input_header

    @property
    def logger(self):
        """ Returns the logger for this command.

        :return: The logger for this command.
        :rtype:

        """
        return self._logger

    @property
    def metadata(self):
        return self._metadata

    @property
    def options(self):
        """ Returns the options specified as argument to this command.

        """
        if self._options is None:
            self._options = Option.View(self)
        return self._options

    @property
    def protocol_version(self):
        return self._protocol_version

    @property
    def search_results_info(self):
        """ Returns the search results info for this command invocation.

        The search results info object is created from the search results info file associated with the command
        invocation.

        :return: Search results info:const:`None`, if the search results info file associated with the command
        invocation is inaccessible.
        :rtype: SearchResultsInfo or NoneType

        """
        if self._search_results_info is not None:
            return self._search_results_info

        if self._protocol_version == 1:
            try:
                path = self._input_header['infoPath']
            except KeyError:
                return None
        else:
            assert self._protocol_version == 2

            try:
                dispatch_dir = self._metadata.searchinfo.dispatch_dir
            except AttributeError:
                return None

            path = os.path.join(dispatch_dir, 'info.csv')

        try:
            with open(path, 'rb') as f:
                reader = csv.reader(f, dialect=CsvDialect)
                fields = reader.next()
                values = reader.next()
        except IOError as error:
            if error.errno == 2:
                self.logger.error('Search results info file {} does not exist.'.format(json_encode_string(path)))
                return
            raise

        def convert_field(field):
            return (field[1:] if field[0] == '_' else field).replace('.', '_')

        decode = MetadataDecoder().decode

        def convert_value(value):
            try:
                return decode(value) if len(value) > 0 else value
            except ValueError:
                return value

        info = ObjectView(dict(imap(lambda (f, v): (convert_field(f), convert_value(v)), izip(fields, values))))

        try:
            count_map = info.countMap
        except AttributeError:
            pass
        else:
            count_map = count_map.split(';')
            n = len(count_map)
            info.countMap = dict(izip(islice(count_map, 0, n, 2), islice(count_map, 1, n, 2)))

        try:
            msg_type = info.msgType
            msg_text = info.msg
        except AttributeError:
            pass
        else:
            messages = ifilter(lambda (t, m): t or m, izip(msg_type.split('\n'), msg_text.split('\n')))
            info.msg = [Message(message) for message in messages]
            del info.msgType

        try:
            info.vix_families = ElementTree.fromstring(info.vix_families)
        except AttributeError:
            pass

        self._search_results_info = info
        return info

    @property
    def service(self):
        """ Returns a Splunk service object for this command invocation or None.

        The service object is created from the Splunkd URI and authentication token passed to the command invocation in
        the search results info file. This data is not passed to a command invocation by default. You must request it by
        specifying this pair of configuration settings in commands.conf:

           .. code-block:: python
               enableheader = true
               requires_srinfo = true

        The :code:`enableheader` setting is :code:`true` by default. Hence, you need not set it. The
        :code:`requires_srinfo` setting is false by default. Hence, you must set it.

        :return: :class:`splunklib.client.Service`, if :code:`enableheader` and :code:`requires_srinfo` are both
        :code:`true`. Otherwise, if either :code:`enableheader` or :code:`requires_srinfo` are :code:`false`, a value
        of :code:`None` is returned.

        """
        if self._service is not None:
            return self._service

        metadata = self._metadata

        if metadata is None:
            return None

        try:
            searchinfo = self._metadata.searchinfo
        except AttributeError:
            return None

        splunkd_uri = searchinfo.splunkd_uri

        if splunkd_uri is None:
            return None

        uri = urlsplit(splunkd_uri, allow_fragments=False)

        self._service = Service(
            scheme=uri.scheme, host=uri.hostname, port=uri.port, app=searchinfo.app, token=searchinfo.session_key)

        return self._service

    # endregion

    # region Methods

    def error_exit(self, error, message=None):
        self.write_error(error.message if message is None else message)
        self.logger.error('Abnormal exit: %s', error)
        exit(1)

    def finish(self):
        """ Flushes the output buffer and signals that this command has finished processing data.

        :return: :const:`None`

        """
        self._record_writer.flush(finished=True)

    def flush(self):
        """ Flushes the output buffer.

        :return: :const:`None`

        """
        self._record_writer.flush(partial=True)

    def prepare(self):
        """ Prepare for execution.

        This method should be overridden in search command classes that wish to examine and update their configuration
        or option settings prior to execution. It is called during the getinfo exchange before command metadata is sent
        to splunkd.

        :return: :const:`None`
        :rtype: NoneType

        """
        pass

    def process(self, argv=sys.argv, ifile=sys.stdin, ofile=sys.stdout):
        """ Process data.

        :param argv: Command line arguments.
        :type argv: list or tuple

        :param ifile: Input data file.
        :type ifile: file

        :param ofile: Output data file.
        :type ofile: file

        :return: :const:`None`
        :rtype: NoneType

        """
        if len(argv) > 1:
            self._process_protocol_v1(argv, ifile, ofile)
        else:
            self._process_protocol_v2(argv, ifile, ofile)

    def _map_input_header(self):
        metadata = self._metadata
        searchinfo = metadata.searchinfo
        self._input_header.update(
            allowStream=None,
            infoPath=os.path.join(searchinfo.dispatch_dir, 'info.csv'),
            keywords=None,
            preview=metadata.preview,
            realtime=searchinfo.earliest_time != 0 and searchinfo.latest_time != 0,
            search=searchinfo.search,
            sid=searchinfo.sid,
            splunkVersion=searchinfo.splunk_version,
            truncated=None)

    def _map_metadata(self, argv):
        source = SearchCommand._MetadataSource(argv, self._input_header, self.search_results_info)

        def _map(metadata_map):
            metadata = {}

            for name, value in metadata_map.iteritems():
                if isinstance(value, dict):
                    value = _map(value)
                else:
                    transform, extract = value
                    if extract is None:
                        value = None
                    else:
                        value = extract(source)
                        if not (value is None or transform is None):
                            value = transform(value)
                metadata[name] = value

            return ObjectView(metadata)

        self._metadata = _map(SearchCommand._metadata_map)

    _metadata_map = {
        'action':
            (lambda v: 'getinfo' if v == '__GETINFO__' else 'execute' if v == '__EXECUTE__' else None, lambda s: s.argv[1]),
        'preview':
            (bool, lambda s: s.input_header.get('preview')),
        'searchinfo': {
            'app':
                (lambda v: v.ppc_app, lambda s: s.search_results_info),
            'args':
                (None, lambda s: s.argv),
            'dispatch_dir':
                (os.path.dirname, lambda s: s.input_header.get('infoPath')),
            'earliest_time':
                (lambda v: float(v.rt_earliest) if len(v.rt_earliest) > 0 else 0.0, lambda s: s.search_results_info),
            'latest_time':
                (lambda v: float(v.rt_latest) if len(v.rt_latest) > 0 else 0.0, lambda s: s.search_results_info),
            'owner':
                (None, None),
            'raw_args':
                (None, lambda s: s.argv),
            'search':
                (unquote, lambda s: s.input_header.get('search')),
            'session_key':
                (lambda v: v.auth_token, lambda s: s.search_results_info),
            'sid':
                (None, lambda s: s.input_header.get('sid')),
            'splunk_version':
                (None, lambda s: s.input_header.get('splunkVersion')),
            'splunkd_uri':
                (lambda v: v.splunkd_uri, lambda s: s.search_results_info),
            'username':
                (lambda v: v.ppc_user, lambda s: s.search_results_info)}}

    _MetadataSource = namedtuple(b'Source', (b'argv', b'input_header', b'search_results_info'))

    def _prepare_protocol_v1(self, argv, ifile, ofile):

        debug = environment.splunklib_logger.debug

        # Provide as much context as possible in advance of parsing the command line and preparing for execution

        self._input_header.read(ifile)
        self._protocol_version = 1
        self._map_metadata(argv)

        debug('  metadata=%r, input_header=%r', self._metadata, self._input_header)

        try:
            tempfile.tempdir = self._metadata.searchinfo.dispatch_dir
        except AttributeError:
            raise RuntimeError('{}.metadata.searchinfo.dispatch_dir is undefined'.format(self.__class__.__name__))

        debug('  tempfile.tempdir=%r', tempfile.tempdir)

        CommandLineParser.parse(self, argv[2:])
        self.prepare()

        if self.record:
            self.record = False

            record_argv = [argv[0], argv[1], str(self._options), ' '.join(self.fieldnames)]
            ifile, ofile = self._prepare_recording(record_argv, ifile, ofile)
            self._record_writer.ofile = ofile
            ifile.record(str(self._input_header), '\n\n')

        if self.show_configuration:
            self.write_info(self.name + ' command configuration: ' + str(self._configuration))

        return ifile  # wrapped, if self.record is True

    def _prepare_recording(self, argv, ifile, ofile):

        # Create the recordings directory, if it doesn't already exist

        recordings = os.path.join(environment.splunk_home, 'var', 'run', 'splunklib.searchcommands', 'recordings')

        if not os.path.isdir(recordings):
            os.makedirs(recordings)

        # Create input/output recorders from ifile and ofile

        recording = os.path.join(recordings, self.__class__.__name__ + '-' + repr(time()) + '.' + self._metadata.action)
        ifile = Recorder(recording + '.input', ifile)
        ofile = Recorder(recording + '.output', ofile)

        # Archive the dispatch directory--if it exists--so that it can be used as a baseline in mocks)

        dispatch_dir = self._metadata.searchinfo.dispatch_dir

        if dispatch_dir is not None:  # __GETINFO__ action does not include a dispatch_dir
            root_dir, base_dir = os.path.split(dispatch_dir)
            make_archive(recording + '.dispatch_dir', 'gztar', root_dir, base_dir, logger=self.logger)

        # Save a splunk command line because it is useful for developing tests

        with open(recording + '.splunk_cmd', 'wb') as f:
            f.write('splunk cmd python '.encode())
            f.write(os.path.basename(argv[0]).encode())
            for arg in islice(argv, 1, len(argv)):
                f.write(' '.encode())
                f.write(arg.encode())

        return ifile, ofile

    def _process_protocol_v1(self, argv, ifile, ofile):

        debug = environment.splunklib_logger.debug
        class_name = self.__class__.__name__

        debug('%s.process started under protocol_version=1', class_name)
        self._record_writer = RecordWriterV1(ofile)

        # noinspection PyBroadException
        try:
            if argv[1] == '__GETINFO__':

                debug('Writing configuration settings')

                ifile = self._prepare_protocol_v1(argv, ifile, ofile)
                self._record_writer.write_record({
                    n: ','.join(v) if isinstance(v, (list, tuple)) else v for n, v in self._configuration.iteritems()})
                self.finish()

            elif argv[1] == '__EXECUTE__':

                debug('Executing')

                ifile = self._prepare_protocol_v1(argv, ifile, ofile)
                self._records = self._records_protocol_v1
                self._metadata.action = 'execute'
                self._execute(ifile, None)

            else:
                message = (
                    'Command {0} appears to be statically configured for search command protocol version 1 and static '
                    'configuration is unsupported by splunklib.searchcommands. Please ensure that '
                    'default/commands.conf contains this stanza:\n'
                    '[{0}]\n'
                    'filename = {1}\n'
                    'enableheader = true\n'
                    'outputheader = true\n'
                    'requires_srinfo = true\n'
                    'supports_getinfo = true\n'
                    'supports_multivalues = true\n'
                    'supports_rawargs = true'.format(self.name, os.path.basename(argv[0])))
                raise RuntimeError(message)

        except (SyntaxError, ValueError) as error:
            self.write_error(unicode(error))
            self.flush()
            exit(0)

        except SystemExit:
            self.flush()
            raise

        except:
            self._report_unexpected_error()
            self.flush()
            exit(1)

        debug('%s.process finished under protocol_version=1', class_name)

    def _process_protocol_v2(self, argv, ifile, ofile):
        """ Processes records on the `input stream optionally writing records to the output stream.

        :param ifile: Input file object.
        :type ifile: file or InputType

        :param ofile: Output file object.
        :type ofile: file or OutputType

        :return: :const:`None`

        """
        debug = environment.splunklib_logger.debug
        class_name = self.__class__.__name__

        debug('%s.process started under protocol_version=2', class_name)
        self._protocol_version = 2

        # Read search command metadata from splunkd
        # noinspection PyBroadException
        try:
            debug('Reading metadata')
            metadata, body = self._read_chunk(ifile)

            action = getattr(metadata, 'action', None)

            if action != 'getinfo':
                raise RuntimeError('Expected getinfo action, not {}'.format(action))

            if len(body) > 0:
                raise RuntimeError('Did not expect data for getinfo action')

            self._metadata = deepcopy(metadata)

            searchinfo = self._metadata.searchinfo

            searchinfo.earliest_time = float(searchinfo.earliest_time)
            searchinfo.latest_time = float(searchinfo.latest_time)
            searchinfo.search = unquote(searchinfo.search)

            self._map_input_header()

            debug('  metadata=%r, input_header=%r', self._metadata, self._input_header)

            try:
                tempfile.tempdir = self._metadata.searchinfo.dispatch_dir
            except AttributeError:
                raise RuntimeError('%s.metadata.searchinfo.dispatch_dir is undefined'.format(class_name))

            debug('  tempfile.tempdir=%r', tempfile.tempdir)
        except:
            self._record_writer = RecordWriterV2(ofile)
            self._report_unexpected_error()
            self.finish()
            exit(1)

        # Write search command configuration for consumption by splunkd
        # noinspection PyBroadException
        try:
            self._record_writer = RecordWriterV2(ofile, getattr(self._metadata, 'maxresultrows', None))
            self.fieldnames = []
            self.options.reset()

            args = self.metadata.searchinfo.args
            error_count = 0

            debug('Parsing arguments')

            if args and type(args) == list:
                for arg in args:
                    result = arg.split('=', 1)
                    if len(result) == 1:
                        self.fieldnames.append(result[0])
                    else:
                        name, value = result
                        try:
                            option = self.options[name]
                        except KeyError:
                            self.write_error('Unrecognized option: {}={}'.format(name, value))
                            error_count += 1
                            continue
                        try:
                            option.value = value
                        except ValueError:
                            self.write_error('Illegal value: {}={}'.format(name, value))
                            error_count += 1
                            continue

            missing = self.options.get_missing()

            if missing is not None:
                if len(missing) == 1:
                    self.write_error('A value for "{}" is required'.format(missing[0]))
                else:
                    self.write_error('Values for these required options are missing: {}'.format(', '.join(missing)))
                error_count += 1

            if error_count > 0:
                exit(1)

            debug('  command: %s', unicode(self))

            debug('Preparing for execution')
            self.prepare()

            if self.record:

                ifile, ofile = self._prepare_recording(argv, ifile, ofile)
                self._record_writer.ofile = ofile

                # Record the metadata that initiated this command after removing the record option from args/raw_args

                info = self._metadata.searchinfo

                for attr in 'args', 'raw_args':
                    setattr(info, attr, [arg for arg in getattr(info, attr) if not arg.startswith('record=')])

                metadata = MetadataEncoder().encode(self._metadata)
                ifile.record('chunked 1.0,', unicode(len(metadata)), ',0\n', metadata)

            if self.show_configuration:
                self.write_info(self.name + ' command configuration: ' + str(self._configuration))

            debug('  command configuration: %s', self._configuration)

        except SystemExit:
            self._record_writer.write_metadata(self._configuration)
            self.finish()
            raise
        except:
            self._record_writer.write_metadata(self._configuration)
            self._report_unexpected_error()
            self.finish()
            exit(1)

        self._record_writer.write_metadata(self._configuration)

        # Execute search command on data passing through the pipeline
        # noinspection PyBroadException
        try:
            debug('Executing under protocol_version=2')
            self._records = self._records_protocol_v2
            self._metadata.action = 'execute'
            self._execute(ifile, None)
        except SystemExit:
            self.finish()
            raise
        except:
            self._report_unexpected_error()
            self.finish()
            exit(1)

        debug('%s.process completed', class_name)

    def write_debug(self, message, *args):
        self._record_writer.write_message('DEBUG', message, *args)

    def write_error(self, message, *args):
        self._record_writer.write_message('ERROR', message, *args)

    def write_fatal(self, message, *args):
        self._record_writer.write_message('FATAL', message, *args)

    def write_info(self, message, *args):
        self._record_writer.write_message('INFO', message, *args)

    def write_warning(self, message, *args):
        self._record_writer.write_message('WARN', message, *args)

    def write_metric(self, name, value):
        """ Writes a metric that will be added to the search inspector.

        :param name: Name of the metric.
        :type name: basestring

        :param value: A 4-tuple containing the value of metric :param:`name` where

            value[0] = Elapsed seconds or :const:`None`.
            value[1] = Number of invocations or :const:`None`.
            value[2] = Input count or :const:`None`.
            value[3] = Output count or :const:`None`.

        The :data:`SearchMetric` type provides a convenient encapsulation of :param:`value`.
        The :data:`SearchMetric` type provides a convenient encapsulation of :param:`value`.

        :return: :const:`None`.

        """
        self._record_writer.write_metric(name, value)

    # P2 [ ] TODO: Support custom inspector values

    @staticmethod
    def _decode_list(mv):
        return [match.replace('$$', '$') for match in SearchCommand._encoded_value.findall(mv)]

    _encoded_value = re.compile(r'\$(?P<item>(?:\$\$|[^$])*)\$(?:;|$)')  # matches a single value in an encoded list

    def _execute(self, ifile, process):
        """ Default processing loop

        :param ifile: Input file object.
        :type ifile: file

        :param process: Bound method to call in processing loop.
        :type process: instancemethod

        :return: :const:`None`.
        :rtype: NoneType

        """
        self._record_writer.write_records(process(self._records(ifile)))
        self.finish()

    @staticmethod
    def _read_chunk(ifile):

        # noinspection PyBroadException
        try:
            header = ifile.readline()
        except Exception as error:
            raise RuntimeError('Failed to read transport header: {}'.format(error))

        if not header:
            return None

        match = SearchCommand._header.match(header)

        if match is None:
            raise RuntimeError('Failed to parse transport header: {}'.format(header))

        metadata_length, body_length = match.groups()
        metadata_length = int(metadata_length)
        body_length = int(body_length)

        try:
            metadata = ifile.read(metadata_length)
        except Exception as error:
            raise RuntimeError('Failed to read metadata of length {}: {}'.format(metadata_length, error))

        decoder = MetadataDecoder()

        try:
            metadata = decoder.decode(metadata)
        except Exception as error:
            raise RuntimeError('Failed to parse metadata of length {}: {}'.format(metadata_length, error))

        # if body_length <= 0:
        #     return metadata, ''

        try:
            body = ifile.read(body_length)
        except Exception as error:
            raise RuntimeError('Failed to read body of length {}: {}'.format(body_length, error))

        return metadata, body

    _header = re.compile(r'chunked\s+1.0\s*,\s*(\d+)\s*,\s*(\d+)\s*\n')

    def _records_protocol_v1(self, ifile):

        reader = csv.reader(ifile, dialect=CsvDialect)

        try:
            fieldnames = reader.next()
        except StopIteration:
            return

        mv_fieldnames = {name: name[len('__mv_'):] for name in fieldnames if name.startswith('__mv_')}

        if len(mv_fieldnames) == 0:
            for values in reader:
                yield OrderedDict(izip(fieldnames, values))
            return

        for values in reader:
            record = OrderedDict()
            for fieldname, value in izip(fieldnames, values):
                if fieldname.startswith('__mv_'):
                    if len(value) > 0:
                        record[mv_fieldnames[fieldname]] = self._decode_list(value)
                elif fieldname not in record:
                    record[fieldname] = value
            yield record

    def _records_protocol_v2(self, ifile):

        while True:
            result = self._read_chunk(ifile)

            if not result:
                return

            metadata, body = result
            action = getattr(metadata, 'action', None)

            if action != 'execute':
                raise RuntimeError('Expected execute action, not {}'.format(action))

            finished = getattr(metadata, 'finished', False)
            self._record_writer.is_flushed = False

            if len(body) > 0:
                reader = csv.reader(StringIO(body), dialect=CsvDialect)

                try:
                    fieldnames = reader.next()
                except StopIteration:
                    return

                mv_fieldnames = {name: name[len('__mv_'):] for name in fieldnames if name.startswith('__mv_')}

                if len(mv_fieldnames) == 0:
                    for values in reader:
                        yield OrderedDict(izip(fieldnames, values))
                else:
                    for values in reader:
                        record = OrderedDict()
                        for fieldname, value in izip(fieldnames, values):
                            if fieldname.startswith('__mv_'):
                                if len(value) > 0:
                                    record[mv_fieldnames[fieldname]] = self._decode_list(value)
                            elif fieldname not in record:
                                record[fieldname] = value
                        yield record

            if finished:
                return

            self.flush()

    def _report_unexpected_error(self):

        error_type, error, tb = sys.exc_info()
        origin = tb

        while origin.tb_next is not None:
            origin = origin.tb_next

        filename = origin.tb_frame.f_code.co_filename
        lineno = origin.tb_lineno
        message = '{0} at "{1}", line {2:d} : {3}'.format(error_type.__name__, filename, lineno, error)

        environment.splunklib_logger.error(message + '\nTraceback:\n' + ''.join(traceback.format_tb(tb)))
        self.write_error(message)

    # endregion

    # region Types

    class ConfigurationSettings(object):
        """ Represents the configuration settings common to all :class:`SearchCommand` classes.

        """
        def __init__(self, command):
            self.command = command

        def __repr__(self):
            """ Converts the value of this instance to its string representation.

            The value of this ConfigurationSettings instance is represented as a string of comma-separated
            :code:`(name, value)` pairs.

            :return: String representation of this instance

            """
            definitions = type(self).configuration_setting_definitions
            settings = imap(
                lambda setting: repr((setting.name, setting.__get__(self), setting.supporting_protocols)), definitions)
            return '[' + ', '.join(settings) + ']'

        def __str__(self):
            """ Converts the value of this instance to its string representation.

            The value of this ConfigurationSettings instance is represented as a string of comma-separated
            :code:`name=value` pairs. Items with values of :const:`None` are filtered from the list.

            :return: String representation of this instance

            """
            text = ', '.join(imap(lambda (name, value): name + '=' + json_encode_string(unicode(value)), self.iteritems()))
            return text

        # region Methods

        @classmethod
        def fix_up(cls, command_class):
            """ Adjusts and checks this class and its search command class.

            Derived classes typically override this method. It is used by the :decorator:`Configuration` decorator to
            fix up the :class:`SearchCommand` class it adorns. This method is overridden by :class:`EventingCommand`,
            :class:`GeneratingCommand`, :class:`ReportingCommand`, and :class:`StreamingCommand`, the base types for
            all other search commands.

            :param command_class: Command class targeted by this class

            """
            return

        def iteritems(self):
            definitions = type(self).configuration_setting_definitions
            version = self.command.protocol_version
            return ifilter(
                lambda (name, value): value is not None, imap(
                    lambda setting: (setting.name, setting.__get__(self)), ifilter(
                        lambda setting: setting.is_supported_by_protocol(version), definitions)))

        pass  # endregion

    pass  # endregion


SearchMetric = namedtuple(b'SearchMetric', (b'elapsed_seconds', b'invocation_count', b'input_count', b'output_count'))


def dispatch(command_class, argv=sys.argv, input_file=sys.stdin, output_file=sys.stdout, module_name=None):
    """ Instantiates and executes a search command class

    This function implements a `conditional script stanza <http://goo.gl/OFaox6>`_ based on the value of
    :code:`module_name`::

        if module_name is None or module_name == '__main__':
            # execute command

    Call this function at module scope with :code:`module_name=__name__`, if you would like your module to act as either
    a reusable module or a standalone program. Otherwise, if you wish this function to unconditionally instantiate and
    execute :code:`command_class`, pass :const:`None` as the value of :code:`module_name`.

    :param command_class: Search command class to instantiate and execute.
    :type command_class: type
    :param argv: List of arguments to the command.
    :type argv: list or tuple
    :param input_file: File from which the command will read data.
    :type input_file: :code:`file`
    :param output_file: File to which the command will write data.
    :type output_file: :code:`file`
    :param module_name: Name of the module calling :code:`dispatch` or :const:`None`.
    :type module_name: :code:`basestring`
    :returns: :const:`None`

    **Example**

    .. code-block:: python
        :linenos:

        #!/usr/bin/env python
        from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
        @Configuration()
        class SomeStreamingCommand(StreamingCommand):
            ...
            def stream(records):
                ...
        dispatch(SomeStreamingCommand, module_name=__name__)

    Dispatches the :code:`SomeStreamingCommand`, if and only if :code:`__name__` is equal to :code:`'__main__'`.

    **Example**

    .. code-block:: python
        :linenos:

        from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
        @Configuration()
        class SomeStreamingCommand(StreamingCommand):
            ...
            def stream(records):
                ...
        dispatch(SomeStreamingCommand)

    Unconditionally dispatches :code:`SomeStreamingCommand`.

    """
    assert issubclass(command_class, SearchCommand)

    if module_name is None or module_name == '__main__':
        command_class().process(argv, input_file, output_file)
                                                                                                                                                                                                                                                                                               humanize/bin/splunklib/searchcommands/streaming_command.py                                          000644  000765  000000  00000014452 12674041006 025464  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import ifilter, imap

from .decorators import ConfigurationSetting
from .search_command import SearchCommand


class StreamingCommand(SearchCommand):
    """ Applies a transformation to search results as they travel through the streams pipeline.

    Streaming commands typically filter, augment, or update, search result records. Splunk will send them in batches of
    up to 50,000 records. Hence, a search command must be prepared to be invoked many times during the course of
    pipeline processing. Each invocation should produce a set of results independently usable by downstream processors.

    By default Splunk may choose to run a streaming command locally on a search head and/or remotely on one or more
    indexers concurrently. The size and frequency of the search result batches sent to the command will vary based
    on scheduling considerations.

    StreamingCommand configuration
    ==============================

    You can configure your command for operation under Search Command Protocol (SCP) version 1 or 2. SCP 2 requires
    Splunk 6.3 or later.

    """
    # region Methods

    def stream(self, records):
        """ Generator function that processes and yields event records to the Splunk stream pipeline.

        You must override this method.

        """
        raise NotImplementedError('StreamingCommand.stream(self, records)')

    def _execute(self, ifile, process):
        SearchCommand._execute(self, ifile, self.stream)

    # endregion

    class ConfigurationSettings(SearchCommand.ConfigurationSettings):
        """ Represents the configuration settings that apply to a :class:`StreamingCommand`.

        """
        # region SCP v1/v2 properties

        required_fields = ConfigurationSetting(doc='''
            List of required fields for this search which back-propagates to the generating search.

            Setting this value enables selected fields mode under SCP 2. Under SCP 1 you must also specify
            :code:`clear_required_fields=True` to enable selected fields mode. To explicitly select all fields,
            specify a value of :const:`['*']`. No error is generated if a specified field is missing.

            Default: :const:`None`, which implicitly selects all fields.

            Supported by: SCP 1, SCP 2

            ''')

        # endregion

        # region SCP v1 properties

        clear_required_fields = ConfigurationSetting(value=False, doc='''
            :const:`True`, if required_fields represent the *only* fields required.

            If :const:`False`, required_fields are additive to any fields that may be required by subsequent commands.
            In most cases, :const:`False` is appropriate for streaming commands.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        local = ConfigurationSetting(value=False, doc='''
            :const:`True`, if the command should run locally on the search head.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        overrides_timeorder = ConfigurationSetting(doc='''
            :const:`True`, if the command changes the order of events with respect to time.

            Default: :const:`False`

            Supported by: SCP 1

            ''')

        streaming = ConfigurationSetting(readonly=True, value=True, doc='''
            Specifies that the command is streamable.

            Fixed: :const:`True`

            Supported by: SCP 1

            ''')

        # endregion

        # region SCP v2 Properties

        distributed = ConfigurationSetting(value=True, doc='''
            :const:`True`, if this command should be distributed to indexers.

            Under SCP 1 you must either specify `local = False` or include this line in commands.conf_, if this command
            should be distributed to indexers.

            ..code:
                local = true

            Default: :const:`True`

            Supported by: SCP 2

            .. commands.conf_: http://docs.splunk.com/Documentation/Splunk/latest/Admin/Commandsconf

            ''')

        maxinputs = ConfigurationSetting(doc='''
            Specifies the maximum number of events that can be passed to the command for each invocation.

            This limit cannot exceed the value of `maxresultrows` in limits.conf. Under SCP 1 you must specify this
            value in commands.conf_.

            Default: The value of `maxresultrows`.

            Supported by: SCP 2

            ''')

        type = ConfigurationSetting(readonly=True, value='streaming', doc='''
            Command type name.

            Fixed: :const:`'streaming'`

            Supported by: SCP 2

            ''')

        # endregion

        # region Methods

        @classmethod
        def fix_up(cls, command):
            """ Verifies :code:`command` class structure.

            """
            if command.stream == StreamingCommand.stream:
                raise AttributeError('No StreamingCommand.stream override')
            return

        def iteritems(self):
            iteritems = SearchCommand.ConfigurationSettings.iteritems(self)
            version = self.command.protocol_version
            if version == 1:
                if self.required_fields is None:
                    iteritems = ifilter(lambda (name, value): name != 'clear_required_fields', iteritems)
            else:
                iteritems = ifilter(lambda (name, value): name != 'distributed', iteritems)
                if self.distributed:
                    iteritems = imap(
                        lambda (name, value): (name, 'stateful') if name == 'type' else (name, value), iteritems)
            return iteritems

        # endregion
                                                                                                                                                                                                                      humanize/bin/splunklib/searchcommands/validators.py                                                 000644  000765  000000  00000026326 12674041006 024150  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # coding=utf-8
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from json.encoder import encode_basestring_ascii as json_encode_string
from collections import namedtuple
from cStringIO import StringIO
from io import open
import csv
import os
import re


class Validator(object):
    """ Base class for validators that check and format search command options.

    You must inherit from this class and override :code:`Validator.__call__` and
    :code:`Validator.format`. :code:`Validator.__call__` should convert the
    value it receives as argument and then return it or raise a
    :code:`ValueError`, if the value will not convert.

    :code:`Validator.format` should return a human readable version of the value
    it receives as argument the same way :code:`str` does.

    """
    def __call__(self, value):
        raise NotImplementedError()

    def format(self, value):
        raise NotImplementedError()


class Boolean(Validator):
    """ Validates Boolean option values.

    """
    truth_values = {
        '1': True, '0': False,
        't': True, 'f': False,
        'true': True, 'false': False,
        'y': True, 'n': False,
        'yes': True, 'no': False
    }

    def __call__(self, value):
        if not (value is None or isinstance(value, bool)):
            value = unicode(value).lower()
            if value not in Boolean.truth_values:
                raise ValueError('Unrecognized truth value: {0}'.format(value))
            value = Boolean.truth_values[value]
        return value

    def format(self, value):
        return None if value is None else 't' if value else 'f'


class Code(Validator):
    """ Validates code option values.

    This validator compiles an option value into a Python code object that can be executed by :func:`exec` or evaluated
    by :func:`eval`. The value returned is a :func:`namedtuple` with two members: object, the result of compilation, and
    source, the original option value.

    """
    def __init__(self, mode='eval'):
        """
        :param mode: Specifies what kind of code must be compiled; it can be :const:`'exec'`, if source consists of a
        sequence of statements, :const:`'eval'`, if it consists of a single expression, or :const:`'single'` if it
        consists of a single interactive statement. In the latter case, expression statements that evaluate to
        something other than :const:`None` will be printed.
        :type mode: unicode or bytes

        """
        self._mode = mode

    def __call__(self, value):
        if value is None:
            return None
        try:
            return Code.object(compile(value, 'string', self._mode), unicode(value))
        except (SyntaxError, TypeError) as error:
            raise ValueError(error.message)

    def format(self, value):
        return None if value is None else value.source

    object = namedtuple(b'Code', (b'object', 'source'))


class Fieldname(Validator):
    """ Validates field name option values.

    """
    pattern = re.compile(r'''[_.a-zA-Z-][_.a-zA-Z0-9-]*$''')

    def __call__(self, value):
        if value is not None:
            value = unicode(value)
            if Fieldname.pattern.match(value) is None:
                raise ValueError('Illegal characters in fieldname: {}'.format(value))
        return value

    def format(self, value):
        return value


class File(Validator):
    """ Validates file option values.

    """
    def __init__(self, mode='rt', buffering=None, directory=None):
        self.mode = mode
        self.buffering = buffering
        self.directory = File._var_run_splunk if directory is None else directory

    def __call__(self, value):

        if value is None:
            return value

        path = unicode(value)

        if not os.path.isabs(path):
            path = os.path.join(self.directory, path)

        try:
            value = open(path, self.mode) if self.buffering is None else open(path, self.mode, self.buffering)
        except IOError as error:
            raise ValueError('Cannot open {0} with mode={1} and buffering={2}: {3}'.format(
                value, self.mode, self.buffering, error))

        return value

    def format(self, value):
        return None if value is None else value.name

    _var_run_splunk = os.path.join(
        os.environ['SPLUNK_HOME'] if 'SPLUNK_HOME' in os.environ else os.getcwdu(), 'var', 'run', 'splunk')


class Integer(Validator):
    """ Validates integer option values.

    """
    def __init__(self, minimum=None, maximum=None):
        if minimum is not None and maximum is not None:
            def check_range(value):
                if not (minimum <= value <= maximum):
                    raise ValueError('Expected integer in the range [{0},{1}], not {2}'.format(minimum, maximum, value))
                return
        elif minimum is not None:
            def check_range(value):
                if value < minimum:
                    raise ValueError('Expected integer in the range [{0},+∞], not {1}'.format(minimum, value))
                return
        elif maximum is not None:
            def check_range(value):
                if value > maximum:
                    raise ValueError('Expected integer in the range [-∞,{0}], not {1}'.format(maximum, value))
                return
        else:
            def check_range(value):
                return

        self.check_range = check_range
        return

    def __call__(self, value):
        if value is None:
            return None
        try:
            value = long(value)
        except ValueError:
            raise ValueError('Expected integer value, not {}'.format(json_encode_string(value)))

        self.check_range(value)
        return value

    def format(self, value):
        return None if value is None else unicode(long(value))


class Duration(Validator):
    """ Validates duration option values.

    """
    def __call__(self, value):

        if value is None:
            return None

        p = value.split(':', 2)
        result = None
        _60 = Duration._60
        _unsigned = Duration._unsigned

        try:
            if len(p) == 1:
                result = _unsigned(p[0])
            if len(p) == 2:
                result = 60 * _unsigned(p[0]) + _60(p[1])
            if len(p) == 3:
                result = 3600 * _unsigned(p[0]) + 60 * _60(p[1]) + _60(p[2])
        except ValueError:
            raise ValueError('Invalid duration value: {0}'.format(value))

        return result

    def format(self, value):

        if value is None:
            return None

        value = int(value)

        s = value % 60
        m = value // 60 % 60
        h = value // (60 * 60)

        return '{0:02d}:{1:02d}:{2:02d}'.format(h, m, s)

    _60 = Integer(0, 59)
    _unsigned = Integer(0)


class List(Validator):
    """ Validates a list of strings

    """
    class Dialect(csv.Dialect):
        """ Describes the properties of list option values. """
        strict = True
        delimiter = b','
        quotechar = b'"'
        doublequote = True
        lineterminator = b'\n'
        skipinitialspace = True
        quoting = csv.QUOTE_MINIMAL

    def __init__(self, validator=None):
        if not (validator is None or isinstance(validator, Validator)):
            raise ValueError('Expected a Validator instance or None for validator, not {}', repr(validator))
        self._validator = validator

    def __call__(self, value):

        if value is None or isinstance(value, list):
            return value

        try:
            value = csv.reader([value], self.Dialect).next()
        except csv.Error as error:
            raise ValueError(error)

        if self._validator is None:
            return value

        try:
            for index, item in enumerate(value):
                value[index] = self._validator(item)
        except ValueError as error:
            raise ValueError('Could not convert item {}: {}'.format(index, error))

        return value

    def format(self, value):
        output = StringIO()
        writer = csv.writer(output, List.Dialect)
        writer.writerow(value)
        value = output.getvalue()
        return value[:-1]


class Map(Validator):
    """ Validates map option values.

    """
    def __init__(self, **kwargs):
        self.membership = kwargs

    def __call__(self, value):

        if value is None:
            return None

        value = unicode(value)

        if value not in self.membership:
            raise ValueError('Unrecognized value: {0}'.format(value))

        return self.membership[value]

    def format(self, value):
        return None if value is None else self.membership.keys()[self.membership.values().index(value)]


class Match(Validator):
    """ Validates that a value matches a regular expression pattern.

    """
    def __init__(self, name, pattern, flags=0):
        self.name = unicode(name)
        self.pattern = re.compile(pattern, flags)

    def __call__(self, value):
        if value is None:
            return None
        value = unicode(value)
        if self.pattern.match(value) is None:
            raise ValueError('Expected {}, not {}'.format(self.name, json_encode_string(value)))
        return value

    def format(self, value):
        return None if value is None else unicode(value)


class OptionName(Validator):
    """ Validates option names.

    """
    pattern = re.compile(r'''(?=\w)[^\d]\w*$''', re.UNICODE)

    def __call__(self, value):
        if value is not None:
            value = unicode(value)
            if OptionName.pattern.match(value) is None:
                raise ValueError('Illegal characters in option name: {}'.format(value))
        return value

    def format(self, value):
        return None if value is None else unicode(value)


class RegularExpression(Validator):
    """ Validates regular expression option values.

    """
    def __call__(self, value):
        if value is None:
            return None
        try:
            value = re.compile(unicode(value))
        except re.error as error:
            raise ValueError('{}: {}'.format(unicode(error).capitalize(), value))
        return value

    def format(self, value):
        return None if value is None else value.pattern


class Set(Validator):
    """ Validates set option values.

    """
    def __init__(self, *args):
        self.membership = set(args)

    def __call__(self, value):
        if value is None:
            return None
        value = unicode(value)
        if value not in self.membership:
            raise ValueError('Unrecognized value: {}'.format(value))
        return value

    def format(self, value):
        return self.__call__(value)


__all__ = ['Boolean', 'Code', 'Duration', 'File', 'Integer', 'List', 'Map', 'RegularExpression', 'Set']
                                                                                                                                                                                                                                                                                                          humanize/bin/splunklib/modularinput/__init__.py                                                     000755  000765  000000  00000000610 12674041006 023262  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         """The following imports allow these classes to be imported via
the splunklib.modularinput package like so:

from splunklib.modularinput import *
"""
from argument import Argument
from event import Event
from event_writer import EventWriter
from input_definition import InputDefinition
from scheme import Scheme
from script import Script
from validation_definition import ValidationDefinition                                                                                                                        humanize/bin/splunklib/modularinput/argument.py                                                     000755  000765  000000  00000010106 12674041006 023346  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET

class Argument(object):
    """Class representing an argument to a modular input kind.

    ``Argument`` is meant to be used with ``Scheme`` to generate an XML 
    definition of the modular input kind that Splunk understands.

    ``name`` is the only required parameter for the constructor.

        **Example with least parameters**::

            arg1 = Argument(name="arg1")

        **Example with all parameters**::

            arg2 = Argument(
                name="arg2",
                description="This is an argument with lots of parameters",
                validation="is_pos_int('some_name')",
                data_type=Argument.data_type_number,
                required_on_edit=True,
                required_on_create=True
            )
    """

    # Constant values, do not change.
    # These should be used for setting the value of an Argument object's data_type field.
    data_type_boolean = "BOOLEAN"
    data_type_number = "NUMBER"
    data_type_string = "STRING"

    def __init__(self, name, description=None, validation=None,
                 data_type=data_type_string, required_on_edit=False, required_on_create=False, title=None):
        """
        :param name: ``string``, identifier for this argument in Splunk.
        :param description: ``string``, human-readable description of the argument.
        :param validation: ``string`` specifying how the argument should be validated, if using internal validation.
        If using external validation, this will be ignored.
        :param data_type: ``string``, data type of this field; use the class constants.
        "data_type_boolean", "data_type_number", or "data_type_string".
        :param required_on_edit: ``Boolean``, whether this arg is required when editing an existing modular input of this kind.
        :param required_on_create: ``Boolean``, whether this arg is required when creating a modular input of this kind.
        :param title: ``String``, a human-readable title for the argument.
        """
        self.name = name
        self.description = description
        self.validation = validation
        self.data_type = data_type
        self.required_on_edit = required_on_edit
        self.required_on_create = required_on_create
        self.title = title

    def add_to_document(self, parent):
        """Adds an ``Argument`` object to this ElementTree document.

        Adds an <arg> subelement to the parent element, typically <args>
        and sets up its subelements with their respective text.

        :param parent: An ``ET.Element`` to be the parent of a new <arg> subelement
        :returns: An ``ET.Element`` object representing this argument.
        """
        arg = ET.SubElement(parent, "arg")
        arg.set("name", self.name)

        if self.title is not None:
            ET.SubElement(arg, "title").text = self.title

        if self.description is not None:
            ET.SubElement(arg, "description").text = self.description

        if self.validation is not None:
            ET.SubElement(arg, "validation").text = self.validation

        # add all other subelements to this Argument, represented by (tag, text)
        subelements = [
            ("data_type", self.data_type),
            ("required_on_edit", self.required_on_edit),
            ("required_on_create", self.required_on_create)
        ]

        for name, value in subelements:
            ET.SubElement(arg, name).text = str(value).lower()

        return arg                                                                                                                                                                                                                                                                                                                                                                                                                                                          humanize/bin/splunklib/modularinput/event.py                                                        000755  000765  000000  00000010211 12674041006 022642  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

try:
    import xml.etree.cElementTree as ET
except ImportError as ie:
    import xml.etree.ElementTree as ET

class Event(object):
    """Represents an event or fragment of an event to be written by this modular input to Splunk.

    To write an input to a stream, call the ``write_to`` function, passing in a stream.
    """
    def __init__(self, data=None, stanza=None, time=None, host=None, index=None, source=None,
                 sourcetype=None, done=True, unbroken=True):
        """There are no required parameters for constructing an Event

        **Example with minimal configuration**::

            my_event = Event(
                data="This is a test of my new event.",
                stanza="myStanzaName",
                time="%.3f" % 1372187084.000
            )

        **Example with full configuration**::

            excellent_event = Event(
                data="This is a test of my excellent event.",
                stanza="excellenceOnly",
                time="%.3f" % 1372274622.493,
                host="localhost",
                index="main",
                source="Splunk",
                sourcetype="misc",
                done=True,
                unbroken=True
            )

        :param data: ``string``, the event's text.
        :param stanza: ``string``, name of the input this event should be sent to.
        :param time: ``float``, time in seconds, including up to 3 decimal places to represent milliseconds.
        :param host: ``string``, the event's host, ex: localhost.
        :param index: ``string``, the index this event is specified to write to, or None if default index.
        :param source: ``string``, the source of this event, or None to have Splunk guess.
        :param sourcetype: ``string``, source type currently set on this event, or None to have Splunk guess.
        :param done: ``boolean``, is this a complete ``Event``? False if an ``Event`` fragment.
        :param unbroken: ``boolean``, Is this event completely encapsulated in this ``Event`` object?
        """
        self.data = data
        self.done = done
        self.host = host
        self.index = index
        self.source = source
        self.sourceType = sourcetype
        self.stanza = stanza
        self.time = time
        self.unbroken = unbroken

    def write_to(self, stream):
        """Write an XML representation of self, an ``Event`` object, to the given stream.

        The ``Event`` object will only be written if its data field is defined,
        otherwise a ``ValueError`` is raised.

        :param stream: stream to write XML to.
        """
        if self.data is None:
            raise ValueError("Events must have at least the data field set to be written to XML.")

        event = ET.Element("event")
        if self.stanza is not None:
            event.set("stanza", self.stanza)
        event.set("unbroken", str(int(self.unbroken)))

        # if a time isn't set, let Splunk guess by not creating a <time> element
        if self.time is not None:
            ET.SubElement(event, "time").text = str(self.time)

        # add all other subelements to this Event, represented by (tag, text)
        subelements = [
            ("source", self.source),
            ("sourcetype", self.sourceType),
            ("index", self.index),
            ("host", self.host),
            ("data", self.data)
        ]
        for node, value in subelements:
            if value is not None:
                ET.SubElement(event, node).text = value

        if self.done:
            ET.SubElement(event, "done")

        stream.write(ET.tostring(event))
        stream.flush()                                                                                                                                                                                                                                                                                                                                                                                       humanize/bin/splunklib/modularinput/event_writer.py                                                 000755  000765  000000  00000005244 12674041006 024250  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys

from splunklib.modularinput.event import ET

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class EventWriter(object):
    """``EventWriter`` writes events and error messages to Splunk from a modular input.

    Its two important methods are ``writeEvent``, which takes an ``Event`` object,
    and ``log``, which takes a severity and an error message.
    """

    # Severities that Splunk understands for log messages from modular inputs.
    # Do not change these
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

    def __init__(self, output = sys.stdout, error = sys.stderr):
        """
        :param output: Where to write the output; defaults to sys.stdout.
        :param error: Where to write any errors; defaults to sys.stderr.
        """
        self._out = output
        self._err = error

        # has the opening <stream> tag been written yet?
        self.header_written = False

    def write_event(self, event):
        """Writes an ``Event`` object to Splunk.

        :param event: An ``Event`` object.
        """

        if not self.header_written:
            self._out.write("<stream>")
            self.header_written = True

        event.write_to(self._out)

    def log(self, severity, message):
        """Logs messages about the state of this modular input to Splunk.
        These messages will show up in Splunk's internal logs.

        :param severity: ``string``, severity of message, see severities defined as class constants.
        :param message: ``string``, message to log.
        """

        self._err.write("%s %s\n" % (severity, message))
        self._err.flush()

    def write_xml_document(self, document):
        """Writes a string representation of an
        ``ElementTree`` object to the output stream.

        :param document: An ``ElementTree`` object.
        """
        self._out.write(ET.tostring(document))
        self._out.flush()

    def close(self):
        """Write the closing </stream> tag to make this XML well formed."""
        self._out.write("</stream>")                                                                                                                                                                                                                                                                                                                                                            humanize/bin/splunklib/modularinput/input_definition.py                                             000755  000765  000000  00000003470 12674041006 025101  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

try:
    import xml.etree.cElementTree as ET
except ImportError as ie:
    import xml.etree.ElementTree as ET

from utils import parse_xml_data

class InputDefinition:
    """``InputDefinition`` encodes the XML defining inputs that Splunk passes to
    a modular input script.

     **Example**::

        i = InputDefinition()

    """
    def __init__ (self):
        self.metadata = {}
        self.inputs = {}

    def __eq__(self, other):
        if not isinstance(other, InputDefinition):
            return False
        return self.metadata == other.metadata and self.inputs == other.inputs

    @staticmethod
    def parse(stream):
        """Parse a stream containing XML into an ``InputDefinition``.

        :param stream: stream containing XML to parse.
        :return: definition: an ``InputDefinition`` object.
        """
        definition = InputDefinition()

        # parse XML from the stream, then get the root node
        root = ET.parse(stream).getroot()

        for node in root:
            if node.tag == "configuration":
                # get config for each stanza
                definition.inputs = parse_xml_data(node, "stanza")
            else:
                definition.metadata[node.tag] = node.text

        return definition                                                                                                                                                                                                        humanize/bin/splunklib/modularinput/scheme.py                                                       000755  000765  000000  00000005737 12674041006 023006  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class Scheme(object):
    """Class representing the metadata for a modular input kind.

    A ``Scheme`` specifies a title, description, several options of how Splunk should run modular inputs of this
    kind, and a set of arguments which define a particular modular input's properties.

    The primary use of ``Scheme`` is to abstract away the construction of XML to feed to Splunk.
    """

    # Constant values, do not change
    # These should be used for setting the value of a Scheme object's streaming_mode field.
    streaming_mode_simple = "SIMPLE"
    streaming_mode_xml = "XML"

    def __init__(self, title):
        """
        :param title: ``string`` identifier for this Scheme in Splunk.
        """
        self.title = title
        self.description = None
        self.use_external_validation = True
        self.use_single_instance = False
        self.streaming_mode = Scheme.streaming_mode_xml

        # list of Argument objects, each to be represented by an <arg> tag
        self.arguments = []

    def add_argument(self, arg):
        """Add the provided argument, ``arg``, to the ``self.arguments`` list.

        :param arg: An ``Argument`` object to add to ``self.arguments``.
        """
        self.arguments.append(arg)

    def to_xml(self):
        """Creates an ``ET.Element`` representing self, then returns it.

        :returns root, an ``ET.Element`` representing this scheme.
        """
        root = ET.Element("scheme")

        ET.SubElement(root, "title").text = self.title

        # add a description subelement if it's defined
        if self.description is not None:
            ET.SubElement(root, "description").text = self.description

        # add all other subelements to this Scheme, represented by (tag, text)
        subelements = [
            ("use_external_validation", self.use_external_validation),
            ("use_single_instance", self.use_single_instance),
            ("streaming_mode", self.streaming_mode)
        ]
        for name, value in subelements:
            ET.SubElement(root, name).text = str(value).lower()

        endpoint = ET.SubElement(root, "endpoint")

        args = ET.SubElement(endpoint, "args")

        # add arguments as subelements to the <args> element
        for arg in self.arguments:
            arg.add_to_document(args)

        return root                                 humanize/bin/splunklib/modularinput/script.py                                                       000755  000765  000000  00000014706 12674041006 023042  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from abc import ABCMeta, abstractmethod
from urlparse import urlsplit
import sys

from splunklib.client import Service
from splunklib.modularinput.event_writer import EventWriter
from splunklib.modularinput.input_definition import InputDefinition
from splunklib.modularinput.validation_definition import ValidationDefinition

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class Script(object):
    """An abstract base class for implementing modular inputs.

    Subclasses should override ``get_scheme``, ``stream_events``,
    and optionally ``validate_input`` if the modular input uses
    external validation.

    The ``run`` function is used to run modular inputs; it typically should
    not be overridden.
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        self._input_definition = None
        self._service = None

    def run(self, args):
        """Runs this modular input

        :param args: List of command line arguments passed to this script.
        :returns: An integer to be used as the exit value of this program.
        """

        # call the run_script function, which handles the specifics of running
        # a modular input
        return self.run_script(args, EventWriter(), sys.stdin)

    def run_script(self, args, event_writer, input_stream):
        """Handles all the specifics of running a modular input

        :param args: List of command line arguments passed to this script.
        :param event_writer: An ``EventWriter`` object for writing events.
        :param input_stream: An input stream for reading inputs.
        :returns: An integer to be used as the exit value of this program.
        """

        try:
            if len(args) == 1:
                # This script is running as an input. Input definitions will be
                # passed on stdin as XML, and the script will write events on
                # stdout and log entries on stderr.
                self._input_definition = InputDefinition.parse(input_stream)
                self.stream_events(self._input_definition, event_writer)
                event_writer.close()
                return 0

            elif str(args[1]).lower() == "--scheme":
                # Splunk has requested XML specifying the scheme for this
                # modular input Return it and exit.
                scheme = self.get_scheme()
                if scheme is None:
                    event_writer.log(
                        EventWriter.FATAL,
                        "Modular input script returned a null scheme.")
                    return 1
                else:
                    event_writer.write_xml_document(scheme.to_xml())
                    return 0

            elif args[1].lower() == "--validate-arguments":
                validation_definition = ValidationDefinition.parse(input_stream)
                try:
                    self.validate_input(validation_definition)
                    return 0
                except Exception as e:
                    root = ET.Element("error")
                    ET.SubElement(root, "message").text = str(e)
                    event_writer.write_xml_document(root)

                    return 1
            else:
                err_string = "ERROR Invalid arguments to modular input script:" + ' '.join(
                    args)
                event_writer._err.write(err_string)

        except Exception as e:
            err_string = EventWriter.ERROR + str(e.message)
            event_writer._err.write(err_string)
            return 1

    @property
    def service(self):
        """ Returns a Splunk service object for this script invocation.

        The service object is created from the Splunkd URI and session key
        passed to the command invocation on the modular input stream. It is
        available as soon as the :code:`Script.stream_events` method is
        called.

        :return: :class:splunklib.client.Service. A value of None is returned,
        if you call this method before the :code:`Script.stream_events` method
        is called.

        """
        if self._service is not None:
            return self._service

        if self._input_definition is None:
            return None

        splunkd_uri = self._input_definition.metadata["server_uri"]
        session_key = self._input_definition.metadata["session_key"]

        splunkd = urlsplit(splunkd_uri, allow_fragments=False)

        self._service = Service(
            scheme=splunkd.scheme,
            host=splunkd.hostname,
            port=splunkd.port,
            token=session_key,
        )

        return self._service

    @abstractmethod
    def get_scheme(self):
        """The scheme defines the parameters understood by this modular input.

        :return: a ``Scheme`` object representing the parameters for this modular input.
        """

    def validate_input(self, definition):
        """Handles external validation for modular input kinds.

        When Splunk calls a modular input script in validation mode, it will
        pass in an XML document giving information about the Splunk instance (so
        you can call back into it if needed) and the name and parameters of the
        proposed input.

        If this function does not throw an exception, the validation is assumed
        to succeed. Otherwise any errors thrown will be turned into a string and
        logged back to Splunk.

        The default implementation always passes.

        :param definition: The parameters for the proposed input passed by splunkd.
        """
        pass

    @abstractmethod
    def stream_events(self, inputs, ew):
        """The method called to stream events into Splunk. It should do all of its output via
        EventWriter rather than assuming that there is a console attached.

        :param inputs: An ``InputDefinition`` object.
        :param ew: An object with methods to write events and log messages to Splunk.
        """
                                                          humanize/bin/splunklib/modularinput/utils.py                                                        000755  000765  000000  00000005006 12674041006 022667  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# File for utility functions

def xml_compare(expected, found):
    """Checks equality of two ``ElementTree`` objects.

    :param expected: An ``ElementTree`` object.
    :param found: An ``ElementTree`` object.
    :return: ``Boolean``, whether the two objects are equal.
    """

    # if comparing the same ET object
    if expected == found:
        return True

    # compare element attributes, ignoring order
    if set(expected.items()) != set(found.items()):
        return False

    # check for equal number of children
    expected_children = list(expected)
    found_children = list(found)
    if len(expected_children) != len(found_children):
        return False

    # compare children
    if not all([xml_compare(a, b) for a, b in zip(expected_children, found_children)]):
        return False

    # compare elements, if there is no text node, return True
    if (expected.text is None or expected.text.strip() == "") \
        and (found.text is None or found.text.strip() == ""):
        return True
    else:
        return expected.tag == found.tag and expected.text == found.text \
            and expected.attrib == found.attrib

def parse_parameters(param_node):
    if param_node.tag == "param":
        return param_node.text
    elif param_node.tag == "param_list":
        parameters = []
        for mvp in param_node:
            parameters.append(mvp.text)
        return parameters
    else:
        raise ValueError("Invalid configuration scheme, %s tag unexpected." % param_node.tag)

def parse_xml_data(parent_node, child_node_tag):
    data = {}
    for child in parent_node:
        if child.tag == child_node_tag:
            if child_node_tag == "stanza":
                data[child.get("name")] = {}
                for param in child:
                    data[child.get("name")][param.get("name")] = parse_parameters(param)
        elif "item" == parent_node.tag:
            data[child.get("name")] = parse_parameters(child)
    return data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          humanize/bin/splunklib/modularinput/validation_definition.py                                        000755  000765  000000  00000005234 12674041006 026074  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


try:
    import xml.etree.cElementTree as ET
except ImportError as ie:
    import xml.etree.ElementTree as ET

from utils import parse_xml_data


class ValidationDefinition(object):
    """This class represents the XML sent by Splunk for external validation of a
    new modular input.

    **Example**::

    ``v = ValidationDefinition()``

    """
    def __init__(self):
        self.metadata = {}
        self.parameters = {}

    def __eq__(self, other):
        if not isinstance(other, ValidationDefinition):
            return False
        return self.metadata == other.metadata and self.parameters == other.parameters

    @staticmethod
    def parse(stream):
        """Creates a ``ValidationDefinition`` from a provided stream containing XML.

        The XML typically will look like this:

        ``<items>``
        ``   <server_host>myHost</server_host>``
        ``     <server_uri>https://127.0.0.1:8089</server_uri>``
        ``     <session_key>123102983109283019283</session_key>``
        ``     <checkpoint_dir>/opt/splunk/var/lib/splunk/modinputs</checkpoint_dir>``
        ``     <item name="myScheme">``
        ``       <param name="param1">value1</param>``
        ``       <param_list name="param2">``
        ``         <value>value2</value>``
        ``         <value>value3</value>``
        ``         <value>value4</value>``
        ``       </param_list>``
        ``     </item>``
        ``</items>``

        :param stream: ``Stream`` containing XML to parse.
        :return definition: A ``ValidationDefinition`` object.

        """

        definition = ValidationDefinition()

        # parse XML from the stream, then get the root node
        root = ET.parse(stream).getroot()

        for node in root:
            # lone item node
            if node.tag == "item":
                # name from item node
                definition.metadata["name"] = node.get("name")
                definition.parameters = parse_xml_data(node, "")
            else:
                # Store anything else in metadata
                definition.metadata[node.tag] = node.text

        return definition                                                                                                                                                                                                                                                                                                                                                                    humanize/bin/humanize/.___init__.py                                                                 000644  000765  000024  00000000261 12167315560 020603  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/__init__.py                                                                   000644  000765  000000  00000000532 12167315560 020362  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         VERSION = (0,4)

from humanize.time import *
from humanize.number import *
from humanize.filesize import *
from humanize.i18n import activate, deactivate

__all__ = ['VERSION', 'naturalday', 'naturaltime', 'ordinal', 'intword',
    'naturaldelta', 'intcomma', 'apnumber', 'fractional', 'naturalsize',
    'activate', 'deactivate', 'naturaldate']
                                                                                                                                                                      humanize/bin/humanize/._compat.py                                                                   000644  000765  000024  00000000261 12145257311 020322  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/compat.py                                                                     000644  000765  000000  00000000152 12145257311 020077  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         import sys

if sys.version_info < (3,):
    string_types = (basestring,)
else:
    string_types = (str,)

                                                                                                                                                                                                                                                                                                                                                                                                                      humanize/bin/humanize/._filesize.py                                                                 000644  000765  000024  00000000261 12305011657 020650  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/filesize.py                                                                   000644  000765  000000  00000003003 12305011657 020423  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         #!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Bits & Bytes related humanization."""

suffixes = {
    'decimal': ('kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'),
    'binary': ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'),
    'gnu': "KMGTPEZY",
}


def naturalsize(value, binary=False, gnu=False, format='%.1f'):
    """Format a number of byteslike a human readable filesize (eg. 10 kB).  By
    default, decimal suffixes (kB, MB) are used.  Passing binary=true will use
    binary suffixes (KiB, MiB) are used and the base will be 2**10 instead of
    10**3.  If ``gnu`` is True, the binary argument is ignored and GNU-style
    (ls -sh style) prefixes are used (K, M) with the 2**10 definition.
    Non-gnu modes are compatible with jinja2's ``filesizeformat`` filter."""
    if gnu: suffix = suffixes['gnu']
    elif binary: suffix = suffixes['binary']
    else: suffix = suffixes['decimal']

    base = 1024 if (gnu or binary) else 1000
    bytes = float(value)

    if bytes == 1 and not gnu: return '1 Byte'
    elif bytes < base and not gnu: return '%d Bytes' % bytes
    elif bytes < base and gnu: return '%dB' % bytes

    for i,s in enumerate(suffix):
        unit = base ** (i+2)
        if bytes < unit and not gnu:
            return (format + ' %s') % ((base * bytes / unit), s)
        elif bytes < unit and gnu:
            return (format + '%s') % ((base * bytes / unit), s)
    if gnu:
        return (format + '%s') % ((base * bytes / unit), s)
    return (format + ' %s') % ((base * bytes / unit), s)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             humanize/bin/humanize/._i18n.py                                                                     000644  000765  000024  00000000261 12431157416 017621  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/i18n.py                                                                       000644  000765  000000  00000003353 12431157416 017404  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # -*- coding: utf-8 -*-
import gettext as gettext_module
from threading import local
import os.path

__all__ = ['activate', 'deactivate', 'gettext', 'ngettext']

_TRANSLATIONS = {None: gettext_module.NullTranslations()}
_CURRENT = local()

_DEFAULT_LOCALE_PATH = os.path.join(os.path.dirname(__file__), 'locale')


def get_translation():
    try:
        return _TRANSLATIONS[_CURRENT.locale]
    except (AttributeError, KeyError):
        return _TRANSLATIONS[None]


def activate(locale, path=None):
    """Set 'locale' as current locale. Search for locale in directory 'path'
    @param locale: language name, eg 'en_GB'"""
    if path is None:
        path = _DEFAULT_LOCALE_PATH
    if locale not in _TRANSLATIONS:
        translation = gettext_module.translation('humanize', path, [locale])
        _TRANSLATIONS[locale] = translation
    _CURRENT.locale = locale
    return _TRANSLATIONS[locale]


def deactivate():
    _CURRENT.locale = None


def gettext(message):
    return get_translation().gettext(message)


def pgettext(msgctxt, message):
    """'Particular gettext' function.
    It works with 'msgctxt' .po modifiers and allow duplicate keys with
    different translations.
    Python 2 don't have support for this GNU gettext function, so we
    reimplement it. It works by joining msgctx and msgid by '4' byte."""
    key = msgctxt + '\x04' + message
    translation = get_translation().gettext(key)
    return message if translation == key else translation


def ngettext(message, plural, num):
    return get_translation().ngettext(message, plural, num)


def gettext_noop(message):
    """Example usage:
    CONSTANTS = [gettext_noop('first'), gettext_noop('second')]
    def num_name(n):
        return gettext(CONSTANTS[n])"""
    return message
                                                                                                                                                                                                                                                                                     humanize/bin/humanize/._locale                                                                      000755  000765  000024  00000000261 12431157636 017661  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/                                                                       000755  000765  000000  00000000000 12431157636 017512  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/._number.py                                                                   000644  000765  000024  00000000261 12431157416 020332  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/number.py                                                                     000644  000765  000000  00000010727 12431157416 020120  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         #!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Humanizing functions for numbers."""

import re
from fractions import Fraction
from .import compat
from .i18n import gettext as _, gettext_noop as N_, pgettext as P_


def ordinal(value):
    """Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer or anything int() will turn into an
    integer.  Anything other value will have nothing done to it."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    t = (P_('0', 'th'),
         P_('1', 'st'),
         P_('2', 'nd'),
         P_('3', 'rd'),
         P_('4', 'th'),
         P_('5', 'th'),
         P_('6', 'th'),
         P_('7', 'th'),
         P_('8', 'th'),
         P_('9', 'th'))
    if value % 100 in (11, 12, 13):  # special case
        return "%d%s" % (value, t[0])
    return '%d%s' % (value, t[value % 10])


def intcomma(value):
    """Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.  To maintain
    some compatability with Django's intcomma, this function also accepts
    floats."""
    try:
        if isinstance(value, compat.string_types):
            float(value.replace(',', ''))
        else:
            float(value)
    except (TypeError, ValueError):
        return value
    orig = str(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)

powers = [10 ** x for x in (6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 100)]
human_powers = (N_('million'), N_('billion'), N_('trillion'), N_('quadrillion'),
                N_('quintillion'), N_('sextillion'), N_('septillion'),
                N_('octillion'), N_('nonillion'), N_('decillion'), N_('googol'))


def intword(value, format='%.1f'):
    """Converts a large integer to a friendly text representation. Works best for
    numbers over 1 million. For example, 1000000 becomes '1.0 million', 1200000
    becomes '1.2 million' and '1200000000' becomes '1.2 billion'.  Supports up to
    decillion (33 digits) and googol (100 digits).  You can pass format to change
    the number of decimal or general format of the number portion.  This function
    returns a string unless the value passed was unable to be coaxed into an int."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    if value < powers[0]:
        return str(value)
    for ordinal, power in enumerate(powers[1:], 1):
        if value < power:
            chopped = value / float(powers[ordinal - 1])
            return (' '.join([format, _(human_powers[ordinal - 1])])) % chopped
    return str(value)


def apnumber(value):
    """For numbers 1-9, returns the number spelled out. Otherwise, returns the
    number. This follows Associated Press style.  This always returns a string
    unless the value was not int-able, unlike the Django filter."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    if not 0 < value < 10:
        return str(value)
    return (_('one'), _('two'), _('three'), _('four'), _('five'), _('six'),
            _('seven'), _('eight'), _('nine'))[value - 1]


def fractional(value):
    '''
    There will be some cases where one might not want to show
        ugly decimal places for floats and decimals.
    This function returns a human readable fractional number
        in form of fractions and mixed fractions.
    Pass in a string, or a number or a float, and this function returns
        a string representation of a fraction
        or whole number
        or a mixed fraction
    Examples:
        fractional(0.3) will return '1/3'
        fractional(1.3) will return '1 3/10'
        fractional(float(1/3)) will return '1/3'
        fractional(1) will return '1'
    This will always return a string.
    '''
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    wholeNumber = int(number)
    frac = Fraction(number - wholeNumber).limit_denominator(1000)
    numerator = frac._numerator
    denominator = frac._denominator
    if wholeNumber and not numerator and denominator == 1:
        return '%.0f' % wholeNumber  # this means that an integer was passed in (or variants of that integer like 1.0000)
    elif not wholeNumber:
        return '%.0f/%.0f' % (numerator, denominator)
    else:
        return '%.0f %.0f/%.0f' % (wholeNumber, numerator, denominator)
                                         humanize/bin/humanize/._time.py                                                                     000644  000765  000024  00000000261 12431157416 020000  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/time.py                                                                       000644  000765  000000  00000012755 12431157416 017571  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         #!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Time humanizing functions.  These are largely borrowed from Django's
``contrib.humanize``."""

import time
from datetime import datetime, timedelta, date
from .i18n import ngettext, gettext as _

__all__ = ['naturaldelta', 'naturaltime', 'naturalday', 'naturaldate']

def _now():
    return datetime.now()

def abs_timedelta(delta):
    """Returns an "absolute" value for a timedelta, always representing a
    time distance."""
    if delta.days < 0:
        now = _now()
        return now - (now + delta)
    return delta

def date_and_delta(value):
    """Turn a value into a date and a timedelta which represents how long ago
    it was.  If that's not possible, return (None, value)."""
    now = _now()
    if isinstance(value, datetime):
        date = value
        delta = now - value
    elif isinstance(value, timedelta):
        date = now - value
        delta = value
    else:
        try:
            value = int(value)
            delta = timedelta(seconds=value)
            date = now - delta
        except (ValueError, TypeError):
            return (None, value)
    return date, abs_timedelta(delta)

def naturaldelta(value, months=True):
    """Given a timedelta or a number of seconds, return a natural
    representation of the amount of time elapsed.  This is similar to
    ``naturaltime``, but does not add tense to the result.  If ``months``
    is True, then a number of months (based on 30.5 days) will be used
    for fuzziness between years."""
    now = _now()
    date, delta = date_and_delta(value)
    if date is None:
        return value

    use_months = months

    seconds = abs(delta.seconds)
    days = abs(delta.days)
    years = days // 365
    days = days % 365
    months = int(days // 30.5)

    if not years and days < 1:
        if seconds == 0:
            return _("a moment")
        elif seconds == 1:
            return _("a second")
        elif seconds < 60:
            return ngettext("%d second", "%d seconds", seconds) % seconds
        elif 60 <= seconds < 120:
            return _("a minute")
        elif 120 <= seconds < 3600:
            minutes = seconds // 60
            return ngettext("%d minute", "%d minutes", minutes) % minutes
        elif 3600 <= seconds < 3600 * 2:
            return _("an hour")
        elif 3600 < seconds:
            hours = seconds // 3600
            return ngettext("%d hour", "%d hours", hours) % hours
    elif years == 0:
        if days == 1:
            return _("a day")
        if not use_months:
            return ngettext("%d day", "%d days", days) % days
        else:
            if not months:
                return ngettext("%d day", "%d days", days) % days
            elif months == 1:
                return _("a month")
            else:
                return ngettext("%d month", "%d months", months) % months
    elif years == 1:
        if not months and not days:
            return _("a year")
        elif not months:
            return ngettext("1 year, %d day", "1 year, %d days", days) % days
        elif use_months:
            if months == 1:
                return _("1 year, 1 month")
            else:
                return ngettext("1 year, %d month",
                                "1 year, %d months", months) % months
        else:
            return ngettext("1 year, %d day", "1 year, %d days", days) % days
    else:
        return ngettext("%d year", "%d years", years) % years


def naturaltime(value, future=False, months=True):
    """Given a datetime or a number of seconds, return a natural representation
    of that time in a resolution that makes sense.  This is more or less
    compatible with Django's ``naturaltime`` filter.  ``future`` is ignored for
    datetimes, where the tense is always figured out based on the current time.
    If an integer is passed, the return value will be past tense by default,
    unless ``future`` is set to True."""
    now = _now()
    date, delta = date_and_delta(value)
    if date is None:
        return value
    # determine tense by value only if datetime/timedelta were passed
    if isinstance(value, (datetime, timedelta)):
        future = date > now

    ago = _('%s from now') if future else _('%s ago')
    delta = naturaldelta(delta, months)

    if delta == _("a moment"):
        return _("now")

    return ago % delta

def naturalday(value, format='%b %d'):
    """For date values that are tomorrow, today or yesterday compared to
    present day returns representing string. Otherwise, returns a string
    formatted according to ``format``."""
    try:
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't date-ish
        return value
    except (OverflowError, ValueError):
        # Date arguments out of range
        return value
    delta = value - date.today()
    if delta.days == 0:
        return _('today')
    elif delta.days == 1:
        return _('tomorrow')
    elif delta.days == -1:
        return _('yesterday')
    return value.strftime(format)

def naturaldate(value):
    """Like naturalday, but will append a year for dates that are a year
    ago or more."""
    try:
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't date-ish
        return value
    except (OverflowError, ValueError):
        # Date arguments out of range
        return value
    delta = abs_timedelta(value - date.today())
    if delta.days >= 365:
        return naturalday(value, '%b %d %Y')
    return naturalday(value)


                   humanize/bin/humanize/locale/._fr_FR                                                                000755  000765  000024  00000000261 12431157636 020657  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/fr_FR/                                                                 000755  000765  000000  00000000000 12431157636 020510  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/._ko_KR                                                                000755  000765  000024  00000000261 12431157636 020666  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ko_KR/                                                                 000755  000765  000000  00000000000 12431157636 020517  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/._ru_RU                                                                000755  000765  000024  00000000261 12431157636 020715  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ru_RU/                                                                 000755  000765  000000  00000000000 12431157636 020546  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/ru_RU/._LC_MESSAGES                                                    000755  000765  000024  00000000261 12431157636 022502  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ru_RU/LC_MESSAGES/                                                     000755  000765  000000  00000000000 12431157636 022333  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/ru_RU/LC_MESSAGES/._humanize.mo                                        000644  000765  000024  00000000261 12431157416 024725  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ru_RU/LC_MESSAGES/humanize.mo                                          000644  000765  000000  00000006016 12431157416 024507  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         ��    5      �  G   l      �     �     �     �     �     �     �     �     �     
            "   3     V     f     k     p     u     z          �     �     �     �     �     �     �     �     �     �  	   �     �     �     �     �     �     �  	   �       	   
               $  
   0     ;  
   A     L     P     V     \     e     n  	   r  �  |  !   _  #   �  -   �  /   �  3   	     7	     W	     e	     s	     x	  ?   }	  M   �	     
     "
     '
     ,
     1
     6
     ;
     @
     E
     J
     S
     `
  
   t
     
     �
     �
     �
     �
     �
     �
     �
     �
     �
               %     2     G     P     i     �     �     �  
   �     �     �     �     �     �  
                           *            
           &   4                5                !   	                  )            $   %      2   +   1       "      3                    .          /   -          (           #       0   '   ,                         %d day %d days %d hour %d hours %d minute %d minutes %d month %d months %d second %d seconds %d year %d years %s ago %s from now 0th 1st 1 year, %d day 1 year, %d days 1 year, %d month 1 year, %d months 1 year, 1 month 2nd 3rd 4th 5th 6th 7th 8th 9th a day a minute a moment a month a second a year an hour billion decillion eight five four googol million nine nonillion now octillion one quadrillion quintillion septillion seven sextillion six three today tomorrow trillion two yesterday Project-Id-Version: PROJECT VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2014-03-24 20:26+0400
PO-Revision-Date: 2014-03-24 20:32+0300
Last-Translator: Sergey Prokhorov <me@seriyps.ru>
Language-Team: ru_RU <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);
Generated-By: Babel 0.9.6
X-Generator: Poedit 1.5.4
 %d день %d дня %d дней %d час %d часа %d часов %d минута %d минуты %d минут %d месяц %d месяца %d месяцев %d секунда %d секунды %d секунд %d год %d года %d лет %s назад через %s ой ый 1 год, %d день 1 год, %d дня 1 год, %d дней 1 год, %d месяц 1 год, %d месяца 1 год, %d месяцев 1 год, 1 месяц ой ий ый ый ой ой ой ый день минуту только что месяц секунду год час миллиарда децилиона восемь пять четыре гогола миллиона девять нониллиона сейчас октиллиона один квадриллиона квинтиллиона септиллиона семь сикстиллиона шесть три сегодня завтра триллиона два вчера                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   humanize/bin/humanize/locale/ru_RU/LC_MESSAGES/._humanize.po                                        000644  000765  000024  00000000261 12431157416 024730  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ru_RU/LC_MESSAGES/humanize.po                                          000644  000765  000000  00000013302 12431157416 024506  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Russian (Russia) translations for PROJECT.
# Copyright (C) 2013 ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2013.
#
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2014-03-24 21:07+0400\n"
"PO-Revision-Date: 2014-03-24 20:32+0300\n"
"Last-Translator: Sergey Prokhorov <me@seriyps.ru>\n"
"Language-Team: ru_RU <LL@li.org>\n"
"Language: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n"
"%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\n"
"Generated-By: Babel 0.9.6\n"
"X-Generator: Poedit 1.5.4\n"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:20
msgctxt "0"
msgid "th"
msgstr "ой"

#: humanize/number.py:21
msgctxt "1"
msgid "st"
msgstr "ый"

#: humanize/number.py:22
msgctxt "2"
msgid "nd"
msgstr "ой"

#: humanize/number.py:23
msgctxt "3"
msgid "rd"
msgstr "ий"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:24
msgctxt "4"
msgid "th"
msgstr "ый"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:25
msgctxt "5"
msgid "th"
msgstr "ый"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:26
msgctxt "6"
msgid "th"
msgstr "ой"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:27
msgctxt "7"
msgid "th"
msgstr "ой"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:28
msgctxt "8"
msgid "th"
msgstr "ой"

# в Django тут "ий" но на самом деле оба варианта работают плохо
#: humanize/number.py:29
msgctxt "9"
msgid "th"
msgstr "ый"

#: humanize/number.py:55
msgid "million"
msgstr "миллиона"

#: humanize/number.py:55
msgid "billion"
msgstr "миллиарда"

#: humanize/number.py:55
msgid "trillion"
msgstr "триллиона"

#: humanize/number.py:55
msgid "quadrillion"
msgstr "квадриллиона"

#: humanize/number.py:56
msgid "quintillion"
msgstr "квинтиллиона"

#: humanize/number.py:56
msgid "sextillion"
msgstr "сикстиллиона"

#: humanize/number.py:56
msgid "septillion"
msgstr "септиллиона"

#: humanize/number.py:57
msgid "octillion"
msgstr "октиллиона"

#: humanize/number.py:57
msgid "nonillion"
msgstr "нониллиона"

#: humanize/number.py:57
msgid "decillion"
msgstr "децилиона"

#: humanize/number.py:57
msgid "googol"
msgstr "гогола"

#: humanize/number.py:91
msgid "one"
msgstr "один"

#: humanize/number.py:91
msgid "two"
msgstr "два"

#: humanize/number.py:91
msgid "three"
msgstr "три"

#: humanize/number.py:91
msgid "four"
msgstr "четыре"

#: humanize/number.py:91
msgid "five"
msgstr "пять"

#: humanize/number.py:91
msgid "six"
msgstr "шесть"

#: humanize/number.py:92
msgid "seven"
msgstr "семь"

#: humanize/number.py:92
msgid "eight"
msgstr "восемь"

#: humanize/number.py:92
msgid "nine"
msgstr "девять"

#: humanize/time.py:64 humanize/time.py:126
msgid "a moment"
msgstr "только что"

#: humanize/time.py:66
msgid "a second"
msgstr "секунду"

#: humanize/time.py:68
#, python-format
msgid "%d second"
msgid_plural "%d seconds"
msgstr[0] "%d секунда"
msgstr[1] "%d секунды"
msgstr[2] "%d секунд"

#: humanize/time.py:70
msgid "a minute"
msgstr "минуту"

#: humanize/time.py:73
#, python-format
msgid "%d minute"
msgid_plural "%d minutes"
msgstr[0] "%d минута"
msgstr[1] "%d минуты"
msgstr[2] "%d минут"

#: humanize/time.py:75
msgid "an hour"
msgstr "час"

#: humanize/time.py:78
#, python-format
msgid "%d hour"
msgid_plural "%d hours"
msgstr[0] "%d час"
msgstr[1] "%d часа"
msgstr[2] "%d часов"

#: humanize/time.py:81
msgid "a day"
msgstr "день"

#: humanize/time.py:83 humanize/time.py:86
#, python-format
msgid "%d day"
msgid_plural "%d days"
msgstr[0] "%d день"
msgstr[1] "%d дня"
msgstr[2] "%d дней"

#: humanize/time.py:88
msgid "a month"
msgstr "месяц"

#: humanize/time.py:90
#, python-format
msgid "%d month"
msgid_plural "%d months"
msgstr[0] "%d месяц"
msgstr[1] "%d месяца"
msgstr[2] "%d месяцев"

#: humanize/time.py:93
msgid "a year"
msgstr "год"

#: humanize/time.py:95 humanize/time.py:103
#, python-format
msgid "1 year, %d day"
msgid_plural "1 year, %d days"
msgstr[0] "1 год, %d день"
msgstr[1] "1 год, %d дня"
msgstr[2] "1 год, %d дней"

#: humanize/time.py:98
msgid "1 year, 1 month"
msgstr "1 год, 1 месяц"

#: humanize/time.py:100
#, python-format
msgid "1 year, %d month"
msgid_plural "1 year, %d months"
msgstr[0] "1 год, %d месяц"
msgstr[1] "1 год, %d месяца"
msgstr[2] "1 год, %d месяцев"

#: humanize/time.py:105
#, python-format
msgid "%d year"
msgid_plural "%d years"
msgstr[0] "%d год"
msgstr[1] "%d года"
msgstr[2] "%d лет"

#: humanize/time.py:123
#, python-format
msgid "%s from now"
msgstr "через %s"

#: humanize/time.py:123
#, python-format
msgid "%s ago"
msgstr "%s назад"

#: humanize/time.py:127
msgid "now"
msgstr "сейчас"

#: humanize/time.py:145
msgid "today"
msgstr "сегодня"

#: humanize/time.py:147
msgid "tomorrow"
msgstr "завтра"

#: humanize/time.py:149
msgid "yesterday"
msgstr "вчера"
                                                                                                                                                                                                                                                                                                                              humanize/bin/humanize/locale/ko_KR/._LC_MESSAGES                                                    000755  000765  000024  00000000261 12431157636 022453  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ko_KR/LC_MESSAGES/                                                     000755  000765  000000  00000000000 12431157636 022304  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/ko_KR/LC_MESSAGES/._humanize.mo                                        000644  000765  000024  00000000261 12431157416 024676  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ko_KR/LC_MESSAGES/humanize.mo                                          000644  000765  000000  00000003452 12431157416 024461  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         ��    "      ,  /   <      �     �               .     A     V     g     n     z  "   �     �     �     �     �     �     �     �     �                              $     )     -     1     7     ;     A     G     P  	   T  �  ^     �     �     
          '     3     A     H     O     e     �     �     �     �     �     �     �     �     �     �     �     �     �     �     �     �     �                              #                   !                                "                           
             	                                                                   %d day %d days %d hour %d hours %d minute %d minutes %d month %d months %d second %d seconds %d year %d years %s ago %s from now 1 year, %d day 1 year, %d days 1 year, %d month 1 year, %d months 1 year, 1 month a day a minute a moment a month a second a year an hour billion eight five four million nine now one seven six three today tomorrow two yesterday Project-Id-Version: PROJECT VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2014-03-24 21:07+0400
PO-Revision-Date: 2013-07-10 11:38+0900
Last-Translator: @youngrok
Language-Team: ko_KR <LL@li.org>
Language: 
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n > 1);
Generated-By: Babel 0.9.6
X-Generator: Poedit 1.5.7
 %d jour %d일 %d heure %d시간 %d분 %d분 %d mois %d개월 %d초 %d초 %d 년 %d ans %s 전 %s 후 1년 %d일 1년 %d일 1년, %d개월 1년, %d개월 1년, 1개월 하루 1분 잠깐 한달 1초 1년 1시간 milliard 여덟 다섯 넷 %(value)s million 아홉 방금 하나 일곱 여섯 셋 오늘 내일 둘 어제                                                                                                                                                                                                                       humanize/bin/humanize/locale/ko_KR/LC_MESSAGES/._humanize.po                                        000644  000765  000024  00000000261 12431157416 024701  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/ko_KR/LC_MESSAGES/humanize.po                                          000644  000765  000000  00000011041 12431157416 024455  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Korean (Korea) translations for humanize.
# Copyright (C) 2013
# This file is distributed under the same license as the humanize project.
# @youngrok, 2013.
#
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2014-03-24 21:07+0400\n"
"PO-Revision-Date: 2013-07-10 11:38+0900\n"
"Last-Translator: @youngrok\n"
"Language-Team: ko_KR <LL@li.org>\n"
"Language: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\n"
"Generated-By: Babel 0.9.6\n"
"X-Generator: Poedit 1.5.7\n"

#: humanize/number.py:20
#, fuzzy
msgctxt "0"
msgid "th"
msgstr "번째"

#: humanize/number.py:21
#, fuzzy
msgctxt "1"
msgid "st"
msgstr "번째"

#: humanize/number.py:22
#, fuzzy
msgctxt "2"
msgid "nd"
msgstr "번째"

#: humanize/number.py:23
#, fuzzy
msgctxt "3"
msgid "rd"
msgstr "번째"

#: humanize/number.py:24
#, fuzzy
msgctxt "4"
msgid "th"
msgstr "번째"

#: humanize/number.py:25
#, fuzzy
msgctxt "5"
msgid "th"
msgstr "번째"

#: humanize/number.py:26
#, fuzzy
msgctxt "6"
msgid "th"
msgstr "번째"

#: humanize/number.py:27
#, fuzzy
msgctxt "7"
msgid "th"
msgstr "번째"

#: humanize/number.py:28
#, fuzzy
msgctxt "8"
msgid "th"
msgstr "번째"

#: humanize/number.py:29
#, fuzzy
msgctxt "9"
msgid "th"
msgstr "번째"

#: humanize/number.py:55
msgid "million"
msgstr "%(value)s million"

#: humanize/number.py:55
msgid "billion"
msgstr "milliard"

#: humanize/number.py:55
#, fuzzy
msgid "trillion"
msgstr "%(value)s billion"

#: humanize/number.py:55
#, fuzzy
msgid "quadrillion"
msgstr "%(value)s quadrillion"

#: humanize/number.py:56
#, fuzzy
msgid "quintillion"
msgstr "%(value)s quintillion"

#: humanize/number.py:56
#, fuzzy
msgid "sextillion"
msgstr "%(value)s sextillion"

#: humanize/number.py:56
#, fuzzy
msgid "septillion"
msgstr "%(value)s septillion"

#: humanize/number.py:57
#, fuzzy
msgid "octillion"
msgstr "%(value)s octillion"

#: humanize/number.py:57
#, fuzzy
msgid "nonillion"
msgstr "%(value)s nonillion"

#: humanize/number.py:57
#, fuzzy
msgid "decillion"
msgstr "%(value)s décillion"

#: humanize/number.py:57
#, fuzzy
msgid "googol"
msgstr "%(value)s gogol"

#: humanize/number.py:91
msgid "one"
msgstr "하나"

#: humanize/number.py:91
msgid "two"
msgstr "둘"

#: humanize/number.py:91
msgid "three"
msgstr "셋"

#: humanize/number.py:91
msgid "four"
msgstr "넷"

#: humanize/number.py:91
msgid "five"
msgstr "다섯"

#: humanize/number.py:91
msgid "six"
msgstr "여섯"

#: humanize/number.py:92
msgid "seven"
msgstr "일곱"

#: humanize/number.py:92
msgid "eight"
msgstr "여덟"

#: humanize/number.py:92
msgid "nine"
msgstr "아홉"

#: humanize/time.py:64 humanize/time.py:126
msgid "a moment"
msgstr "잠깐"

#: humanize/time.py:66
msgid "a second"
msgstr "1초"

#: humanize/time.py:68
#, python-format
msgid "%d second"
msgid_plural "%d seconds"
msgstr[0] "%d초"
msgstr[1] "%d초"

#: humanize/time.py:70
msgid "a minute"
msgstr "1분"

#: humanize/time.py:73
#, python-format
msgid "%d minute"
msgid_plural "%d minutes"
msgstr[0] "%d분"
msgstr[1] "%d분"

#: humanize/time.py:75
msgid "an hour"
msgstr "1시간"

#: humanize/time.py:78
#, python-format
msgid "%d hour"
msgid_plural "%d hours"
msgstr[0] "%d heure"
msgstr[1] "%d시간"

#: humanize/time.py:81
msgid "a day"
msgstr "하루"

#: humanize/time.py:83 humanize/time.py:86
#, python-format
msgid "%d day"
msgid_plural "%d days"
msgstr[0] "%d jour"
msgstr[1] "%d일"

#: humanize/time.py:88
msgid "a month"
msgstr "한달"

#: humanize/time.py:90
#, python-format
msgid "%d month"
msgid_plural "%d months"
msgstr[0] "%d mois"
msgstr[1] "%d개월"

#: humanize/time.py:93
msgid "a year"
msgstr "1년"

#: humanize/time.py:95 humanize/time.py:103
#, python-format
msgid "1 year, %d day"
msgid_plural "1 year, %d days"
msgstr[0] "1년 %d일"
msgstr[1] "1년 %d일"

#: humanize/time.py:98
msgid "1 year, 1 month"
msgstr "1년, 1개월"

#: humanize/time.py:100
#, python-format
msgid "1 year, %d month"
msgid_plural "1 year, %d months"
msgstr[0] "1년, %d개월"
msgstr[1] "1년, %d개월"

#: humanize/time.py:105
#, python-format
msgid "%d year"
msgid_plural "%d years"
msgstr[0] "%d 년"
msgstr[1] "%d ans"

#: humanize/time.py:123
#, python-format
msgid "%s from now"
msgstr "%s 후"

#: humanize/time.py:123
#, python-format
msgid "%s ago"
msgstr "%s 전"

#: humanize/time.py:127
msgid "now"
msgstr "방금"

#: humanize/time.py:145
msgid "today"
msgstr "오늘"

#: humanize/time.py:147
msgid "tomorrow"
msgstr "내일"

#: humanize/time.py:149
msgid "yesterday"
msgstr "어제"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               humanize/bin/humanize/locale/fr_FR/._LC_MESSAGES                                                    000755  000765  000024  00000000261 12431157636 022444  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/fr_FR/LC_MESSAGES/                                                     000755  000765  000000  00000000000 12431157636 022275  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/bin/humanize/locale/fr_FR/LC_MESSAGES/._humanize.mo                                        000644  000765  000024  00000000261 12431157416 024667  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/fr_FR/LC_MESSAGES/humanize.mo                                          000644  000765  000000  00000003525 12431157416 024453  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         ��    !      $  /   ,      �     �     �     	          1     F     W     ^     j  "   �     �     �     �     �     �     �     �     �     �     �                                        #     )     /     8  	   <  �  F     �     �     
          /     F  	   S     ]  "   e  !   �     �     �  
   �  	   �     �     �     �  	   �     �          
            
        &     )     .     2     8     D     K     P                                                   !                           
             	                                                                    %d day %d days %d hour %d hours %d minute %d minutes %d month %d months %d second %d seconds %d year %d years %s ago %s from now 1 year, %d day 1 year, %d days 1 year, %d month 1 year, %d months 1 year, 1 month a day a minute a moment a month a second a year an hour billion eight five four nine now one seven six three today tomorrow two yesterday Project-Id-Version: PROJECT VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2014-03-24 21:07+0400
PO-Revision-Date: 2013-06-22 08:52+0100
Last-Translator: Olivier Cortès <oc@1flow.io>
Language-Team: fr_FR <LL@li.org>
Language: 
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n > 1);
Generated-By: Babel 0.9.6
X-Generator: Poedit 1.5.5
 %d jour %d jours %d heure %d heures %d minute %d minutes %d mois %d mois %d seconde %d secondes %d an %d ans il y a %s dans %s un an et %d jour un an et %d jours un an et %d mois un an et %d mois un an et un mois un jour une minute un moment un mois une seconde un an une heure milliard huit cinq quatre neuf maintenant un sept six trois aujourd'hui demain deux hier                                                                                                                                                                            humanize/bin/humanize/locale/fr_FR/LC_MESSAGES/._humanize.po                                        000644  000765  000024  00000000261 12431157416 024672  0                                                                                                    ustar 00northben                        staff                           000000  000000                                                                                                                                                                             Mac OS X            	   2         �                                      ATTR       �   �                     �     com.apple.quarantine q/0001;56eefca6;Firefox;                                                                                                                                                                                                                                                                                                                                                humanize/bin/humanize/locale/fr_FR/LC_MESSAGES/humanize.po                                          000644  000765  000000  00000011156 12431157416 024455  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # French (France) translations for PROJECT.
# Copyright (C) 2013 ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2013.
#
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2014-03-24 21:07+0400\n"
"PO-Revision-Date: 2013-06-22 08:52+0100\n"
"Last-Translator: Olivier Cortès <oc@1flow.io>\n"
"Language-Team: fr_FR <LL@li.org>\n"
"Language: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\n"
"Generated-By: Babel 0.9.6\n"
"X-Generator: Poedit 1.5.5\n"

#: humanize/number.py:20
#, fuzzy
msgctxt "0"
msgid "th"
msgstr "e"

#: humanize/number.py:21
#, fuzzy
msgctxt "1"
msgid "st"
msgstr "er"

#: humanize/number.py:22
#, fuzzy
msgctxt "2"
msgid "nd"
msgstr "e"

#: humanize/number.py:23
#, fuzzy
msgctxt "3"
msgid "rd"
msgstr "e"

#: humanize/number.py:24
#, fuzzy
msgctxt "4"
msgid "th"
msgstr "e"

#: humanize/number.py:25
#, fuzzy
msgctxt "5"
msgid "th"
msgstr "e"

#: humanize/number.py:26
#, fuzzy
msgctxt "6"
msgid "th"
msgstr "e"

#: humanize/number.py:27
#, fuzzy
msgctxt "7"
msgid "th"
msgstr "e"

#: humanize/number.py:28
#, fuzzy
msgctxt "8"
msgid "th"
msgstr "e"

#: humanize/number.py:29
#, fuzzy
msgctxt "9"
msgid "th"
msgstr "e"

#: humanize/number.py:55
#, fuzzy
msgid "million"
msgstr "%(value)s million"

#: humanize/number.py:55
msgid "billion"
msgstr "milliard"

#: humanize/number.py:55
#, fuzzy
msgid "trillion"
msgstr "%(value)s billion"

#: humanize/number.py:55
#, fuzzy
msgid "quadrillion"
msgstr "%(value)s quadrillion"

#: humanize/number.py:56
#, fuzzy
msgid "quintillion"
msgstr "%(value)s quintillion"

#: humanize/number.py:56
#, fuzzy
msgid "sextillion"
msgstr "%(value)s sextillion"

#: humanize/number.py:56
#, fuzzy
msgid "septillion"
msgstr "%(value)s septillion"

#: humanize/number.py:57
#, fuzzy
msgid "octillion"
msgstr "%(value)s octillion"

#: humanize/number.py:57
#, fuzzy
msgid "nonillion"
msgstr "%(value)s nonillion"

#: humanize/number.py:57
#, fuzzy
msgid "decillion"
msgstr "%(value)s décillion"

#: humanize/number.py:57
#, fuzzy
msgid "googol"
msgstr "%(value)s gogol"

#: humanize/number.py:91
msgid "one"
msgstr "un"

#: humanize/number.py:91
msgid "two"
msgstr "deux"

#: humanize/number.py:91
msgid "three"
msgstr "trois"

#: humanize/number.py:91
msgid "four"
msgstr "quatre"

#: humanize/number.py:91
msgid "five"
msgstr "cinq"

#: humanize/number.py:91
msgid "six"
msgstr "six"

#: humanize/number.py:92
msgid "seven"
msgstr "sept"

#: humanize/number.py:92
msgid "eight"
msgstr "huit"

#: humanize/number.py:92
msgid "nine"
msgstr "neuf"

#: humanize/time.py:64 humanize/time.py:126
msgid "a moment"
msgstr "un moment"

#: humanize/time.py:66
msgid "a second"
msgstr "une seconde"

#: humanize/time.py:68
#, python-format
msgid "%d second"
msgid_plural "%d seconds"
msgstr[0] "%d seconde"
msgstr[1] "%d secondes"

#: humanize/time.py:70
msgid "a minute"
msgstr "une minute"

#: humanize/time.py:73
#, python-format
msgid "%d minute"
msgid_plural "%d minutes"
msgstr[0] "%d minute"
msgstr[1] "%d minutes"

#: humanize/time.py:75
msgid "an hour"
msgstr "une heure"

#: humanize/time.py:78
#, python-format
msgid "%d hour"
msgid_plural "%d hours"
msgstr[0] "%d heure"
msgstr[1] "%d heures"

#: humanize/time.py:81
msgid "a day"
msgstr "un jour"

#: humanize/time.py:83 humanize/time.py:86
#, python-format
msgid "%d day"
msgid_plural "%d days"
msgstr[0] "%d jour"
msgstr[1] "%d jours"

#: humanize/time.py:88
msgid "a month"
msgstr "un mois"

#: humanize/time.py:90
#, python-format
msgid "%d month"
msgid_plural "%d months"
msgstr[0] "%d mois"
msgstr[1] "%d mois"

#: humanize/time.py:93
msgid "a year"
msgstr "un an"

#: humanize/time.py:95 humanize/time.py:103
#, python-format
msgid "1 year, %d day"
msgid_plural "1 year, %d days"
msgstr[0] "un an et %d jour"
msgstr[1] "un an et %d jours"

#: humanize/time.py:98
msgid "1 year, 1 month"
msgstr "un an et un mois"

#: humanize/time.py:100
#, python-format
msgid "1 year, %d month"
msgid_plural "1 year, %d months"
msgstr[0] "un an et %d mois"
msgstr[1] "un an et %d mois"

#: humanize/time.py:105
#, python-format
msgid "%d year"
msgid_plural "%d years"
msgstr[0] "%d an"
msgstr[1] "%d ans"

#: humanize/time.py:123
#, python-format
msgid "%s from now"
msgstr "dans %s"

#: humanize/time.py:123
#, python-format
msgid "%s ago"
msgstr "il y a %s"

#: humanize/time.py:127
msgid "now"
msgstr "maintenant"

#: humanize/time.py:145
msgid "today"
msgstr "aujourd'hui"

#: humanize/time.py:147
msgid "tomorrow"
msgstr "demain"

#: humanize/time.py:149
msgid "yesterday"
msgstr "hier"
                                                                                                                                                                                                                                                                                                                                                                                                                  humanize/default/                                                                                   000755  000765  000000  00000000000 12674546615 015317  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/default/app.conf                                                                           000644  000765  000000  00000000535 12674546135 016746  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # Splunk app configuration file

[ui]
label = Humanize
is_visible = 0

[launcher]
description = Convert numbers, bytes, and timestamps into fuzzy, human-friendly units! Using the humanize library from https://github.com/jmoiron/humanize
author = Ben Northway
version = 0.1

[package]
id = humanize
check_for_updates = 1

[install]
is_configured = 0
                                                                                                                                                                   humanize/default/commands.conf                                                                      000644  000765  000000  00000000256 12674337114 017762  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         # [commands.conf]($SPLUNK_HOME/etc/system/README/commands.conf.spec)
# Configuration for Search Commands Protocol version 2

[humanize]
chunked = true
filename = humanize.py
                                                                                                                                                                                                                                                                                                                                                  humanize/default/data/                                                                              000755  000765  000000  00000000000 12674037532 016221  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/default/logging.conf                                                                       000644  000765  000000  00000003121 12674531005 017574  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         #
# The format of this file is described in this article at Python.org:
#
#     [Configuration file format](http://goo.gl/K6edZ8)
#
[loggers]
keys = root, splunklib, HumanizeCommand

[logger_root]
level = WARNING   ; Default: WARNING
handlers = stderr ; Default: stderr

[logger_splunklib]
qualname = splunklib
level = NOTSET        ; Default: WARNING
handlers = splunklib  ; Default: stderr
propagate = 0         ; Default: 1

[logger_HumanizeCommand]
qualname = HumanizeCommand
level = DEBUG    ; Default: WARNING
handlers = app,stderr    ; Default: stderr
propagate = 0     ; Default: 1

[handler_app]
# Select this handler to log events to $SPLUNK_HOME/var/log/splunk/searchcommands_app.log
class = logging.handlers.RotatingFileHandler
level = NOTSET
args = ('/Applications/Splunk/var/log/splunk/searchcommands_app.log', 'a', 524288000, 9, 'utf-8', True)
formatter = searchcommands

[handler_splunklib]
# Select this handler to log events to $SPLUNK_HOME/var/log/splunk/splunklib.log
class = logging.handlers.RotatingFileHandler
args = ('%(SPLUNK_HOME)s/var/log/splunk/splunklib.log', 'a', 524288000, 9, 'utf-8', True)
level = NOTSET
formatter = searchcommands

[handler_stderr]
# Select this handler to log events to stderr which splunkd redirects to the associated job's search.log file
class = logging.StreamHandler
level = NOTSET
args = (sys.stderr,)
formatter = searchcommands

[formatters]
keys = searchcommands

[formatter_searchcommands]
format = %(asctime)s, Level=%(levelname)s, Pid=%(process)s, Logger=%(name)s, File=%(filename)s, Line=%(lineno)s, %(message)s

[handlers]
keys = app, splunklib, stderr
                                                                                                                                                                                                                                                                                                                                                                                                                                               humanize/default/data/ui/                                                                           000755  000765  000000  00000000000 12674037532 016636  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/default/data/ui/nav/                                                                       000755  000765  000000  00000000000 12674037532 017422  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/default/data/ui/nav/default.xml                                                            000644  000765  000000  00000001040 12674037532 021563  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         <nav>
    <view name="flashtimeline" default='true' />
    <collection label="Dashboards">
        <view source="unclassified" match="dashboard"/>
        <divider />
    </collection>
    <collection label="Views">
        <view source="unclassified" />
        <divider />
    </collection>
    <collection label="Searches &amp; Reports">
        <collection label="Reports">
            <saved source="unclassified" match="report" />
        </collection>
        <divider />
        <saved source="unclassified" />
    </collection>
</nav>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                humanize/local/                                                                                     000700  000765  000000  00000000000 12674546615 014753  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/metadata/                                                                                  000755  000765  000000  00000000000 12674544502 015444  5                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         humanize/metadata/default.meta                                                                      000644  000765  000000  00000000213 12674337154 017737  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         [commands/humanize]
access = read : [ * ], write : [ admin ]
export = system
owner = nobody
version = 6.3.3
modtime = 1458589291.806870000
                                                                                                                                                                                                                                                                                                                                                                                     humanize/metadata/local.meta                                                                        000600  000765  000000  00000000307 12674544502 017376  0                                                                                                    ustar 00northben                        wheel                           000000  000000                                                                                                                                                                         [app/ui]
version = 6.3.3
modtime = 1458751810.444692000

[app/launcher]
version = 6.3.3
modtime = 1458751810.450027000

[app/package/check_for_updates]
version = 6.3.3
modtime = 1458751810.451788000
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         