from abc import ABC, abstractmethod

from typing import Sequence, Type, Optional, Generator

from sqlparse.engine import StatementSplitter, FilterStack
from sqlparse.engine.grouping import Grouper, GenericGrouper
from sqlparse.keywords import TokenRule, SQL_REGEX
from sqlparse.lexer import Lexer
from sqlparse.sql import Statement


class SqlParser(ABC):
    @abstractmethod
    def parse(self, sql: str, encoding: Optional[str] = None) -> Generator[Statement, None, None]:
        pass


# lexer -> token_rules
# filter_stack -> statement_splitter, lexer, grouper
# class ParametrizedSqlParser(SqlParser):
#     def __init__(self, token_rules: Sequence[TokenRule], grouper: Grouper, statement_splitter: StatementSplitter,
#                  lexer_cls: Optional[Type[Lexer]] = None, filter_stack_cls: Optional[Type[FilterStack]] = None):
#         self.token_rules = token_rules
#         self.grouper = grouper
#         self.statement_splitter = statement_splitter
#         self.lexer_cls = lexer_cls or Lexer
#         self.filter_stack_cls = filter_stack_cls or FilterStack
#
#         self.lexer = lexer_cls(token_rules)
#         self.filter_stack = filter_stack_cls(self.statement_splitter, self.lexer, self.grouper)
#
#     def parse(self, sql: str, encoding=None):
#         return self.filter_stack.run(sql, encoding)
#
#
# class FilterStackSqlParser(SqlParser):
#     def __init__(self, filter_stack: FilterStack):
#         self.filter_stack = filter_stack
#
#     def parse(self, sql: str, encoding=None):
#         return self.filter_stack.run(sql, encoding)
#
#
# generic_sql_parser = FilterStackSqlParser(
#     filter_stack=FilterStack(
#         statement_splitter=StatementSplitter(),
#         lexer=Lexer(SQL_REGEX),
#         grouper=Grouper()
#     )
# )


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


parsers = {}


def get_parser(dialect: str):
    return parsers.get(dialect, GenericSqlParser())
