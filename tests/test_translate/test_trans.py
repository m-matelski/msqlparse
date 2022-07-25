from copy import deepcopy

import sqlparse
from sqlparse.translate.translate import find_route
from sqlparse.translate.translate import translate


def test_dummy_parse():
    sql = "SELECT * from tab1 where 1 > 2"
    parsed = sqlparse.parse(sql)[0]
    x = 1


def test_dummy_parse2():
    sql = "SELECT t.a, t.b, case when t.d > 1 then 'bigger' else 'lower' END from tab1 where (1>2) and t.c is not null"
    parsed = sqlparse.parse(sql)[0]
    x = 1


def test_find_route1():
    assert find_route({0: [1], 1: [2], 2: [3]}, 0, 1) == [(0, 1)]
    assert find_route({0: [1], 1: [2], 2: [3]}, 0, 2) == [(0, 1), (1, 2)]
    assert find_route({0: [1], 1: [2, 3], 2: [3], 3: [4, 5], 4: [5]}, 0, 5) == [(0, 1), (1, 3), (3, 5)]
    assert find_route({0: [1, 2], 1: [2], 2: [3], 3: [0, 1, 2]}, 0, 3) == [(0, 2), (2, 3)]
    assert find_route({0: [1], 1: [2], 2: [3]}, 0, 4) is None
    assert find_route({0: [1], 2: [3]}, 0, 3) is None


def test_copy():
    sql = "SELECT * FROM tab WHERE 1 < 2"
    parsed = sqlparse.parse(sql)[0]
    c = deepcopy(parsed)
    x = 1


def test_spark_to_redshift_cast():
    sql = "select cast(substring(tab.field, 1, 4) as int) from tab"
    parsed_src = sqlparse.parse(sql)
    parsed_tgt = translate(sql, 'spark', 'redshift', as_parsed=True)
    x = 1
