# 家計簿アプリ

Flask + SQLite で作成したシンプルな家計簿 Web アプリです。

## 機能

- 収入・支出の追加 / 削除
- 月別フィルタリング
- 収入 / 支出 / 残高のサマリー表示
- カテゴリ別集計・グラフ表示（Chart.js）
- 月別収支推移グラフ
- CSV エクスポート

## 技術スタック

| 用途 | 技術 |
|---|---|
| Web フレームワーク | Flask 3.x |
| データベース | SQLite |
| UI | Bootstrap 5 |
| グラフ | Chart.js 4 |

## セットアップ

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# サーバー起動
python main.py
```

ブラウザで `http://127.0.0.1:5001` を開いてください。

## ファイル構成

```
.
├── main.py          # Flask ルーティング
├── database.py      # DB 操作 (SQLite)
├── requirements.txt
├── templates/
│   ├── base.html    # 共通レイアウト
│   ├── index.html   # 収支一覧
│   ├── add.html     # 収支追加
│   └── summary.html # 集計・グラフ
└── static/
    └── style.css
```

## カテゴリ

**収入:** 給与 / 副業 / 賞与 / その他

**支出:** 食費 / 交通費 / 住居費 / 光熱費 / 娯楽費 / 医療費 / 衣類 / 通信費 / その他
