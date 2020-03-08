# sqlparseサンプルコード その2

ブログにて解説予定のsqlparseサンプルコードです。

# table_graphについて
HiveQLで書かれたクエリを入力として、その中で使われるテーブル/サブクエリ間の相関を表示するプログラムです。
なお、CTE（WITH句）は非対応です。

# 環境
Python >= 3.6, sqlparse == 0.3.0での動作を確認しています。

# 使用方法
リポジトリのホームで以下のコマンドを実行してください（インストール不要）。

```bash
$ python -m table_graph <sql_file_path>
```

# 実行例
__root__はクエリ全体を、数値はエイリアスのないサブクエリのIDを表しています。

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
