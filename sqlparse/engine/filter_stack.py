#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""filter"""
from typing import Generator, Optional

import sqlparse.sql
from sqlparse.engine.grouping import Grouper
from sqlparse.lexer import Lexer
from sqlparse.engine import grouping
from sqlparse.engine.statement_splitter import StatementSplitter


class FilterStack:
    def __init__(self, statement_splitter: StatementSplitter, lexer: Lexer, grouper: Grouper):
        self.statement_splitter = statement_splitter
        self.lexer = lexer
        self.grouper = grouper

        self.preprocess = []
        self.stmtprocess = []
        self.postprocess = []
        self._grouping = False

    def enable_grouping(self):
        self._grouping = True

    def run(self, sql: str, encoding: Optional[str] = None) -> Generator[sqlparse.sql.Statement, None, None]:
        stream = self.lexer.get_tokens(sql, encoding)
        # Process token stream
        for filter_ in self.preprocess:
            stream = filter_.process(stream)

        stream = self.statement_splitter.process(stream)

        # Output: Stream processed Statements
        for stmt in stream:
            if self._grouping:
                stmt = grouping.group(stmt)

            for filter_ in self.stmtprocess:
                filter_.process(stmt)

            for filter_ in self.postprocess:
                stmt = filter_.process(stmt)

            yield stmt
