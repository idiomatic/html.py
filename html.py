# Copyright 2005-2006, by R. Brian Harrison.  All rights reserved.

__VERSION__ = '3.0'

# XXX normalize exceptions (IndexError, StopIteration, AttributeError)
# XXX tempted to write a str wrapper to erradicate is_string()'s

"""HTML composition and decomposition within Python's syntax
designed to retrieve or modify data tersely.

    doc = tag.urlopen('http://www.digg.com/')
    if head in doc.html and title in doc.html.title:
        print 'title = %s' % doc.html.head.title
    print 'table rows = %d' % len(doc.findall(by.tr))
    for image in doc.findall(by.and(by.img, by.width('64'))):
        image.height *= 2
        image.width *= 2
        image.parent.append(img(a('(original)', href=image.href)))
    rows = doc.getattrs('findall_td.parents', iter([ ]))
    try:
        while True:
            rows.next().bgcolor = '#000000'
            rows.next().bgcolor = '#333333'
    except StopIteration:
        pass
    print str(doc)                          # HTML rendition
    print repr(doc)                         # Python rendition
"""

import re
import sys
import UserDict

# type tools

def is_string(s):
    return (isinstance(s, basestring)
            or (isinstance(s, cursor) and is_string(s.delegate)))

def is_index_or_slice(i):
    return isinstance(i, int) or isinstance(i, slice)

def is_sequence(l):
    return isinstance(l, tuple) or isinstance(l, list)

def is_entity(e):
    return (isinstance(e, entity)
            or (isinstance(e, cursor) and is_entity(e.delegate)))

def is_tag(t):
    return hasattr(entities, t)

# string tools

def dequote_identifier(s):
    s = s.lower()
    if s.endswith('_') and not s.startswith('_'):
        return s[:-1]
    else:
        return s

def quote_identifier(s):
    if s == 'class' or hasattr(sys.modules['__builtin__'], s):
        return s + '_'
    else:
        return s

def sgml_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def sgml_escape_quotes_too(s):
    return sgml_escape(s).replace('"', '&quot;')

def substfmt(value, format, equals_format='', test_value=''):
    # example usage:
    # substfmt(v, (k + '=%s' + ';'))
    if value == test_value:
        format = equals_format
    if '%' in format:
        return format % value
    else:
        return format

# sequence/list tools

def first(iterable):
    if is_sequence(iterable):
        return iterable[0]
    else:
        return iterable.next()

def iterskip(n, iterable):
    while n > 0:
        void = iterable.next()
        n -= 1

def nth(n, iterable):
    assert(n >= 0)
    if is_sequence(iterable):
        return iterable[n]
    else:
        try:
            iterskip(n, iterable)
            return iterable.next()
        except StopIteration:
            raise IndexError

def slice1(s, iterable):
    if is_sequence(iterable):
        return iterable[s]
    else:
        try:
            iterskip(s.start, iterable)
            n = s.stop - s.start
            ret = [ ]
            while n > 1:
                ret.append(iterable.next())
                if s.step > 1:
                    iterskip(s.step, iterable)
                    n -= s.step
                else:
                    n -= 1
            return ret
        except StopIteration:
            raise IndexError

def slice2(m, n, iterable):
    return slice1(slice(m, n), iterable)

def slice3(m, n, i, iterable):
    return slice1(slice(m, n, i), iterable)

def last(iterable):
    if is_sequence(iterable):
        return iterable[-1]
    while True:
        try:
            value = iterable.next()
        except StopIteration:
            return value

# exceptions

class AttributeExists: pass
class AttributeNonexistent: pass
class RaiseSomething: pass

args_re = re.compile('([^_]+_?)(?:_|$)')

class criterion:
    """curries for specifying a condition.

    CAUTION: some are methods, some are attributes.

    criterion.first
    criterion.last
    criterion.nth(N)
    criterion.slice2(M, N)        => criterion.slice3(M, N, None)
    criterion.slice3(M, N, I)
    criterion.substring('STRING')
    criterion.regexp('(PATTERN)')
    criterion.and_(CRITERIA)      => reduce(and, CRITERIA)
    criterion.or_(CRITERIA)       => reduce(or, CRITERIA)
    criterion.attribute('ATTR', 'VALUE')
    criterion.ATTR('VALUE')
    criterion.TAG                 => criterion.tag('TAG')
    criterion.has_ATTR            => criterion.ATTR(AttributeExists)
    criterion.ATTR_PARAMS         => criterion.ATTR(PARAMS)
    """
    #def first(self):
    #    return lambda iterable: first(iterable)
    #def last(self):
    #    return lambda iterable: last(iterable)
    #def nth(self, n):
    #    return lambda iterable: nth(int(n), iterable)
    #def slice1(self, s):
    #    return lambda iterable: slice1(s, iterable)
    #def slice2(self, m, n):
    #    return self.slice1(slice(m, n))
    #def slice3(self, m, n, i):
    #    return self.slice1(slice(m, n, i))
    def substring(self, substring):
        return lambda item: is_string(item) and substring in item
    #def regexp(self, regexp):
    #    if is_string(regexp):
    #        regexp = re.compile(regexp)
    #    return lambda item: is_string(item) and regexp.search(item)
    def and_(self, *criteria):
        and_lambda = lambda a, b: a and b
        return lambda item: reduce(and_lambda, [ c(item) for c in criteria ]) 
    def or_(self, *criteria):
        or_lambda = lambda a, b: a or b
        return lambda item: reduce(or_lambda, [ c(item) for c in criteria ]) 
    def attribute(self, attr, value=AttributeExists):
        if value is AttributeExists:
            return lambda item: is_entity(item) and attr in item.attributes
        else:
            return lambda item: (
                is_entity(item)
                and item.attributes.get(attr, AttributeNonexistent) == value
                )
    def __getattr__(self, attr):
        # criterion.body  =>  criterion.tag(body)
        if is_tag(attr):
            assert(attr != 'tag')
            #print "criterion tag(%r)" % (attr,)
            return self.tag(attr)
        elif attr.startswith('has_'):
            #print "criterion has %s()" % (attr[4:],)
            return self.attribute(attr[4:])
        elif attr.startswith('by_'):
            #print "criterion by %s(?)" % (attr[3:],)
            return getattr(self, attr[3:])
        else:
            attrs = args_re.findall(attr)
            if len(attrs) > 1:
                #print "criterion %s%r" % (attrs[0], tuple(attrs[1:]))
                return getattr(self, attrs[0])(*attrs[1:])
            else:
                #print "criterion %s(?)" % (attr,)
                attr = dequote_identifier(attr)
                return lambda value=AttributeExists: self.attribute(attr, value)
by = criterion()

class mixin: pass

class renderable(mixin):
    def __str__(self):
        # XXX return self.as_html(path(self))
        return self.as_html()
    def __repr__(self):
        # XXX return self.as_python(path(self))
        #return self.as_python()
        return self.as_info()

class searchable(mixin):
    """adds traversal and searching to a sequence.

    list methods:
    list(searchable)
    searchable[N]
    searchable[M:N]
    searchable[M:N:I]
    'SUBSTRING' in searchable
    CLASS in searchable
    ENTITY in searchable
    searchable.first
    searchable.last
    searchable.nth_N
    searchable.slice2_M_N
    searchable.slice3_M_N_I

    searching:
    searchable.match(LAMBDA)
    searchable.matchall(LAMBDA)
    searchable.search(LAMBDA, DEPTH)
    searchable.findall(LAMBDA, NEST, DEPTH) => MATCHES

    searchable.match_by_CRITERION_PARAMS
    searchable.matchall_by_CRITERION_PARAMS
    searchable.search_by_CRITERION_PARAMS
    searchable.findall_by_CRITERION_PARAMS

    searchable.match_TAG
    searchable.matchall_TAG
    searchable.search_TAG
    searchable.findall_TAG

    searchable.TAG
    searchable.all_TAG

    searchable.getattrs(ATTRS, default=raise)
    """
    def __contains__(self, item):
        #print "searchable __contains__"
        if isinstance(item, type):
            # find an item of this class
            #print "searchable __contains__ type"
            for c in self:
                if type(c) == item:
                    return True
            else:
                return False
        elif is_string(item):
            #print "searchable __contains__ string"
            return item in self.as_text()
        else:
            #print "searchable __contains__ ?"
            return False
    def first(self):
        return first(self)
    def last(self):
        return last(self)
    def nth(self, n):
        return nth(n, self)
    def slice1(self, s):
        return slice1(s, self)
    def slice2(self, m, n):
        return slice2(m, n, self)
    def slice3(self, m, n, i):
        return slice3(m, n, i, self)
    def match(self, fn):
        return self.matchall(fn).next()
    def matchall(self, fn):
        return self.findall(fn, nest=0, max_depth=1)
    def search(self, fn, max_depth=sys.maxint):
        return self.findall(fn, nest=0, max_depth=max_depth).next()
    def findall(self, fn, nest=1, min_depth=1, max_depth=sys.maxint, depth_first=True):
        if isinstance(self, cursor):
            work = [ self ]
        else:
            work = [ cursor(self, path(), None) ]
        while work:
            e = work.pop(0)
            if len(e.ancestors) >= min_depth:
                if fn(e):
                    yield e
                    if not nest:
                        continue
            if len(e.ancestors) < max_depth:
                if is_entity(e):
                    # "magically" wraps each item in its contents with
                    # another cursor() proxy with its relative position.
                    new_work = list(e)
                    if depth_first:
                        work = new_work + work
                    else:
                        work += new_work
    def __getattr__(self, attr):
        #print "searchable __getattr__ %s" % attr
        if '_' in attr:
            firstword, rest = attr.split('_', 1)
            if firstword in ('slice1' 'slice2', 'slice3', 'nth'):
                return getattr(self, firstword)(map(int, rest.split('_')))
            elif firstword in ('match', 'matchall', 'search', 'findall'):
                return getattr(self, firstword)(getattr(by, rest))
            elif attr.startswith('all_'):
                return list(self.findall(getattr(by, rest)))
            else:
                raise AttributeError, attr
        elif is_tag(attr):
            try:
                return self.match(by.tag(attr))
            except StopIteration:
                raise AttributeError, attr
        else:
            raise AttributeError, attr
    def getattrs(self, attrs, default=RaiseSomething):
        if is_string(attrs):
            attrs = attrs.split('.')
        try:
            return reduce(getattr, attrs, self)
        except AttributeError:
            if default is RaiseSomething:
                raise
        return default

class entity(object, UserDict.DictMixin, searchable, renderable):
    """structured recursive container with tag, attributes, and contents.

    dict methods access of attributes, e.g.:
      entity.keys()                 => entity.attributes.keys_not_tag()
      entity['ATTR']

    dict method access of sub-entities (unnecessary):
      entity['TAG']

    attribute method access of attributes (special case):
      entity.ATTR

    attribute method access of attributes:
      entity.TAG

    list methods acccess contents, e.g.:
      list(entity)                  => entity.contents
      iter(entity)                  => iter(entity.contents)
      CLASS in entity               => CLASS in entity.contents
      ENTITY in entity              => ENTITY in entity.contents
      entity[N]                     => entity.contents[N]
      entity[M:N]                   => entity.contents[M:N]
      entity[M:N:I]                 => entity.contents[M:N:I]

    rendering (see renderable):
      str(entity)                   => entity.as_html()
      repr(entity)                  => entity.as_python()
      entity.as_text()
    """
    module_prefix = __name__ + '.'
    def __init__(self, *flow, **attrs):
        if 'tag' in attrs:
            self.__dict__['attributes'] = attributes(**attrs)
        else:
            tag = dequote_identifier(self.__class__.__name__)
            self.__dict__['attributes'] = attributes(tag=tag, **attrs)
        self.__dict__['contents'] = contents(flow)
    #def __lt__(self, other):
    #    # XXX compare self.attributes?
    #    return self.contents < self.__cast(other)
    #def __le__(self, other):
    #    return self.contents <= self.__cast(other)
    #def __eq__(self, other):
    #    return self.contents == self.__cast(other)
    #def __ne__(self, other):
    #    return self.contents != self.__cast(other)
    #def __gt__(self, other):
    #    return self.contents > self.__cast(other)
    #def __ge__(self, other):
    #    return self.contents >= self.__cast(other)
    #def __cast(self, other):
    #    if isinstance(other, self.__class__):
    #        return other.contents
    #    else:
    #        return other
    def __cmp__(self, other):
        #print "entity __cmp__"
        return (cmp(type(self), type(other))
                or cmp(self.contents, other.contents)
                or cmp(self.attributes, other.attributes))
    def __contains__(self, item):
        #print "entity __contains__"
        if item in self.attributes:
            #print "entity __contains__ in attributes"
            return True
        elif item in self.contents:
            #print "entity __contains__ in contents"
            return True
        else:
            #print "entity __contains__ delegating to searchable"
            return searchable.__contains__(self, item)
    def __len__(self):
        return len(self.contents)
    def __iter__(self):
        return iter(self.contents)
    def __getitem__(self, key):
        if is_index_or_slice(key):
            return self.contents[key]
        else:
            return self.attributes[key]
    def __setitem__(self, key, value):
        if is_index_or_slice(key):
            self.contents[key] = value
        else:
            self.attributes[key] = value
    def __delitem__(self, key):
        if is_index_or_slice(key):
            del self.contents[key]
        else:
            del self.attributes[key]
    #def __getslice__(self, i, j):
    #    return self.contents[i:j]
    #def __setslice__(self, i, j, other):
    #    i = max(i, 0)
    #    j = max(j, 0)
    #    if isinstance(other, self.__class__):
    #        self.contents[i:j] = other.data
    #    elif isinstance(other, type(self.contents)):
    #        self.contents[i:j] = other
    #    else:
    #        self.contents[i:j] = list(other)
    #def __delslice__(self, i, j):
    #    i = max(i, 0)
    #    j = max(j, 0)
    #    del self.contents[i:j]
    #def __add__(self, other):
    #    if isinstance(other, self.__class__):
    #        return self.__class__(self.contents + other.data)
    #    elif isinstance(other, type(self.contents)):
    #        return self.__class__(self.contents + other)
    #    else:
    #        return self.__class__(self.contents + list(other))
    #def __radd__(self, other):
    #    if isinstance(other, self.__class__):
    #        return self.__class__(other.data + self.contents)
    #    elif isinstance(other, type(self.contents)):
    #        return self.__class__(other + self.contents)
    #    else:
    #        return self.__class__(list(other) + self.contents)
    #def __iadd__(self, other):
    #    if isinstance(other, self.__class__):
    #        self.contents += other.data
    #    elif isinstance(other, type(self.contents)):
    #        self.contents += other
    #    else:
    #        self.contents += list(other)
    #    return self
    #def __mul__(self, n):
    #    return self.__class__(self.contents*n)
    #__rmul__ = __mul__
    #def __imul__(self, n):
    #    self.contents *= n
    #    return self
    def append(self, item):
        self.contents.append(item)
    def insert(self, i, item):
        self.contents.insert(i, item)
    def pop(self, i=-1):
        return self.contents.pop(i)
    def remove(self, item):
        self.contents.remove(item)
    def count(self, item):
        return self.contents.count(item)
    def index(self, item, *args):
        return self.contents.index(item, *args)
    def reverse(self):
        self.contents.reverse()
    def sort(self, *args):
        self.contents.sort(*args)
    def extend(self, other):
        if isinstance(other, entity):
            self.contents.extend(other.contents)
        else:
            self.contents.extend(other)
    def __getattr__(self, attr):
        #print "entity __getattr__ %s" % attr
        try:
            return getattr(self.attributes, attr)
        except KeyError:
            return searchable.__getattr__(self, attr)
    def __setattr__(self, attr, value):
        #print "entity __setattr__ %s" % attr
        self.attributes[attr] = value
    def __delattr__(self, attr):
        try:
            del self.attributes.attr
        except:
            # ??? unnecessary?
            del self.contents.attr
    def keys(self):
        return self.attributes.keys_not_tag()
    #def items(self): return self.attributes.items()
    def get_tag(self):
        return self.attributes['tag']
    def set_tag(self, value):
        self.attributes['tag'] = value
    tag = property(get_tag, set_tag)
    def as_html(self):
        return '<%s>%s</%s>' % (self.attributes.as_html(),
                                self.contents.as_html(), self.tag)
    def as_python(self, module_prefix=None):
        if module_prefix is None:
            module_prefix = self.module_prefix
        return '%s%s(%s)' % (
            module_prefix, quote_identifier(self.tag),
            ','.join(self.contents.as_python_args(module_prefix)
                     + self.attributes.as_python_args())
            )
    def as_text(self):
        return self.contents.as_text()
    def as_info(self):
        return '<%s.%s [<%s%s>%s]>' % (
            self.__module__, self.__class__.__name__,
            self.tag,
            substfmt(self.attributes.as_info(), ' %s'),
            substfmt(self.contents.as_info(), '%%s</%s>' % self.tag))
    __str__ = renderable.__str__
    __repr__ = renderable.__repr__
    # XXX replace?

class quiet_entity(entity):
    def as_html(self):
        return ''
    def as_text(self):
        return ''

class empty_entity(entity):
    def as_html(self):
        return '<%s>' % (self.attributes.as_html(),)

class comment(entity):
    def as_html(self):
        return '<!--%s-->' % (self.contents.as_html(),)

class document(entity):
    def as_html(self):
        return self.contents.as_html()
    def as_text(self):
        return ''

class contents(list, searchable, renderable):
    """simple concatenating recursive container."""
    def first(self):
        return self[0]
    def last(self):
        return self[-1]
    def nth(self, n):
        return self[n]
    def slice1(self, s):
        return self[s]
    def slice2(self, m, n):
        return self[m:n]
    def slice3(self, m, n, i):
        return self[m:n:i]
    def as_html(self):
        def as_html(c):
            if is_string(c):
                return c
            else:
                return c.as_html()
        return ''.join(map(as_html, self))
    def as_python(self, module_prefix=None):
        return repr(self.as_python_args(module_prefix))
    def as_python_args(self, module_prefix=None):
        def as_python(c):
            if is_string(c):
                return repr(c)
            else:
                return c.as_python(module_prefix)
        return map(as_python, self)
    def as_text(self):
        def as_text(c):
            if is_string(c):
                return c
            else:
                return c.as_text()
        return ''.join(map(as_text, self))
    def as_info(self):
        if len(self) == 0:
            return ''
        elif is_string(self[0]):
            text = self[0].replace('\n', ' ').strip()
            if len(text) > 16 or len(self) > 1:
                return text[:16] + '...'
            else:
                return text
        elif is_entity(self[0]):
            return '<%s...>' % self[0].tag
        else:
            raise "extraneous object %r" % type(self[0])
    __str__ = renderable.__str__
    __repr__ = renderable.__repr__
    
class attributes(dict, UserDict.DictMixin, renderable):
    """unordered key-value container."""
    def __init__(self, **attrs):
        for attr, value in attrs.items():
            # class_ => class
            # id_ =-> id
            self[dequote_identifier(attr)] = value
    # object attribute shortcuts
    def __getattr__(self, attr):
        return self[dequote_identifier(attr)]
    def __setattr__(self, attr, value):
        #print "attributes __setattr__ %s" % attr
        self[dequote_identifier(attr)] = str(value)
    def __delattr__(self, attr):
        del self[dequote_identifier(attr)]
    def __getstate__(self):
        return dict(self)
    def keys_not_tag(self):
        for k in self.keys():
            if k != 'tag':
                yield k
    def as_html(self):
        return ' '.join(self.as_html_args())
    def as_html_args(self):
        def as_html(k, v):
            #k = dequote_identifier(k) ???
            if v is None:
                return k
            else:
                v = sgml_escape_quotes_too(str(v))
                return '%s="%s"' % (k, v)
        return ([ self['tag'] ]
                + [ as_html(k, self[k]) for k in self.keys_not_tag() ])
    def as_python(self):
        return dict.__repr__(self)
    def as_python_args(self):
        return [ '%s=%r' % (quote_identifier(k), self[k])
                 for k in self.keys_not_tag() ]
    def as_text(self):
        return ''
    def as_info(self):
        keys = list(self.keys_not_tag())
        for k in [ 'id', 'name', 'class' ] + keys:
            if k in self:
                break
        else:
            return ''
        info = '%s=%r' % (k, self[k])
        if len(keys) > 1:
            info += '...'
        return info
    __str__ = renderable.__str__
    __repr__ = renderable.__repr__

class view(object):
    """
    (unvetted)
    as_html(path)
    as_python(path)
    as_text(path)
    """
    def __init__(self):
        raise "NYI"

class matches(tuple, searchable):
    """lazy immutable list of search results.
    
    list(MATCHES)           => [ CURSOR... ]
    MATCHES.parents
    """
    def __init__(self, matches):
        raise "NYI"
        if is_generator(matches):
            self.matches = [ ]
            self.match_maker = matches
        else:
            self.matches = matches
            self.match_maker = None
    def __len__(self):
        raise "NYI"
    def __getitem__(self, key):
        if self.match_maker is not None:
            if key >= 0:
                try:
                    remainder = key - len(self.matches)
                    while remainder > 0:
                        c = self.match_maker.next()
                        self.matches.append(c)
                        remainder -= 1
                except StopIteration:
                    self.match_maker = None
                    raise IndexError
            else:
                try:
                    while True:
                        self.matches.append(self.match_maker.next())
                except StopIteration:
                    self.match_maker = None
        return self.matches[key]
    def __iter__(self):
        for c in self.matches:
            yield c
        if self.match_maker is not Null:
            try:
                while True:
                    c = self.match_maker.next()
                    self.matches.append(c)
                    yield c
            except StopIteration:
                self.match_maker = None
    def get_parents(self):
        for c in self:
            yield c.parent
    parents = property(get_parents)
    """tupleitize a list:
    def __setitem__(self, key, value): raise
    def __delitem__(self, key): raise
    def append(self, junk): raise
    def extend(self, junk): raise
    def insert(self, junk): raise
    def pop(self, junk=None): raise
    def remove(self, junk): raise
    def reverse(self): raise
    def sort(self, junk=None): raise
    def __iadd__(self, junk): raise
    def __imul__(self, junk): raise
    """

class path(list, searchable):
    """
    list(path)              => [ cursor(...)... ]
    #path.parents
    """
    #def get_parents(self):
    #    for c in self:
    #        yield c.parent
    #parents = property(get_parents)

class cursor(object, searchable, renderable):
    """entity proxy with positional information.

    cursor.ATTR            => CURSOR.delegate.ATTR
    cursor.next
    cursor.previous
    cursor.sibbling(OFFSET)
    cursor.parent
    """
    def __init__(self, delegate, ancestors, which_child):
        self.delegate = delegate
        self.ancestors = ancestors
        self.which_child = which_child
    def __getitem__(self, key):
        return cursor(self.delegate[key], self.ancestors + [ self ], key)
    def __delitem__(self, key):
        """WARNING: the offsets stored in other cursors may be affected by deletion."""
        self.delegate[key] = ''
    def __setitem__(self, key, value):
        self.delegate[key] = value
    def __contains__(self, item):
        # no need for cursoritization
        #print "cursor __contains__"
        return item in self.delegate
    #def __iter__(self):
    #    return iter(self.delegate)
    #def __len__(self):
    #    return len(self.delegate)
    def sibbling(self, offset):
        return self.parent[self.which_child + offset]
    def get_next(self):
        return self.sibbling(1)
    next = property(get_next)
    def get_previous(self):
        return self.sibbling(-1)
    previous = property(get_previous)
    def get_parent(self):
        try:
            return self.ancestors[-1]
        except IndexError:
            return None
    parent = property(get_parent)
    def __getattr__(self, attr):
        # ??? unsure if all __getitem__ covers everything
        #print "cursor __getattr__ %s" % attr
        return getattr(self.delegate, attr)
    #XXXdef __setattr__(self, attr, value):
    #    return setattr(self.delegate, attr, value)
    def __str__(self):
        if is_string(self.delegate):
            return self.delegate
        else:
            return renderable.__str__(self)
    def __repr__(self):
        if is_string(self.delegate):
            return repr(self.delegate)
        else:
            return renderable.__repr__(self)

tags = ('html',
        # head
        'head', 'title',
        # document body
        'body',
        # text markup, fontstyle
        'tt', 'i', 'b', 'big', 'small',
        'em', 'strong', 'u', 'dfn', 'code', 'samp',
        'kbd', 'var', 'cite', 'abbr', 'acronym', 
        # text markup, special
        'a', 'map', 'q', 'sub', 'sup', 'span', 'bdo',
        # contents model, block
        'p',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ol', 'ul', 'li', 'dt', 'dd',
        'pre',
        'dl', 'div', 'noscript', 'blockquote', 'address',
        # form
        'form', 'select', 'textarea', 'label', 'button',
        'fieldset', 'legend', 'optgroup', 'option',
        # table
        'table', 'tr', 'th', 'td',
        'thead', 'tbody', 'tfoot', 'colgroup', 'caption',
        # junk
        'strike',
        'basefont', 'layer', 'ilayer', 'font',
        # frames
        'frameset', 'frame', 'iframe', 'noframes',
        # misc markup
        'del', 'ins',
        'blink', 'fontsize', 'center', 'nobr',
        'wbr', 'noembed',
        # hrrrm... quiet?
        'style', 'script',
)
quiet_tags = ('applet', 'embed', 'object')
empty_tags = ('br', 'area', 'link', 'img', 'param', 'hr',
             'input', 'col', 'base', 'meta', '!doctype',
             'ssi')

class entities:
    pass

def register_entity(tag, tag_class):
    quoted_tag = quote_identifier(tag)
    globals()[quoted_tag] = tag_class
    setattr(entities, quoted_tag, tag_class)
def add_entity(tag):
    register_entity(tag, type(tag, (entity,), { }))
def add_quiet_entity(tag):
    register_entity(tag, type(tag, (quiet_entity,), { }))
def add_empty_entity(tag):
    register_entity(tag, type(tag, (empty_entity,), { }))

for t in tags:
    add_entity(t)
for t in quiet_tags:
    add_quiet_entity(t)
for t in empty_tags:
    add_empty_entity(t)

entities.comment = comment
entities.document = document


__all__ = ([ 'is_string', 'is_index_or_slice', 'is_sequence', 'is_entity',
             'is_tag',
             'first', 'iterskip', 'nth', 'slice1', 'slice2', 'slice3', 'last',
             'AttributeExists',
             'criterion', 'by', 'entity', 'contents', 'attributes', 'view',
             'matches', 'path', 'cursor',
             'document' ]
           + map(quote_identifier, tags)
           + map(quote_identifier, quiet_tags)
           + map(quote_identifier, empty_tags)
           + [ 'parser', 'urlopen', 'parse', 'read', 'openfile' ])

# parsing

import HTMLParser
# XXX http://mail.python.org/pipermail/python-list/2002-August/119930.html
#HTMLParser.interesting_cdata = HTMLParser.interesting_normal
class parser(HTMLParser.HTMLParser):
    def __init__(self):
        self.urlopen_user_agent = None
        self.result = None
    def first_entity(self):
        for t in self.result:
            if is_entity(t):
                return t
        raise HTMLParser.HTMLParseError
    def parse(self, data):
        self.reset()
        self.feed(data)
        self.close()
        return self.result
    def urlopen(self, url):
        self.reset()
        import urllib
        if self.urlopen_user_agent is not None:
            urllib.URLopener.version = self.urlopen_user_agent
        f = urllib.urlopen(url)
        data = f.read(8192)
        while data != '':
            self.feed(data)
            data = f.read(8192)
        self.close()
        return self.result
    def reset(self):
        HTMLParser.HTMLParser.reset(self)
        self.result = document()
        self.stack = [ self.result ]
    def handle_starttag(self, tag_name, attrs):
        d = dict(attrs)
        if (tag_name in ('p', 'tr', 'th', 'td', 'option')
            and tag_name == self.stack[-1].tag):
            # implied </tag_name>
            self.stack.pop()
        try:
            t = getattr(entities, tag_name)(**d)
        except AttributeError:
            #raise "parser key error for %s" % tag_name
            t = entity(tag=tag_name, **d)
        self.stack[-1].contents.append(t)
        if t.tag not in empty_tags:
            self.stack.append(t)
    def handle_data(self, data):
        self.stack[-1].contents.append(data)
    def handle_charref(self, data):
        self.handle_data('&#%s;' % data)
    def handle_entityref(self, name):
        self.handle_data('&%s;' % name)
    def handle_endtag(self, tag_name):
        if tag_name in empty_tags:
            return
        # HACK: try to find possibly mismatched closing tag
        original_stack = self.stack[:]
        while len(self.stack) > 0:
            t = self.stack.pop()
            if t.tag == tag_name: break
        else:
            self.stack = original_stack
    def handle_comment(self, data):
        self.stack[-1].contents.append(comment(data))
    def parse_endtag(self, i):
        #http://marc.free.net.ph/message/20041022.235258.ada7712d.html
        rawdata = self.rawdata
        assert rawdata[i:i+2] == '</', 'unexpected call to parse_endtag'
        match = HTMLParser.endendtag.search(rawdata, i+1) # >
        if not match:
            return -1
        j = match.end()
        match = HTMLParser.endtagfind.match(rawdata, i) # </ + tag + >
        if not match:
            # HACK
            self.handle_data(rawdata[i:j])
            return j
            self.error('bad end tag: %r' % rawdata[i:j])
        tag = match.group(1)
        #START BUGFIX
        if self.interesting == HTMLParser.interesting_cdata:
            #we're in of of the CDATA_CONTENT_ELEMENTS
            if (tag.lower() == self.lasttag
                and tag.lower() in self.CDATA_CONTENT_ELEMENTS):
               #its the end of the CDATA_CONTENT_ELEMENTS tag we are in.
               self.handle_endtag(tag.lower())
               self.clear_cdata_mode()  #backto normal mode
            else:
               #we're inside the CDATA_CONTENT_ELEMENTS tag still. throw the tag to handle_data instead.
               self.handle_data(match.group())
        else:
            #we're not in a CDATA_CONTENT_ELEMENTS tag. standard ending:
            self.handle_endtag(tag.lower())
        return j

def urlopen(url):
    doc = parser().urlopen(url)
    doc.url = url
    return doc

def parse(data):
    return parser().parse(data)

def read(file):
    return parse(file.read())

def openfile(path):
    doc = read(open(path))
    doc.path = path
    return doc

def testdoc():
    return html(body('foo', br(), p('bar', class_=42), bgcolor='black'))

def tests():
    #import sys
    #tagng = sys.modules[__name__]
    d = testdoc()
    d.body
    d.body.attributes
    d.body.contents
    str(d.body.contents)
    d.body.parent
    d.body.p
    assert(d.body[0] == 'foo')
    assert(d.body[-1][0] == 'bar')
    assert(d.body.p.class_ == 42)
    assert(body in d)
    assert(body in d.contents)          # XXX FAILS
    assert(p not in d)
    assert('foo' in d.body)
    assert('foo' in d.body.contents)
    assert('foo' not in d.body.attributes)
    assert('bgcolor' in d.body)
    assert('bgcolor' in d.body.attributes)
    assert('bgcolor' not in d.body.contents)
    assert(object_().tag == 'object')
    x = map_('foo', id_='baz')
    x.attributes['class'] = """that's "all" folks"""
    x.as_python()
    x.as_html()
    assert(x.as_text() == 'foo')
    assert(object_('foo', bar='baz').as_html() == '')
    assert(object_('foo', bar='baz').as_text() == '')
    d.findall(lambda o: True)
    d.findall(by.bgcolor('black'))
    d.findall(by.and_(by.p, by.has_class))
    d.findall(by.has_br)                 # XXX FAILS
    assert(by.align('right')(div('foo', align='right')))
    assert(by.class_('report')(div('foo', class_='report')))
    d = div('foo', id_='adiv')
    assert(d.id_)
    assert(d.attributes['id'])
    assert('id' in d.attributes)
    assert('id_' not in d.attributes)
    d.attributes['class_'] = 'not a class'
    d.attributes['CLASS'] = 'not a class'
    d.all_has_class
    d.all_by_bgcolor_black
