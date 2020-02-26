import re
from typing import Generator, List

from sqlparse.sql import TokenList
from sqlparse.tokens import Token

TokenType = Token.__class__
QUERY_SYMBOL = "__root__"


class TraverseFailure(Exception):
    """パースツリーの走査に失敗した場合にraiseされるエラー。"""

class HQLTokenWrapper:
    """
    HiveQLの構文ルールを適用するためのトークンラッパの基底クラス。
    あるトークンオブジェクトを対応する構文規則でラップしている。
    """

    def __init__(self, token: TokenType):
        if token is None:
            raise ValueError(token)
        self.token = token

    def traverse(self) -> Generator["HQLTokenWrapper", None, None]:
        """構文ルールを適用して得られるトークンをyieldするメソッド"""
        yield from []

    def nexts(self) -> List["HQLTokenWrapper"]:
        """1回のtraverseの結果得られる全てのトークンのリスト"""
        return list(self.traverse())

    @property
    def text(self) -> str:
        """トークンの文字列"""
        return str(self.token)

    def __str__(self):
        """オブジェクト情報（主にデバッグ用）"""
        clsname = self.__class__.__name__
        statement = re.sub("\n", " ", str(self.token).strip())
        if len(statement) > 10:
            return "<{} \"{}...\">".format(clsname, statement[:10])
        return "<{} \"{}\">".format(clsname, statement)


class ExtraToken(TokenList):
    """
    sqlparse.parseの結果得られるトークンのいくつかをグルーピングしたトークン。
    HiveQLの構文規則をトークン化したもの。
    このオブジェクトをインスタンス化する際に
    sqlparse.sql.Token.group_tokens()メソッドを使うと元の構文結果を変えてしまうため、
    そちらには影響しないようにmisc.group_tokens()関数を使うこと。
    """
