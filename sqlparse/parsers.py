from abc import ABC, abstractmethod, ABCMeta

from typing import Optional, Generator

from sqlparse.engine import StatementSplitter, FilterStack
from sqlparse.engine.grouping import GenericGrouper, Grouper
from sqlparse.keywords import SQL_REGEX
from sqlparse.lexer import Lexer
from sqlparse.sql import Statement


class SqlParser(ABC):

    @abstractmethod
    def parse(self, sql: str, encoding: Optional[str] = None) -> Generator[Statement, None, None]:
        pass

    @abstractmethod
    def get_lexer(self):
        pass

    @abstractmethod
    def get_statement_splitter(self):
        pass

    @abstractmethod
    def get_grouper(self):
        pass


class GenericSqlParser(SqlParser):
    def __init__(self):
        self.stack = FilterStack(
            statement_splitter=StatementSplitter(),
            lexer=Lexer(SQL_REGEX),
            grouper=GenericGrouper()
        )
        self.stack.enable_grouping()

    def parse(self, sql: str, encoding: Optional[str] = None) -> Generator[Statement, None, None]:
        return self.stack.run(sql, encoding)

    def get_lexer(self) -> Lexer:
        return self.stack.lexer

    def get_statement_splitter(self) -> StatementSplitter:
        return self.stack.statement_splitter

    def get_grouper(self) -> Grouper:
        return self.stack.grouper


parsers = {}


def get_parser(dialect: str):
    return parsers.get(dialect, GenericSqlParser())
