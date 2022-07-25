from __future__ import annotations

import re
import sys
import collections.abc as collections_abc
from abc import ABC, abstractmethod
from typing import Union, Type, Tuple, Generator, TypeVar, Optional, Collection, Iterable, List, overload, \
    Sequence

import sqlparse.sql as s
from sqlparse.tokens import TokenType
from sqlparse.sql import TypeParsed

from sqlparse.utils import listify

# region Typing
T = TypeVar('T')
C = TypeVar('C')
PatternType = Union[str, re.Pattern]

OneOrIterable = Iterable[T] | T
OneOrList = List[T] | T
OneOrTuple = Tuple[T, ...] | T
OneOrCollection = Collection[T] | T


# endregion


# region Parsed Search helper functions
def match_sql_class(parsed: TypeParsed, sql_class: OneOrTuple[Type[s.Token]]) -> bool:
    """
    Test if parsed is one of provided sql classes to match.
    :param parsed: parsed
    :param sql_class: sql class - Token and subclasses in hierarchy.
    :return: True if match found.
    """
    return isinstance(parsed, sql_class)


def match_token_type(parsed: TypeParsed, ttype: OneOrTuple[Type[TokenType]]) -> bool:
    """
    Test parsed token type against Token Types.
    :param parsed: parsed
    :param ttype: token type - provide lower token type in  hierarchy for more strict checks.
    :return: True if match found.
    """
    return parsed.ttype in ttype


def match_string(string: str, pattern: OneOrIterable[PatternType], case_sensitive=False) -> bool:
    """
    Test string against provided patterns. If string matches any pattern returns true. False otherwise.

    :param string: string to test
    :param pattern: pattern or patterns to test string against. Can be a string, re, or regex string.
    :param case_sensitive: Whether string to pattern match have to be case-sensitive
    :return: True if string matches any of provided patterns.
    """
    flags = 0
    flags = re.IGNORECASE if not case_sensitive else flags

    pattern = listify(pattern)

    for p in pattern:
        if isinstance(p, str):
            match = bool(re.fullmatch(p, string, flags))
        elif isinstance(p, re.Pattern):
            match = bool(p.fullmatch(string))
        else:
            raise ValueError(f'Invalid object type in pattern: {p}')
        if match:
            return True
    return False


def match_token_value(parsed: TypeParsed, pattern: OneOrIterable[PatternType], case_sensitive=False) -> bool:
    """
    Match token's value with provided pattern.

    :param parsed: input token
    :param pattern: pattern or patterns to test string against. Can be a string, re, or regex string.
    :param case_sensitive: Whether string to pattern match have to be case-sensitive
    :return: True if token's value matches any of provided patterns.
    """
    return match_string(parsed.value, pattern, case_sensitive)


def match_parsed(parsed: TypeParsed,
                 sql_class: OneOrTuple[Type[s.Token]] | None = None,
                 ttype: OneOrTuple[Type[TokenType]] | None = None,
                 pattern: OneOrIterable[PatternType] | None = None,
                 case_sensitive=False) -> bool:
    """
    Matching parsed against: sql class, token type, and token value. Returns True if any match found.
    Sql class and token type are mutually exclusive - there is no sense providing them both.
    If Sql class or token type is provided without pattern - token value check is not performed.
    If Sql class or token type is provided without pattern
        - value check against pattern is performed when token matches type or class.
    If only pattern is provided - value check against pattern is performed whatever token type or class it is.

    :param parsed: parsed statement (or it's part)
    :param sql_class: sql class - Token and subclasses in hierarchy.
    :param ttype: token type - provide lower token type in hierarchy for more strict checks.
    :param pattern: pattern or patterns to test string against. Can be a string, re, or regex string.
    :param case_sensitive: Whether string to pattern match have to be case-sensitive
    :return: True if token matches description.
    """
    class_type_match = (sql_class and match_sql_class(parsed, sql_class)) or \
                       (ttype and match_token_type(parsed, ttype)) or (sql_class is None and ttype is None)
    pattern_match = (pattern is None or match_token_value(parsed, pattern, case_sensitive))
    return class_type_match and pattern_match


def identity(a):
    return a


def neg(a) -> bool:
    return not a


def search_parsed(parsed: TypeParsed | Iterable[s.Token],
                  sql_class: OneOrTuple[Type[s.Token]] | None = None,
                  ttype: OneOrTuple[Type[TokenType]] | None = None,
                  pattern: OneOrIterable[PatternType] | None = None,
                  case_sensitive=False, levels=sys.maxsize, exclude=False) -> Generator[TypeParsed, None, None]:
    """
    Performs recursive search on provided parsed statement (or list of parsed statements),
    yields token if meets input condition.

    :param parsed: parsed statement (or it's part), or any Iterable of parsed statements
    :param sql_class: sql class - Token and subclasses in hierarchy.
    :param ttype: token type - provide lower token type in hierarchy for more strict checks.
    :param pattern: pattern or patterns to test string against. Can be a string, re, or regex string.
    :param case_sensitive: Whether string to pattern match have to be case-sensitive
    :param levels: how deep recursive search should be. 1 is for no recursion.
    :param exclude: Whether to yield or not if token match condition.
    :return: Generator of tokens matching input conditions.
    """
    bool_func = neg if exclude else identity
    if isinstance(parsed, collections_abc.Iterable) and levels > 0:
        for i in parsed:
            if bool_func(match_parsed(parsed=i, sql_class=sql_class, ttype=ttype,
                                      pattern=pattern, case_sensitive=case_sensitive)):
                yield i
            yield from search_parsed(i, sql_class, ttype, pattern, case_sensitive, levels - 1)


# endregion

# single token tools
def get_token_idx(token: s.Token) -> int | None:
    """
    Returns index of token in parent tokens list.
    """
    try:
        return token.parent.tokens.index(token)
    except ValueError:
        return None


def get_token_neighbours(token: s.Token, left: int | None, right: int | None, include_self: bool = False
                         ) -> List[s.Token]:
    """
    Returns token neighbours from token's parent token list.

    :param token: Input token
    :param left: how many neighbour tokens from token to the beginning should be returned. All if None Provided.
    :param right: how many neighbour tokens from token to the end should be returned. All if None Provided.
    :param include_self: whether to include input token in a list (keeping the order)
    :return: list of neighbour tokens
    """
    left = sys.maxsize if left is None else left
    right = sys.maxsize if right is None else right
    token_idx = get_token_idx(token)
    plist = token.parent.tokens
    tokens = plist[token_idx - left: token_idx] + ([token] if include_self else []) + plist[token_idx+1: right]
    return tokens


def get_preceding_tokens(token: s.Token, how_many: int | None = None, include_self=False) -> List[s.Token]:
    """
    Returns preceding tokens in current token group.
    :param token: Input token
    :param how_many: How many preceding tokens should be returned (all if None provided)
    :param include_self: whether to include input token in result list.
    :return: List of preceding tokens.
    """
    return get_token_neighbours(token=token, left=how_many, right=0, include_self=include_self)


def get_succeeding_tokens(token: s.Token, how_many: int | None = None, include_self=False) -> List[s.Token]:
    """
    Returns succeeding tokens in current token group.
    :param token: Input token
    :param how_many: How many succeeding tokens should be returned (all if None provided)
    :param include_self: whether to include input token in result list
    :return: List of succeeding tokens.
    """
    return get_token_neighbours(token=token, left=0, right=how_many, include_self=include_self)


# Search fluent Interface
class ParsedSearcher(ABC):
    @abstractmethod
    def get(self,
            sql_class: OneOrTuple[Type[s.Token]] | None = None,
            ttype: OneOrTuple[Type[TokenType]] | None = None,
            pattern: OneOrIterable[PatternType] | None = None,
            case_sensitive: bool = False, levels: int = sys.maxsize) -> SearchStep:
        """
        Returns all Tokens matching condition.
        If sql_class and ttype are both provided, then check for either sql_class match or ttype match is done.
        If pattern is provided with sql_class and/or ttype then method checks for (sql_class or ttpye) and pattern.
        :param sql_class: sql class or tuple of sql classes to check, if Tuple provided, check for any match.
        :param ttype: token type or tuple of token types, if Tuple provided, check for any match.
        :param pattern: pattern or tuple of patterns to test token value against, check for any match.
        :param case_sensitive: Whether string pattern checks have to be case-sensitive.
        :param levels: How deep recursive search should be performed.
        :return:
        """
        pass

    @abstractmethod
    def get_all(self, levels: int = sys.maxsize) -> SearchStep:
        """
        Scans recursively through all tokens, depends on maximum level
        :param levels: How deep recursive search should be performed.
        :return:
        """
        pass


class Search(ParsedSearcher):
    def __init__(self, parsed: OneOrIterable[TypeParsed]):
        # Todo consider exclusion plain Token type from parsed argument, as search is done within a group
        #   type(t) is s.Token
        self.parsed = parsed

    def get(self, sql_class: OneOrTuple[Type[s.Token]] | None = None,
            ttype: OneOrTuple[Type[TokenType]] | None = None,
            pattern: OneOrIterable[PatternType] | None = None,
            case_sensitive=False, levels=sys.maxsize) -> SearchStep:
        result_set = search_parsed(parsed=self.parsed, sql_class=sql_class, ttype=ttype, pattern=pattern,
                                   case_sensitive=case_sensitive, levels=levels)
        return SearchStep(result_set)

    def get_all(self, levels=sys.maxsize) -> SearchStep:
        result_set = search_parsed(parsed=self.parsed, levels=levels)
        return SearchStep(result_set)


class SearchStep(ParsedSearcher):
    def __init__(self, parsed: Iterable[TypeParsed]):
        self.parsed = parsed

    def result(self) -> SearchResult:
        return SearchResult(self.parsed)

    def get(self, sql_class: OneOrTuple[Type[s.Token]] | None = None,
            ttype: OneOrTuple[Type[TokenType]] | None = None,
            pattern: OneOrIterable[PatternType] | None = None,
            case_sensitive=False, levels=sys.maxsize) -> SearchStep:
        # Delegate to Search instance
        return Search(self.parsed).get(sql_class=sql_class, ttype=ttype, pattern=pattern,
                                       case_sensitive=case_sensitive, levels=levels)

    def get_all(self, levels=sys.maxsize) -> SearchStep:
        # Delegate to Search instance
        return Search(self.parsed).get_all(levels=levels)

    def exclude(self, sql_class: OneOrTuple[Type[s.Token]] | None = None,
                ttype: OneOrTuple[Type[TokenType]] | None = None,
                pattern: OneOrIterable[PatternType] | None = None,
                case_sensitive=False, levels=sys.maxsize) -> SearchStep:
        result_set = search_parsed(parsed=self.parsed, sql_class=sql_class, ttype=ttype, pattern=pattern,
                                   case_sensitive=case_sensitive, levels=levels, exclude=True)
        return SearchStep(result_set)

    def top(self, n: int) -> SearchStep:
        if not n > 0:
            raise ValueError('n must be > 0')
        return SearchStep(list(self.parsed)[:n])

    def bottom(self, n: int) -> SearchStep:
        if not n > 0:
            raise ValueError('n must be > 0')
        return SearchStep(list(reversed(list(self.parsed)))[:n])

    def first(self) -> SearchStep:
        return self.top(1)

    def last(self) -> SearchStep:
        return self.bottom(1)

    def search_token(self) -> SearchToken:
        """
        if one value then go search in token, if many then excpetion
        :return:
        """
        try:
            result = self.result().one()
        except SearchResultException:
            raise InvalidSearchable('Cannot perform search token on a search result which is not a single token.')
        return SearchToken(result)


class SearchResultException(Exception):
    pass


class SearchTokenException(Exception):
    pass


class InvalidSearchable(Exception):
    pass


class SearchResult(collections_abc.Sequence):

    def __init__(self, parsed: Iterable[TypeParsed]):
        self.parsed = parsed
        self.values = list(self.__values())

    def __values(self) -> Generator[TypeParsed, None, None]:
        if not isinstance(self.parsed, s.Token):
            return (i for i in self.parsed)
        else:
            raise ValueError('Error')

    def as_list(self) -> List[TypeParsed]:
        return self.values

    def one(self) -> TypeParsed:
        if len(self.values) != 1:
            raise SearchResultException(f'Expected single value, got {len(self.values)}')
        return self.values[0]

    def __iter__(self) -> Iterable[TypeParsed]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, n) -> Sequence[TypeParsed]:
        return self.values[n]


class SearchToken:
    def __init__(self, token: s.Token):
        if not isinstance(token, s.Token):
            raise InvalidSearchable('Searchable must be an instance of a Token.')
        self.token = token

    def get_preceding(self, how_many: int | None = None, include_self=False) -> SearchStep:
        tokens = get_preceding_tokens(self.token, how_many, include_self)
        return SearchStep(tokens)

    def get_succeeding(self, how_many: int | None = None, include_self=False) -> SearchStep:
        tokens = get_succeeding_tokens(token=self.token, how_many=how_many, include_self=include_self)
        return SearchStep(tokens)

    def get_neighbours(self, left: int | None = None, right: int | None = None,
                       include_self: bool = False) -> SearchStep:
        tokens = get_token_neighbours(token=self.token, left=left, right=right, include_self=include_self)
        return SearchStep(tokens)

    def get_all_neighbours(self, include_self=False) -> SearchStep:
        tokens = get_token_neighbours(token=self.token, left=None, right=None, include_self=include_self)
        return SearchStep(tokens)


class CommonPatterns:
    whitespaces = re.compile('\s')
