from typing import Tuple, Generator

from sqlparse.sql import Parenthesis, IdentifierList, Where, Identifier
from sqlparse.tokens import Keyword, Token, DML, Name

from .base import HQLTokenWrapper, ExtraToken, TraverseFailure
from .misc import get_token_next, group_tokens

TokenType = Token.__class__
QUERY_IDENTIFIER = "__root__"


class Query(HQLTokenWrapper):
    """クエリと対応するトークンのラッパ"""

    def yield_edges(self) -> Generator[Tuple, None, None]:
        """エッジを生成する"""
        token_stack = self.nexts()
        ident_stack = [(self.get_identifier(), 0)]
        while len(token_stack):
            token = token_stack.pop()
            if len(token_stack) < ident_stack[-1][1]:
                ident_stack.pop()
            if isinstance(token, (TblName, Query)):
                yield ident_stack[-1][0], token.get_identifier()
            if isinstance(token, Query):
                ident_stack.append((token.get_identifier(), len(token_stack)))
            token_stack.extend(token.nexts())

    def get_identifier(self) -> str:
        """クエリ全体に対する識別子として便宜的にQUERY_IDENTIFIERを割り当てる"""
        return QUERY_IDENTIFIER

    def traverse(self):
        """全てのSELECTトークンを抜き出す"""
        for t in self.token:
            if t.match(DML, "SELECT"):
                yield Select(t)


class Subquery(Query):
    """サブクエリと対応するトークンのラッパ"""
    UNSET_IDENT_SYMBOL = "__UNSET__"

    def __init__(self, token, ident=UNSET_IDENT_SYMBOL):
        super().__init__(token)
        self.ident = ident

    def get_identifier(self):
        """
        Subquery.identが設定されていれば、それを返す。
        無ければサブクエリのaliasを、それもなければオブジェクトIDを返す。
        なお、Subquery.ident = Noneの場合は無名のサブクエリであることを表すため、
        Subquery.UNSET_IDENT_SYMBOLはデフォルト値（＝Subquery.identが未設定）
        であることを表す。
        """
        empty_filler = id(self.token)
        if self.ident != self.UNSET_IDENT_SYMBOL:
            return self.ident or empty_filler
        ident = getattr(
            self.token.parent,
            "get_alias",
            lambda: None
        )() or empty_filler
        return ident


class TblName(HQLTokenWrapper):
    """tbl_nameトークン"""

    def get_identifier(self):
        """テーブル名を取得"""
        if self.token.ttype == Name:
            return self.token.parent.get_real_name()
        if self.token.__class__ == Identifier:
            return self.token.get_real_name()


class Select(HQLTokenWrapper):
    FROM_END_KEYWORD = [
        "GROUP",
        "ORDER",
        "CLUSTER",
        "DISTRIBUTE",
        "SORT",
        "LIMIT",
        "^UNION"
    ]

    @classmethod
    def is_from_end_keyword(cls, token):
        if isinstance(token, Where):
            return True
        return any(token.match(Keyword, kw, regex=True) for kw in
                   cls.FROM_END_KEYWORD)

    def traverse(self):
        """
        以下のルールに従い、table_referenceとwhere_conditionを抜き出す。
        [WITH CommonTableExpression (, CommonTableExpression)*]
        SELECT [ALL | DISTINCT] select_expr, select_expr, ...
          FROM table_reference
          [WHERE where_condition]
          [GROUP BY col_list]
          [ORDER BY col_list]
          [CLUSTER BY col_list
            | [DISTRIBUTE BY col_list] [SORT BY col_list]
          ]
         [LIMIT [offset,] rows]
        """
        token = self.token
        # UNION以降は別のSELECT節に当たるので探索範囲から外す。
        while token and not token.match(Keyword, "^UNION", regex=True):
            if token.match(Keyword, "FROM"):
                token_first_id = self.token.parent.token_index(token) + 1
                token = get_token_next(self.token.parent, token)
                # Select.FROM_END_KEYWORDでFROM節の終わりを判定する
                token = self.token.parent.token_matching(
                    self.is_from_end_keyword,
                    self.token.parent.token_index(token)
                )
                if token is None:
                    token_last = self.token.parent.tokens[-1]
                    yield TableReference.from_grouping(
                        self.token.parent,
                        token_first_id,
                        self.token.parent.token_index(token_last)
                    )
                    return
                else:
                    yield TableReference.from_grouping(
                        self.token.parent,
                        token_first_id,
                        self.token.parent.token_index(token) - 1
                    )
                    continue
            if isinstance(token, Where):
                yield WhereCondition(token)
                return
            token = get_token_next(self.token.parent, token)


class TableReference(HQLTokenWrapper):
    class TableReferenceToken(ExtraToken):
        """TableReference用のExtraToken"""

    @classmethod
    def from_grouping(cls, token, start_idx, end_idx):
        """あるトークンの一部をgroupingしたものをtokenとして初期化するためのメソッド"""
        t = group_tokens(token, cls.TableReferenceToken, start_idx, end_idx)
        return cls(t)

    def is_join_table(self):
        """self.tokenがjoin_tableかどうかを判定するためのメソッド"""
        for token in self.token:
            if JoinTable.is_join_keyword(token):
                return True
        return False

    def traverse(self):
        """
        以下のルールに従って、table_factorもしくはjoin_tableを抜き出し。
        table_reference:
            table_factor
          | join_table
        """
        if self.is_join_table():
            yield JoinTable(self.token)
        else:
            yield TableFactor(self.token)


class WhereCondition(HQLTokenWrapper):
    def traverse(self):
        """
        FROM where_conditionルールのwhere_conditionが
        サブクエリならそれをyieldする。
        """
        for t in self.token:
            if isinstance(t, Parenthesis):
                subquery = Subquery(t)
                subquery.ident = self.get_subquery_alias()
                if len(subquery.nexts()):
                    yield subquery
                return

    def get_subquery_alias(self):
        """
        HiveQL対応版のget_aliasメソッド
        オリジナルはWHERE句の中のサブクエリに未対応だったため、その部分を追記したもの。
        """
        from sqlparse.tokens import Whitespace
        # "name AS alias"
        kw_idx, kw = self.token.token_next_by(m=(Keyword, 'AS'))
        if kw is not None:
            return self.token._get_first_name(kw_idx + 1, keywords=True)
        # "name alias" or "complicated column expression alias"
        _, ws = self.token.token_next_by(t=Whitespace)
        if len(self.token.tokens) > 2 and ws is not None:
            kw_in_idx, _ = self.token.token_next_by(m=(Keyword, "IN"))
            return self.token._get_first_name(idx=kw_in_idx, reverse=True)


class TableReferences(HQLTokenWrapper):
    def traverse(self):
        """
        table_referencesからtable_referenceを抜き出す。
        """
        for t in self.token.get_identifiers():
            yield TableReference(t)


class JoinTable(HQLTokenWrapper):
    JOIN_KEYWORD = [
        "JOIN",
        "INNER JOIN",
        "RIGHT JOIN",
        "FULL JOIN",
        "LEFT JOIN",
        "LEFT SEMI JOIN",
        "RIGHT OUTER JOIN",
        "FULL OUTER JOIN",
        "LEFT OUTER JOIN",
        "CROSS JOIN",
    ]

    @classmethod
    def is_join_keyword(cls, token):
        """あるトークンがjoin_keywordに当たるかチェック"""
        return any(token.match(Keyword, kw) for kw in cls.JOIN_KEYWORD)

    def traverse(self):
        """
        以下の構文規則に従ってtable_referenceとtable_factorを抜き出す。
        join_table:
            table_reference [INNER] JOIN table_factor [join_condition]
          | table_reference {LEFT|RIGHT|FULL} [OUTER] JOIN table_reference join_condition
          | table_reference LEFT SEMI JOIN table_reference join_condition
          | table_reference CROSS JOIN table_reference [join_condition]
        """
        # table_reference
        token = self.token.token_first(skip_cm=True, skip_ws=True)
        token_first_idx = self.token.token_index(token)
        token_join = self.token.token_matching(
            self.is_join_keyword,
            token_first_idx
        )
        if token_join is None:
            raise TraverseFailure()
        # JOIN keyword
        yield TableReference.from_grouping(
            self.token,
            token_first_idx,
            self.token.token_index(token_join) - 1
        )
        token_on = self.token.token_matching(
            lambda x: x.match(Keyword, "ON"),
            self.token.token_index(token_join)
        )
        # table_reference or table_factor
        if token_join.match(Keyword, "(JOIN|INNER JOIN)", regex=True):
            group_cls = TableFactor
        else:
            group_cls = TableReference
        yield group_cls.from_grouping(
            self.token,
            self.token.token_index(token_join) + 1,
            self.token.token_index(token_on) - 1
        )
        # join_conditionについてはテーブル名抽出に無関係なので省略


class TableFactor(HQLTokenWrapper):
    class TableFactorToken(ExtraToken):
        """TableFactor用のExtraToken"""

    @classmethod
    def from_grouping(cls, token, start_idx, end_idx):
        """あるトークンの一部をgroupingしたものをtokenとして初期化するためのメソッド"""
        t = group_tokens(token, cls.TableFactorToken, start_idx, end_idx)
        return cls(t)

    def traverse(self):
        """
        以下の規則に従って分岐する。
        table_factor:
            tbl_name [alias]
          | table_subquery alias
          | ( table_references )
        """
        token_first = self.token.token_first(skip_ws=True, skip_cm=True)
        # tbl_name [alias] 1/2 (最初のトークンがNameの場合)
        if token_first.ttype == Name:
            yield TblName(token_first)
            return
        # ( table_references )
        # HQL特有文法であるためか二重括弧と認識されてしまうので、それを逆手に取って同定
        if isinstance(token_first, Parenthesis):
            for t in self.token:
                if isinstance(t, Parenthesis):
                    for sub_t in t:
                        if isinstance(sub_t, IdentifierList):
                            yield TableReferences(sub_t)
                            return
        # table_subquery alias
        token_subq = token_first.token_first(skip_cm=True, skip_ws=True)
        if isinstance(token_subq, Parenthesis):
            yield Subquery(token_subq)
            return
        # tbl_name [alias] 2/2 (Identifierトークンがサブクエリでない場合)
        if token_first.__class__ == Identifier:
            yield TblName(token_first)
            return
        raise TraverseFailure("Invalid Tablefactor " + str(self))
