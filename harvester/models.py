import abc
import os
from random import choice, uniform
import re
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import ProxyHandler, build_opener, HTTPCookieProcessor
import http.cookiejar
import time
import uuid

from . import __version__, __github_url__
from .utils import fix_url, force_decode
from .user_agents import USER_AGENTS
from harvester.utils import is_url


class Field(metaclass=abc.ABCMeta):
    """ A fragment of data delimited by two regular expressions. """

    def __init__(self, start, end, as_list=False, mods=None, deps=None, skip_new_lines=False):
        """ Initializes this field.

        In case of "as_list" parameter is active (i.e. True), the field will be matched against all the document,
        retrieving a list of each match (between start and end). If not, only the first occurrence will be matched.

        :param start: The regular expression taken as lower bound.
        :param end: The regular expression taken as upper bound.
        :param as_list: If the result of the extraction is a list (True) or a single field (False, the default). In case
            of get the result as a list of elements), all the matches will be returned. In case of get only one element,
            only the first matching element will be returned.
        :param mods: A single or a list of custom user post-processors (i.e. functions that could alter the data
            extracted). The expected function should get and return a str value.
        :param deps: The string or list of string of the names of those fields that this field needs to have
            processed before.
        :param skip_new_lines: If the new line characters should be skipped (included) in pattern matching.
        """
        self.__start = start
        self.__end = end
        self.__as_list = as_list
        self.__skip_new_lines = skip_new_lines

        self.__regex = '{0}(.*?){1}'.format(start, end)
        self.__mods = [mods] if mods and not isinstance(mods, (list, tuple)) else mods or []
        self.__deps = [deps] if deps and not isinstance(deps, (list, tuple)) else deps or []

        self._model = None

    def __call__(self, model, *args, **kwargs):
        """ Realizes the extraction.

        :param args: All the positional parameters specified in Field superclass.
        :param model: The model who own this field instance.
        :return: The extracted data.
        """
        self._model = model

        # Extract all the elements from the content
        elements = re.findall(
            self.__regex, model.content(),
            re.DOTALL | re.MULTILINE if self.__skip_new_lines else re.MULTILINE
        )

        if elements:
            # If elements, process the field and the modifiers over all elements (or the fiers in case as_list = False)
            elements = elements if self.__as_list else elements[:1]
            result = []
            for element in elements:
                processed_value = self.process(element)

                # Apply modifiers
                for modifier in self.__mods:
                    processed_value = modifier(processed_value)

                result.append(processed_value)
            result = result if self.__as_list else result[0]
        else:
            result = [] if self.__as_list else None

        self._model = None

        return result

    @abc.abstractmethod
    def process(self, value):
        """ Processes the data extracted.

        This is an abstract method, and the subclasses must provide the behavior.

        :param value: The value to be processed.
        :return: The processed value.
        """

    @property
    def start(self):
        """ The regular expression taken as a lower bound. """
        return self.__start

    @property
    def end(self):
        """ The regular expression taken as a upper bound. """
        return self.__end

    @property
    def as_list(self):
        """ If the field is a list of results instead a sole result.

        :return: True or False depending on the field being or not a list of values.
        """
        return self.__as_list

    @property
    def modifiers(self):
        """ The modifiers this field has.

        :return: The modifiers of this field as a list of functors.
        """
        return self.__mods[:]

    @property
    def dependencies(self):
        """ The dependencies this field has.

        :return: The dependencies of this field as a list of strings.
        """
        return self.__deps[:]

    @property
    def skip_new_lines(self):
        """ If the field gathering process understands the skip new line chars as blanks.

        :return: True or False depending if the process is using new lines chars as blanks.
        """
        return self.__skip_new_lines


class BooleanField(Field):
    """ Field which points out whether a field exists or no. """

    def __init__(self, value, **kwargs):
        """ Initializes the field descriptor for boolean contents.

        :param value: The value to find
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        super().__init__(start=value, end=value, **kwargs)
        self.__value = value
        self._model = None

    def __call__(self, model, *args, **kwargs):
        """ Transforms the extracted value to True if there is a value or False if not. """
        self._model = model

        if self.skip_new_lines:
            result = bool(re.search(self.__value, model.content(), re.DOTALL))
        else:
            result = bool(re.search(self.__value, model.content()))

        self._model = None

        return result

    def process(self, value):
        """ This method exists because the warning of the class. It's not called at all. """
        raise NotImplementedError()


class CharField(Field):
    """ Field for processing text types. """

    def __init__(self, *args, prefix=None, suffix=None, strip_tags=False, stripped=False, **kwargs):
        """ Initializes the field descriptor for textual contents.

        The field also allows the user to add a prefix and suffix string to the field. This parameters should be valid
        fields of the model where the CharField defined. The developer should be aware that using the same field as
        prefix (or suffix) and base field could lead to a infinite loop. So be careful!

        The field allows a clearance of xml tags via "strip_tags" argument (disabled by default)

        :param args: All the positional parameters specified in Field superclass.
        :param prefix: The name of the field that belongs to the same model of this field and to be used as prefix of
            this field. If not None (the default) it should be the name of a valid existent field in the same model
            where the instance of this field is used. Otherwise, a ValueError will be raised when the method "cast" is
            being called.
        :param suffix: The name of the field that belongs to the same model of this field and to be used as prefix of
            this field. If not None (the default) it should be the name of a valid existent field in the same model
            where the instance of this field is used. Otherwise, a ValueError will be raised when the method "cast" is
            being called.
        :param strip_tags: If any html tag should be removed (strip_tags = True) or not. isabled by default.
        :param stripped: If the field is needed as stripped, that is, without leading and trailing white characters.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        super().__init__(*args, deps=[x for x in (prefix, suffix) if x], **kwargs)
        self.__prefix = prefix
        self.__suffix = suffix
        self.__strip_tags = strip_tags
        self.__stripped = stripped

    def process(self, value):
        """ Transforms the extracted value to the expected textual data. """
        casted_value = value.strip() if self.__stripped else value

        if self.__prefix:
            prefix = getattr(self._model, self.__prefix)
            if prefix:
                casted_value = '{0}{1}'.format(prefix, casted_value)
        if self.__suffix:
            suffix = getattr(self._model, self.__suffix)
            if suffix:
                casted_value = '{0}{1}'.format(casted_value, suffix)
        if self.__strip_tags:
            casted_value = re.sub('<[^<]+>', " ", casted_value)

        return casted_value


class IntegerField(Field):
    """ Field for processing integer types. """

    def __init__(self, *args, thousands_marks=('.', ','), **kwargs):
        """ Initializes the descriptor for integer types

        :param args: All the positional parameters specified in Field superclass.
        :param thousands_marks: A string or list of string with the decimal markers of the number if any. If specified,
            the marker or markers will be stripped out.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        super().__init__(*args, **kwargs)
        self.__thousands_marks = thousands_marks

    def process(self, value):
        """ Transforms the extracted value to the expected integer data. """
        if value is not None and value != '':
            for thousand_mark in self.__thousands_marks:
                value = value.replace(thousand_mark, '')
            return int(value.replace(',', '').replace('.', ''))
        else:
            return None


class FloatField(Field):
    """ Field for processing integer types. """

    def __init__(self, *args, decimal_mark='.', **kwargs):
        """ Initializes the descriptor for float types

        :param args: All the positional parameters specified in Field superclass.
        :param decimal_mark: The character which separes the decimal part of the float number. If not specified, '.' is
            assumed for decimal mark and ',' for thousands mark. If specified as ',', '.' is assumed for thousands mark.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        super().__init__(*args, **kwargs)
        self.decimal_mark = decimal_mark
        self.thousands_mark = ',' if decimal_mark == '.' else '.'

    def process(self, value):
        """ Transforms the extracted value to the expected integer data. """
        if value.count(self.decimal_mark) > 1:
            raise ValueError('Decimal mark cannot appear more than once ({})'.format(value))

        temp_mark = str(uuid.uuid4())
        value = value.strip().replace(self.decimal_mark, temp_mark)
        value = value.replace(self.thousands_mark, '')
        value = value.replace(temp_mark, '.')

        return float(value)


class DateField(Field):
    """ Field for processing files. """

    def __init__(self, *args, formats=None, **kwargs):
        """ Initializes the field descriptor for date contents.

        Works as a Field object, returning the content as a date. The field works using a set of formats to parse the
        date, so at least one format is required.

        The developer should be aware that using the same field as prefix (or suffix) and base field could lead to a
        infinite loop. So be careful!

        :param args: All the positional parameters specified in Field superclass.
        :param formats: The formats to be used to parse the date. It could be a single string or a list (or tuple) of
            strings, where each string is a date casting format. If no format is supplied, a ValueError will be raised.
            If no format can decode the data, a value of None will be returned.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        :raises ValueError: Any of the parameters is not valid.
        """
        super().__init__(self, *args, **kwargs)
        self.__formats = list(formats) if not isinstance(formats, (list, tuple)) else formats

    def process(self, value):
        """ Transforms the extracted value to the expected date.

        Does the required casting to a date value. This process will be accomplished by trying one by one all formats
        supplied at initialization time.
        """
        # TODO Hacer el método (y asegurarse de que termina, o bien devolviendo una fecha o bien devolviendo None).
        raise NotImplementedError()


class ModelField(Field):
    """ Field for processing a bunch of grouped fields. """

    def __init__(self, cls, *args, ignore_url_process=False, **kwargs):
        """ Initializes the field with the model which will parse the content delimited by "start" and "end" parameters.

        If the content delimited by "start" and "end" parameters is other than an url, that content will be processed by
        the class specified by cls parameter. If not (i.e. content delimited by "start" and "end" params is an url), a
        new connection will be performed retrieving  that content and parsing it with the model class. This behavior may
        be disabled by enabling the "ignore_url_process" parameter at initialization time.

        :param cls: The class that will parse the content delimited by "start" and "end" parameters.
        :param args: All the positional parameters specified in Field superclass.
        :param ignore_url_like_content: If the content delimited by "start" and "end" has a url structure (or a url
            query structure) and want to ignore the behaviour of making a new connection to that url to extract the
            content. It's False by default (i.e. do not gnore the behavior.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        Field.__init__(self, *args, **kwargs)

        self.__cls = cls
        self.__ignore_url_process = ignore_url_process

    def process(self, value):
        """ Transforms the extracted value in an instance of the class model specified in the initialization. """
        if value:
            params = {
                'proxies': self._model.proxies(),
                'disguise': self._model.disguise(),
                'wait_about': self._model.wait_about(),
                'enable_cache': self._model.cache_enabled(),
                'headers': self._model.request_headers(),
                'cookies': self._model.cookies(),
                'deep_encoding_discovery': self._model.deep_encoding_discovery(),
            }

            if self.__ignore_url_process:
                # No matter if the content is and url or not, we want to parse the content as-is
                return self.__cls(content=value, url=self._model.url(), **params)
            else:
                if is_url(value):
                    # Ok, it's an url, so let's download and parse the content.
                    return self.__cls(url=value, **params)
                elif value.startswith('/'):
                    # Maybe is an absolute url (i.e. hanging of the base url of the harvested site) so let's try against it
                    absolute_url = self._model.base_url() + value
                    if is_url(absolute_url):
                        return self.__cls(url=absolute_url, **params)

            # No way. It's a content. Well, at least is one less connection.
            return self.__cls(content=value, url=self._model.url(), **params)
        else:
            return None


class FileField(Field):
    """ Field for processing files. """

    def __init__(self, *args, upload_to, **kwargs):
        """ Initializes the file descriptor for processing files.

        Works as a Field object but, instead processing the content between the two delimiters (i.e. "start" and "end"
        parameters), downloads it to a file.

        :param upload_to: A local directory to save the file.
        :param args: All the positional parameters specified in Field superclass.
        :param kwargs: All the mandatory parameters specified in Field superclass.
        """
        super().__init__(*args, **kwargs)
        self.upload_to = upload_to

    def process(self, value):
        """ Downloads the content. """
        value = value.strip()
        if value[:2] == '//':
            value = 'http:' + value

        content, headers, _ = Model.touch(
            self.as_absolute(value),
            headers=self._model.request_headers(),
            proxy=self._model.proxy()
        )

        if 'Content-Disposition' in headers and len(re.findall(r'filename=(\S+)', headers['Content-Disposition'])) > 0:
            filename = re.findall(r'filename=(\S+)', headers['Content-Disposition'])[0].strip()
        else:
            filename = value

        file_path = self.get_file_path(filename)
        with open(file_path, 'wb') as out_file:
            out_file.write(content)

        return file_path

    def as_absolute(self, url):
        return url if self.is_absolute(url) else '{}/{}'.format(self._model.base_url(), url)

    @staticmethod
    def is_absolute(url):
        return bool(urlparse(url).netloc)

    def get_file_path(self, file_url):
        # TODO Lo mismo viene bien sacar esto a utilidades
        base_path = os.path.abspath(self.upload_to)
        if not os.path.exists(base_path):
            os.makedirs(base_path)

        filename_base, filename_extension = os.path.splitext(file_url.split('/')[-1])

        file_path = os.path.join(base_path, '{}{}'.format(filename_base, filename_extension))
        if os.path.exists(file_path):
            i = 1
            file_path = os.path.join(base_path, '{}-{}{}'.format(filename_base, i, filename_extension))
            while os.path.exists(file_path):
                i += 1
                file_path = os.path.join(base_path, '{}-{}{}'.format(filename_base, i, filename_extension))
        return file_path


class Headers:
    """ Guarda los datos de las cabeceras en caso de que haya hecho petición a través de la url.

    Se accederá de la forma headers.CAMPO, devolviendo el valor del header correspondiente al campo o None en caso de
    que no se encuentre.
    """

    def __init__(self, h=None):
        self.__h = h or {}

    def __getattr__(self, item):
        return self.__h.get(item, None)

    def __str__(self):
        return str(self.__h)


class CircularDependencyError(Exception):
    def __init__(self, fields):
        msg = 'The next fields are in conflict: {0}'.format(fields)
        Exception.__init__(self, msg)


class FieldNotFoundError(Exception):
    def __init__(self, field):
        msg = 'Field "{0}" not found in model'.format(field)
        Exception.__init__(self, msg)


class Model:
    """ Model to extract from a given content or from a http address. """
    cache = {}

    def __init__(
            self,
            url=None,
            content=None,
            proxies=None,
            disguise=False,
            post_data=None,
            wait_about=None,
            enable_cache=False,
            headers=None,
            cookies=None,
            deep_encoding_discovery=False,
    ):
        """ Initializes the model to extract from a content.

        Initializes the model with the content retrieved from the url specified
        in the parameter or directly with a textual content (but no both. If
        None or both are specified, a ValueError will be raised).

        :param url: The address from which retrieve the content to extract the model. If used with "content" parameter, the url will be saved as the url for the content, but the
            model will parse the content and not the source of url (i.e. will not make any request to that url).
        :param content: The content from which extract the model. If None, the model will retrieve the content from the source of the specified url. Defaults to None.
        :param proxies: Optional parameter which will contain the proxy config for connections. It must be provided as a dictionary mapping protocol names to URLs of proxies (as
            seen in the example of the description).
        :param disguise: Optional parameter which set the disguise mode. If True (the default), a random user agent is sent with the headers. If False, a default message is sent.
        :param post_data: Optional parameter which sends post data if its value is a dictionary. If false, a GET method is used.
        :param wait_about: Waits about the seconds specified. If nothing specified, the harvesting is made as soon as
            possible.
        :param enable_cache: If the cache should be enabled or not. Default is False.
        :param headers: A dictionary with the headers to be used as request headers for the query. It's useful in case of maintain a session. Defaults to None (i.e. no headers).
        :param cookies: The cookies (as a CookieJar or any subclass object) for maintaining a session. Default to None (i.e. no session).
        :param deep_encoding_discovery: If a deep analysis is needed to dicover the encoding. For this purpose, the 3rd party library "chardet" is needed. If not found, an error
            message will be displayed and the decode process will continue as if deep_codec_discovery wasn't activated (i.e. False). Defaults to False.
        :raises CircularDependencyError: If one or more of the fields declared as dependencies causes any form of
            circular dependency.
        :raises FieldNotFoundError: If one or more of the fields declared as dependencies does not exist in the field
            set of this model.
        :raises ValueError: If there is any problem with the input parameters.
        """
        if not url and not content:
            raise ValueError('Either "url" or "content" must be provided.')

        self.__wait_about = wait_about
        self.__proxies = proxies or []
        self.__disguise = disguise
        self.__post_data = post_data
        self.__deep_encoding_discovery = deep_encoding_discovery
        self.__content = None
        self.__cache_enabled = enable_cache
        self.__request_headers = headers or {}
        self.__response_headers = None
        self.__cookies = cookies
        self.__url = url

        self.__content = content or self.__get_content()

        # Extracting all the fields info.
        self.__extracted = False
        self.__extract()

    def __get_content(self):
        if self.cache_enabled() and self.url() in self.cache:
            # It's in cache so no need for making again the connection
            return self.cache[self.url()]
        else:
            # Cache is not activated or url is not in cache so let's connect
            self.__wait_for_connection()
            content, self.__response_headers, cookies = self.touch(
                self.url(),
                data=self.__post_data,
                headers=self.request_headers(),
                proxy=self.proxy(),
                cookies=self.__cookies,
            )

            content_type_args = {k.strip(): v for k, v in parse_qs(self.__response_headers['Content-Type']).items()}
            codecs_to_try = content_type_args['charset'][0] if 'charset' in content_type_args and content_type_args['charset'] else []

            decoded_content = force_decode(content, codecs_to_try, deep_encoding_discovery=self.__deep_encoding_discovery)

            if self.cache_enabled():
                self.cache[self.url()] = decoded_content

            return decoded_content

    def __wait_for_connection(self):
        """ Waits some time before doing any connection.

        It will wait some seconds, about the ones indicated by the user in initialization time (parameter "wait_about").
        It'll work only if "wait_about" parameter is specified. If not (it's value is None or negative) the method will
        do nothing.
        """
        if self.__wait_about is not None and not self.__content:
            seconds = float(self.__wait_about)
            if seconds > 0:
                time.sleep(uniform(seconds, seconds + 1.5))

    def __extract(self):
        """ Does the extraction for each of the fields in this model. """
        if not self.__extracted:
            fields = {
                name: getattr(self, name)
                for name in dir(self)
                if isinstance(getattr(self, name), Field)
                }

            dependencies = {
                name: field.dependencies
                for name, field in fields.items()
                }
            fields_ok = []
            fields_remaining = [f for f in dependencies]
            while fields_remaining:
                num_fields_remaining = len(fields_remaining)
                i = 0
                while i < num_fields_remaining:
                    field = fields_remaining.pop(0)
                    if dependencies[field]:
                        dependencies[field] = [
                            d for d in dependencies[field]
                            if d not in fields_ok
                            ]
                        if dependencies[field]:
                            fields_remaining.append(field)
                        else:
                            fields_ok.append(field)
                            result = fields[field](self)
                            setattr(self, field, result)
                    else:
                        fields_ok.append(field)
                        result = fields[field](self)
                        setattr(self, field, result)
                    i += 1
                if num_fields_remaining == len(fields_remaining):
                    raise CircularDependencyError(fields_remaining)

            self.__extracted = True

    def content(self):
        """ Shows the content of this particular model.

        :return: The content this model uses to extract the fields data.
        """
        return self.__content

    def wait_about(self):
        """ Shows the approx. time to wait before making a request.

        :return: The time or None in case no time was setted.
        """
        return self.__wait_about

    def cache_enabled(self):
        """ If the cache is disable for this Model.

        :return: True if it's enabled, False otherwise.
        """
        return self.__cache_enabled

    def deep_encoding_discovery(self):
        """ If deep encoding is activated for this model

        :return: True if it's activated or False otherwise.
        """
        return self.__deep_encoding_discovery

    def url(self):
        """ Returns the url used for this model.

        :return: A string value for the url or None in case of no url provided in initialization time
        """
        return self.__url

    def request_headers(self):
        """ Returns the (request) headers used for this model as a dictionary. """
        return self.__request_headers

    def response_headers(self):
        """ Returns the (response) headers used for this model as a dictionary. """
        return self.__response_headers

    def cookies(self):
        """ Returns the cookies stored by this model.

        :return: A CookieJar (or any of its subclasses) object.
        """
        return self.__cookies

    def base_url(self):
        """ Returns the base url of the url to process by this Model.

        :return: The base url of the url to be processed by this model or None in case of this model were created directly with a content (in witch case it will return None).
        """
        parsed_url = urlparse(self.url())
        return '{0}://{1}'.format(parsed_url[0], parsed_url[1])

    def agent(self):
        """ Returns a Web agent.

        If the harvester is configured with "disguise" parameter, the user agent will be one out of the existent agents. If not, the agent will be the harvester user agent.
        """
        return choice(USER_AGENTS) if self.__disguise else 'Harvester v.{} ({})'.format(__version__, __github_url__)

    def disguise(self):
        """ Returns if the model is or not in disguise model. """
        return self.__disguise

    def proxies(self):
        """ Returns the list of proxies this model has. """
        return self.__proxies

    def proxy(self):
        """ Returns a random proxy of those specified in initialization time.

        :return: A dictionary with two schemas of access for the randomly chosen proxy, http and https. In case of no proxies specified in initialization time, the return value
            will be a empty dictionary.
        """
        if self.__proxies:
            proxy = choice(self.__proxies)
            return {'http': proxy, 'https': proxy, }
        else:
            return {}

    def process_meta(self, content):
        """ Process all the metainformation specified by the inner Meta class of the model.

        :param content: The content to be preprocessed.
        :return: The content preprocessed.
        """
        if getattr(self, 'Meta', False):
            meta = getattr(self, 'Meta')
            result_content = content
            if getattr(meta, 'drop_before', False):
                result_content = self.__process_drop_before(meta.drop_before, result_content)
            if getattr(meta, 'drop_after', False):
                result_content = self.__process_drop_after(meta.drop_after, result_content)
            return result_content
        else:
            return content

    @staticmethod
    def __process_drop_before(tag, content):
        """ Removes all the content before the reg_exp specified by drop_before. """
        m = re.search(r'(?:{0})(.*?$)'.format(tag), content, re.DOTALL | re.IGNORECASE)
        return m.group(1) if m else content

    @staticmethod
    def __process_drop_after(tag, content):
        """ Removes all the content after the reg_exp specified by drop_after. """
        m = re.search(r'(^.*?)(?:{0})'.format(tag), content, re.DOTALL | re.IGNORECASE)
        return m.group(1) if m else content

    @staticmethod
    def touch(url, data=None, headers=None, proxy=None, cookies=None):
        """ Touches the given url.

        The proxy to use may be specified (if needed, is optional) in two forms:
        1. As an IP: an string representing a valid IP. In this case, the proxy will be used by all the needed protocols.
        2. As a dictionary: The keys will be the protocols and the values will be the ip to use in this protocols. An example of this is as follows:
        proxy = {
            'http': '82.31.89.21',
            'https': '82.31.89.27'
        }

        :param url: The url to connect to.
        :param data: In case of a POST or PUT method, the data to be sent. Defaults to None.
        :param headers: The headers to send along with the request. Should be represented as a dictionary.
        :param proxy: The proxy through which to connect. May be specified as a dictionary or a string (see above for more information). Defaults to None (i.e. no proxy).
        :return: A tuple in the form (content, headers, cookies) representing the content of the response as a byte-string, the response headers as a dictionary and the cookies
            sent by the server.
        """
        # Process the data
        data_to_send = urlencode(data).encode('utf-8') if data else None

        # Prepare the request
        cj = cookies or http.cookiejar.CookieJar()
        opener = build_opener(
            ProxyHandler(proxy or {}),
            HTTPCookieProcessor(cj)
        )
        opener.addheaders = (headers or {}).items()

        # Do the connection
        response = opener.open(fix_url(url), data=data_to_send)

        return (
            response.read(),  # The content of the get method.
            {k: v for k, v in response.headers.items()},  # The headers as a dictionary
            cj,  # The cookies
        )
