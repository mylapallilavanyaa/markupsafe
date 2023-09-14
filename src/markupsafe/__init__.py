from __future__ import annotations

import collections.abc as cabc
import re
import string
import sys
import typing as t

if t.TYPE_CHECKING:
    import typing_extensions as te

    class HasHTML(te.Protocol):
        def __html__(self) -> str:
            pass

    _P = te.ParamSpec("_P")


__version__ = "2.2.0.dev"

_strip_comments_re = re.compile(r"<!--.*?-->", re.DOTALL)
_strip_tags_re = re.compile(r"<.*?>", re.DOTALL)


class Markup(str):
    """A string that is ready to be safely inserted into an HTML or XML
    document, either because it was escaped or because it was marked
    safe.

    Passing an object to the constructor converts it to text and wraps
    it to mark it safe without escaping. To escape the text, use the
    :meth:`escape` class method instead.

    >>> Markup("Hello, <em>World</em>!")
    Markup('Hello, <em>World</em>!')
    >>> Markup(42)
    Markup('42')
    >>> Markup.escape("Hello, <em>World</em>!")
    Markup('Hello &lt;em&gt;World&lt;/em&gt;!')

    This implements the ``__html__()`` interface that some frameworks
    use. Passing an object that implements ``__html__()`` will wrap the
    output of that method, marking it safe.

    >>> class Foo:
    ...     def __html__(self):
    ...         return '<a href="/foo">foo</a>'
    ...
    >>> Markup(Foo())
    Markup('<a href="/foo">foo</a>')

    This is a subclass of :class:`str`. It has the same methods, but
    escapes their arguments and returns a ``Markup`` instance.

    >>> Markup("<em>%s</em>") % ("foo & bar",)
    Markup('<em>foo &amp; bar</em>')
    >>> Markup("<em>Hello</em> ") + "<foo>"
    Markup('<em>Hello</em> &lt;foo&gt;')
    """

    __slots__ = ()

    def __new__(
        cls, base: t.Any = "", encoding: str | None = None, errors: str = "strict"
    ) -> te.Self:
        if hasattr(base, "__html__"):
            base = base.__html__()

        if encoding is None:
            return super().__new__(cls, base)

        return super().__new__(cls, base, encoding, errors)

    def __html__(self) -> te.Self:
        return self

    def __add__(self, other: str | HasHTML) -> te.Self:
        if isinstance(other, str) or hasattr(other, "__html__"):
            return self.__class__(super().__add__(self.escape(other)))

        return NotImplemented

    def __radd__(self, other: str | HasHTML) -> te.Self:
        if isinstance(other, str) or hasattr(other, "__html__"):
            return self.escape(other).__add__(self)

        return NotImplemented

    def __mul__(self, num: t.SupportsIndex) -> te.Self:
        if isinstance(num, int):
            return self.__class__(super().__mul__(num))

        return NotImplemented

    __rmul__ = __mul__

    def __mod__(self, arg: t.Any) -> te.Self:
        if isinstance(arg, tuple):
            # a tuple of arguments, each wrapped
            arg = tuple(_MarkupEscapeHelper(x, self.escape) for x in arg)
        elif hasattr(type(arg), "__getitem__") and not isinstance(arg, str):
            # a mapping of arguments, wrapped
            arg = _MarkupEscapeHelper(arg, self.escape)
        else:
            # a single argument, wrapped with the helper and a tuple
            arg = (_MarkupEscapeHelper(arg, self.escape),)

        return self.__class__(super().__mod__(arg))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def join(self, seq: cabc.Iterable[str | HasHTML]) -> te.Self:
        return self.__class__(super().join(map(self.escape, seq)))

    join.__doc__ = str.join.__doc__

    def split(  # type: ignore[override]
        self, sep: str | None = None, maxsplit: int = -1
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().split(sep, maxsplit)]

    split.__doc__ = str.split.__doc__

    def rsplit(  # type: ignore[override]
        self, sep: str | None = None, maxsplit: int = -1
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().rsplit(sep, maxsplit)]

    rsplit.__doc__ = str.rsplit.__doc__

    def splitlines(  # type: ignore[override]
        self, keepends: bool = False
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().splitlines(keepends)]

    splitlines.__doc__ = str.splitlines.__doc__

    def unescape(self) -> str:
        """Convert escaped markup back into a text string. This replaces
        HTML entities with the characters they represent.

        >>> Markup("Main &raquo; <em>About</em>").unescape()
        'Main » <em>About</em>'
        """
        from html import unescape

        return unescape(str(self))

    def striptags(self) -> str:
        """:meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup("Main &raquo;\t<em>About</em>").striptags()
        'Main » About'
        """
        # Use two regexes to avoid ambiguous matches.
        value = _strip_comments_re.sub("", self)
        value = _strip_tags_re.sub("", value)
        value = " ".join(value.split())
        return self.__class__(value).unescape()

    @classmethod
    def escape(cls, s: t.Any) -> te.Self:
        """Escape a string. Calls :func:`escape` and ensures that for
        subclasses the correct type is returned.
        """
        rv = escape(s)

        if rv.__class__ is not cls:
            return cls(rv)

        return rv  # type: ignore[return-value]

    def __getitem__(self, key: t.SupportsIndex | slice, /) -> te.Self:
        return self.__class__(super().__getitem__(key))

    def capitalize(self, /) -> te.Self:
        return self.__class__(super().capitalize())

    def title(self, /) -> te.Self:
        return self.__class__(super().title())

    def lower(self, /) -> te.Self:
        return self.__class__(super().lower())

    def upper(self, /) -> te.Self:
        return self.__class__(super().upper())

    def replace(self, old: str, new: str, count: t.SupportsIndex = -1, /) -> te.Self:
        return self.__class__(
            super().replace(self.escape(old), self.escape(new), count)
        )

    def ljust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().ljust(width, self.escape(fillchar)))

    def rjust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().rjust(width, self.escape(fillchar)))

    def lstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().lstrip(self.escape(chars)))

    def rstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().rstrip(self.escape(chars)))

    def center(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().center(width, self.escape(fillchar)))

    def strip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().strip(self.escape(chars)))

    def translate(
        self,
        table: cabc.Mapping[int, str | int | None],  # type: ignore[override]
        /,
    ) -> str:
        return self.__class__(super().translate(table))

    def expandtabs(self, /, tabsize: t.SupportsIndex = 8) -> te.Self:
        return self.__class__(super().expandtabs(tabsize))

    def swapcase(self, /) -> te.Self:
        return self.__class__(super().swapcase())

    def zfill(self, width: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().zfill(width))

    def casefold(self, /) -> te.Self:
        return self.__class__(super().casefold())

    if sys.version_info >= (3, 9):

        def removeprefix(self, prefix: str, /) -> te.Self:
            return self.__class__(super().removeprefix(self.escape(prefix)))

        def removesuffix(self, suffix: str) -> te.Self:
            return self.__class__(super().removesuffix(self.escape(suffix)))

    def partition(self, sep: str, /) -> tuple[te.Self, te.Self, te.Self]:
        l, s, r = super().partition(self.escape(sep))
        cls = self.__class__
        return cls(l), cls(s), cls(r)

    def rpartition(self, sep: str) -> tuple[te.Self, te.Self, te.Self]:
        l, s, r = super().rpartition(self.escape(sep))
        cls = self.__class__
        return cls(l), cls(s), cls(r)

    def format(self, *args: t.Any, **kwargs: t.Any) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, args, kwargs))

    def format_map(  # type: ignore[override]
        self, map: cabc.Mapping[str, t.Any]
    ) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, (), map))

    def __html_format__(self, format_spec: str) -> te.Self:
        if format_spec:
            raise ValueError("Unsupported format specification for Markup.")

        return self


class EscapeFormatter(string.Formatter):
    __slots__ = ("escape",)

    def __init__(self, escape: t.Callable[[t.Any], Markup]) -> None:
        self.escape = escape
        super().__init__()

    def format_field(self, value: t.Any, format_spec: str) -> str:
        if hasattr(value, "__html_format__"):
            rv = value.__html_format__(format_spec)
        elif hasattr(value, "__html__"):
            if format_spec:
                raise ValueError(
                    f"Format specifier {format_spec} given, but {type(value)} does not"
                    " define __html_format__. A class that defines __html__ must define"
                    " __html_format__ to work with format specifiers."
                )
            rv = value.__html__()
        else:
            # We need to make sure the format spec is str here as
            # otherwise the wrong callback methods are invoked.
            rv = string.Formatter.format_field(self, value, str(format_spec))
        return str(self.escape(rv))


class _MarkupEscapeHelper:
    """Helper for :meth:`Markup.__mod__`."""

    __slots__ = ("obj", "escape")

    def __init__(self, obj: t.Any, escape: t.Callable[[t.Any], Markup]) -> None:
        self.obj = obj
        self.escape = escape

    def __getitem__(self, item: t.Any) -> te.Self:
        return self.__class__(self.obj[item], self.escape)

    def __str__(self) -> str:
        return str(self.escape(self.obj))

    def __repr__(self) -> str:
        return str(self.escape(repr(self.obj)))

    def __int__(self) -> int:
        return int(self.obj)

    def __float__(self) -> float:
        return float(self.obj)


# circular import
try:
    from ._speedups import escape as escape
    from ._speedups import escape_silent as escape_silent
    from ._speedups import soft_str as soft_str
except ImportError:
    from ._native import escape as escape
    from ._native import escape_silent as escape_silent  # noqa: F401
    from ._native import soft_str as soft_str  # noqa: F401
