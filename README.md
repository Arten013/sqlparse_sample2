# sqlparseサンプルコード その2 (開発中)

[sqlparseの解説記事中](https://blog.hoxo-m.com/entry/sqlparse_parse) で紹介したサンプルコードです。
詳しくは記事をご参照ください。

また、何かございましたらお気軽に記事中へのコメントでご指摘ください。

# table_graphについて
HiveQLで書かれたクエリを入力として、その中で使われるテーブルの相関を表示するプログラムです。

# 環境
Python >= 3.6, sqlparse == 0.3.0での動作を確認しています。

# 使用方法
ポジトリのホームで以下のコマンドを実行してください（インストール不要）。

```bash
$ python -m table_graph <sql_file_path>
```

# 実行例git
```bash
$ python -m table_graph samples/01.sql 
Query 1
__root__ -> page_views

$ python -m table_graph samples/04.sql 
Query 1
__root__ -> 4329279560
4329279560 -> B
__root__ -> A
Query 2
__root__ -> 4329280400
4329280400 -> T2
__root__ -> T1
```

# References 
以下のサイトからサンプルクエリを引用させていただきました。
- [Hive Language Manual](https://cwiki.apache.org/confluence/display/Hive/LanguageManual)
