import sqlparse
from sqlparse.helpers import Search, CommonPatterns
import sqlparse.sql as s
import sqlparse.tokens as t


def test_search1():
    sql = "SELECT substring(a, 1, 4), f2 FROM tab1"
    parsed = sqlparse.parse(sql)[0]
    res = Search(parsed).get(ttype=t.Keyword).result().as_list()
    x = 1


def test_search_2():
    sql = "select cast(substring(tab.field, 1, 4) as int) from tab"
    parsed = sqlparse.parse(sql)[0]
    res1 = Search(parsed).get(sql_class=s.Function).result().as_list()
    res2 = Search(parsed) \
        .get(sql_class=s.Function, levels=1) \
        .get(sql_class=s.Parenthesis).first() \
        .get(pattern='as', case_sensitive=False).last() \
        .result().one()

    # search_token
    # token next from token perspective (consider matching exlusion etc)
    # 1. locate token in parent - get token idx in parent
    # 2. Get all tokens from token to the start/end (include token? recursive search?)

    res3 = Search(parsed) \
        .get(sql_class=s.Function, levels=1) \
        .get(sql_class=s.Parenthesis).first() \
        .get(pattern='as', case_sensitive=False).last() \
        .search_token() \
        .get_succeeding() \
        .exclude(pattern=CommonPatterns.whitespaces) \
        .first().result().one()
    x =1





