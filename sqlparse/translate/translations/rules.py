from sqlparse.utils import imt, recurse
from sqlparse.sql import TypeParsed
from sqlparse import sql as s
from sqlparse import tokens as t
from sqlparse import helpers as helpers
from sqlparse.helpers import Search, SearchToken, CommonPatterns, match_string


def get_function_name(parsed: s.Function) -> str:
    # Todo check for Function type
    name = Search(parsed).get(sql_class=s.Identifier, levels=1).first().result().one().value
    return name


def spark_cast_to_redshift(parsed: TypeParsed) -> None:
    if isinstance(parsed, s.Function) and match_string(get_function_name(parsed), 'cast'):
        # 1. Wez zawartosc nawiasow
        # 2. Pierwszy token po AS ktory nie jest bialym znakiem



        # Todo delegate Search() constructor to SearchToken if single instance of token provided?
        #   - No how would it know wheter you want to search the token or its group?

        # TODO consider, to store translations as a simple list of tokens? let the parser do the job later wih grouping
        #   - even on the lexer level - just return string? it's lexer job to decide what is keytword etc token type
        # TODO: also add to translation relation to parser (source for sure, what about target?)

        as_token = Search(parsed) \
            .get(sql_class=s.Parenthesis).first() \
            .get(pattern='as', case_sensitive=False).last().result().one()

        casted_token = SearchToken(as_token)\
            .get_preceding() \
            .exclude(pattern=CommonPatterns.whitespaces) \
            .first().result().one()
        cast_type_token = SearchToken(as_token)\
            .get_succeeding() \
            .exclude(pattern=CommonPatterns.whitespaces) \
            .first().result().one()

        new_syntax = f'{str(cast_type_token)}({str(casted_token)})'
        new_token = s.Token(None, new_syntax)
        # TODO find parsed function in parent, replace tokens (remove)



