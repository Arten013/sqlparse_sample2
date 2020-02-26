from sqlparse.sql import Statement

from .base import ExtraToken, TokenType


class TraverseFailure(Exception):
    """走査失敗を判定するための例外"""


def get_token_next(statement: Statement, t: TokenType) -> TokenType:
    """`statement`中のあるトークン`t`の次のトークンを取得。コメントと空白はスキップ。"""
    if isinstance(t, ExtraToken):
        t = t.tokens[-1]
    return statement.token_next(
        statement.token_index(t),
        skip_ws=True,
        skip_cm=True
    )[1]


def group_tokens(token, grp_cls, start_idx, end_idx, include_end=True):
    """
    tokenのサブグループをgrp_clsによってまとめる。
    sqlparse純正のものから機能を大幅に少なくし、さらに元のパースツリーを書き換えないよう
    変更したもの。
    """
    end_idx = end_idx + include_end
    subtokens = token.tokens[start_idx:end_idx]
    grp = grp_cls(subtokens)
    grp.parent = token
    return grp
