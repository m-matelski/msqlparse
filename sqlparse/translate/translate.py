from abc import ABC, abstractmethod
from collections import UserDict
from copy import deepcopy
from typing import List, Tuple, Any, Collection, Union, Optional, Mapping, Protocol

import sqlparse.sql

# SQLs to consider
# MySQL, Oracle, PostgreSQL, MicrosoftSQL, MongoDB
# Redis, Elasticsearch, Teradata, SparkSQL, Redshift

# In future adding dialect recognition??
from sqlparse.parsers import get_parser
from sqlparse.translate.exceptions import TranslationNotFoundException
from sqlparse.utils import chain_func
from sqlparse.sql import TypeParsed


class TranslationCommand(Protocol):
    """
    Interface for translation command. Translation modifies statement in place.
    """

    def __call__(self, parsed: TypeParsed) -> None:
        ...


class TranslationRunner:
    """
    Runs sequence of commands over input statement traversed recursively.
    """

    def __init__(self, translation_rules: List[TranslationCommand]):
        self.translation_rules = translation_rules

    def _recursive_run(self, parsed: TypeParsed):
        if parsed.is_group:
            for i in parsed:
                self._recursive_run(i)

        for rule in self.translation_rules:
            rule(parsed)

    def run(self, stmt: sqlparse.sql.Statement) -> sqlparse.sql.Statement:
        """
        Runs sequence of commands over input statement traversed recursively.
        Returns translated statement.
        """
        stmt_copy = deepcopy(stmt)
        self._recursive_run(stmt_copy)
        return stmt_copy


class TranslationBase(ABC):
    """
    Stores translation objects and translation
    """

    def __init__(self, src_dialect: str, tgt_dialect: str, ):
        self.src_dialect = src_dialect
        self.tgt_dialect = tgt_dialect

    @abstractmethod
    def translate(self, stmt: sqlparse.sql.Statement) -> sqlparse.sql.Statement:
        pass


class Translation(TranslationBase):
    def __init__(self, src_dialect: str, tgt_dialect: str, translation_rules: List[TranslationCommand], register=True):
        super().__init__(src_dialect, tgt_dialect)
        self.translation_rules = translation_rules
        self.translation_runner = TranslationRunner(self.translation_rules)
        if register:
            register_translation(self)

    def translate(self, stmt: sqlparse.sql.Statement) -> sqlparse.sql.Statement:
        return self.translation_runner.run(stmt)


class CompositeTranslation(TranslationBase):
    def __init__(self, src_dialect: str, tgt_dialect: str, translations: List[Translation]):
        super().__init__(src_dialect, tgt_dialect)
        self.translations = translations

    def translate(self, stmt: sqlparse.sql.Statement) -> sqlparse.sql.Statement:
        return chain_func(stmt, (trans.translate for trans in self.translations))


class TranslationMapping(UserDict):
    def register_translation(self, src: str, tgt: str, translation: Translation, overwrite=False):
        trans = self.setdefault(src, {})
        if tgt in trans and overwrite:
            raise ValueError(f"Translation from {src} to {tgt} already exists. "
                             f"Use overwrite=True if You want to overwrite a translation")
        else:
            trans[tgt] = translation

    def get_translation(self, src: str, tgt: str) -> Translation:
        return self[src][tgt]


translations_meta = TranslationMapping()


def register_translation(translation: Translation, overwrite=False, trans_meta=translations_meta):
    trans_meta.register_translation(translation.src_dialect, translation.tgt_dialect, translation, overwrite)


def _find_edges(pairs: Mapping[Any, Collection[Any]], src, tgt, keys=None):
    keys = keys or [src]
    if src == tgt:
        return keys
    if src in pairs:
        new_keys = [k for neighbour in pairs[src]
                    if (k := _find_edges(pairs, neighbour, tgt, keys + [neighbour])) is not None]
        best = min(new_keys, key=lambda x: len(x)) if new_keys else None
        return best
    else:
        return None


def find_route(pairs: Mapping[Any, Collection[Any]], src, tgt) -> Optional[List[Tuple[Any, Any]]]:
    points = _find_edges(pairs, src, tgt)
    result = list(zip(points, points[1:])) if points else None
    return result


def find_translation(src_dialect: str, tgt_dialect: str, trans_meta: TranslationMapping) -> Optional[TranslationBase]:
    route = find_route(trans_meta, src_dialect, tgt_dialect)
    if not route:
        return None
    if len(route) == 1:
        src, tgt = route[0]
        return trans_meta.get_translation(src, tgt)
    elif len(route) > 1:
        # build composite translation on a fly
        translations = [trans_meta.get_translation(src, tgt) for src, tgt in route]
        translation = CompositeTranslation(src_dialect, tgt_dialect, translations)
        return translation


def translate(sql: str, src_dialect: str, tgt_dialect: str, encoding=None,
              trans_meta=translations_meta, as_parsed=False, ensure_list=False
              ) -> Union[TypeParsed, str, List[TypeParsed], List[str]]:
    parser = get_parser('src_dialect')
    parsed = list(parser.parse(sql, encoding))
    translation = find_translation(src_dialect, tgt_dialect, trans_meta)

    if not translation:
        raise TranslationNotFoundException(f"Couldn't find {src_dialect} to {tgt_dialect} translation.")

    translated = [translation.translate(stmt) for stmt in parsed]
    result = translated
    if not as_parsed:
        result = [str(i) for i in result]
    if not ensure_list and len(result) == 1:
        result = result[0]
    return result

# TODO register translation decorator??, is there a need to create new class instead of parametrized instance?
