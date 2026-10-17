"""Database layer: SQLite connection, schema, and seed data.

Everything a Flask app needs to talk to the database lives here.
Tables:

    users        - shop customers (and admins)
    categories   - product categories
    products     - items for sale (prices stored as integer cents!)
    orders       - one row per checkout
    order_items  - the products that made up each order
"""

import os
import sqlite3

from flask import current_app, g

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def get_db():
    """Return the connection for the current request (cached on `g`)."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row  # access columns by name: row["price_cents"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Close the connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Schema + seed data
# ---------------------------------------------------------------------------

SCHEMA = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    emoji       TEXT NOT NULL DEFAULT '📦',   -- used instead of product images
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    status       TEXT NOT NULL DEFAULT 'pending',
    total_cents  INTEGER NOT NULL,
    customer_name  TEXT NOT NULL,
    email        TEXT NOT NULL,
    address      TEXT NOT NULL,
    city         TEXT NOT NULL,
    country      TEXT NOT NULL,
    postal_code  TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE order_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id         INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id       INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name     TEXT NOT NULL,          -- snapshot: name at time of purchase
    unit_price_cents INTEGER NOT NULL,       -- snapshot: price at time of purchase
    quantity         INTEGER NOT NULL
);
"""

SEED_CATEGORIES = [
    ("参茸滋补", "shen-rong"),
    ("山珍干货", "shan-zhen"),
    ("蜂蜜蜂产品", "feng-mi"),
    ("茶叶茗品", "cha-ye"),
    ("东北特产", "dongbei"),
]

# (名称, slug, 描述, 价格(分), 库存, 图标, 分类 slug)
SEED_PRODUCTS = [
    ("长白山六年根红参", "changbaishan-hongshen",
     "精选长白山六年生红参，参香浓郁，切片泡水、炖汤皆宜。",
     68000, 30, "🫚", "shen-rong"),
    ("特级鹿茸片", "teji-lurongpian",
     "梅花鹿头茬二杠鹿茸，蜡片细腻，滋补强身。",
     128000, 12, "🦌", "shen-rong"),
    ("西洋参切片", "xiyangshen-qiepian",
     "进口花旗参切片，含服、泡茶、炖汤均佳，清补不上火。",
     36000, 25, "🌿", "shen-rong"),
    ("长白山野生灵芝", "yesheng-lingzhi",
     "长白山野生赤灵芝，切片煮水，滋补养生。",
     42000, 18, "🍄", "shen-rong"),
    ("古法阿胶糕", "gufa-ejiaogao",
     "东阿阿胶搭配核桃、黑芝麻，即食方便，气血双补。",
     19800, 40, "🍫", "shen-rong"),
    ("东北野生黑木耳", "dongbei-heimuer",
     "秋木耳厚无根，泡发率高，凉拌、炒菜两相宜。",
     6800, 60, "🫘", "shan-zhen"),
    ("长白山野生榛蘑", "changbaishan-zhenmo",
     "林间野生榛蘑，晒干锁鲜，炖小鸡最是地道。",
     8800, 35, "🪵", "shan-zhen"),
    ("特级干香菇", "teji-xianggu",
     "肉厚柄短，香气浓郁，煲汤提鲜必备。",
     4500, 50, "🍄", "shan-zhen"),
    ("天目山笋干", "tianmushan-sungan",
     "嫩笋烘干，泡发后爽脆清甜，红烧炖肉都好吃。",
     5600, 45, "🎋", "shan-zhen"),
    ("长白山椴树原蜜", "changbaishan-duanshu-mifeng",
     "东北椴树花期成熟蜜，结晶细腻，入口花香清甜。",
     12800, 32, "🍯", "feng-mi"),
    ("蜂王浆冻干粉", "fengwangjiang-dongganfen",
     "低温冻干工艺锁住活性，每日一小勺，滋补养身。",
     16800, 20, "🐝", "feng-mi"),
    ("天然蜂花粉", "tianran-feng-huafen",
     "纯净蜂花粉，可直接冲服或加入酸奶、燕麦。",
     8800, 28, "🌼", "feng-mi"),
    ("明前西湖龙井", "mingqian-longjing",
     "清明前采摘，芽叶细嫩，豆香清雅，回甘持久。",
     28800, 22, "🍵", "cha-ye"),
    ("云南古树红茶", "yunnan-gushu-hongcha",
     "百年古树鲜叶制成，汤色红艳，蜜香浓郁。",
     15800, 26, "🫖", "cha-ye"),
    ("东北开口松子", "dongbei-kaikou-songzi",
     "大颗粒开口松子，粒粒饱满，原味烘炒。",
     9800, 55, "🌰", "dongbei"),
    ("云南薄皮核桃", "yunnan-baopi-hetao",
     "一捏即开的薄皮核桃，果仁香脆，无苦涩味。",
     5800, 48, "🥜", "dongbei"),
    ("五常稻花香大米", "wuchang-daohuaxiang-dami",
     "黑龙江五常核心产区，米粒油亮，蒸饭满屋飘香。",
     7800, 40, "🌾", "dongbei"),
]


def init_db():
    """创建数据表并写入演示数据。会清空现有数据库！"""
    db = get_db()
    db.executescript(SCHEMA)

    db.executemany("INSERT INTO categories (name, slug) VALUES (?, ?)",
                   SEED_CATEGORIES)
    categories = {row["slug"]: row["id"] for row in
                  db.execute("SELECT id, slug FROM categories")}

    db.executemany(
        """INSERT INTO products (name, slug, description, price_cents, stock, emoji, category_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(name, slug, desc, price, stock, emoji, categories[cat_slug])
         for name, slug, desc, price, stock, emoji, cat_slug in SEED_PRODUCTS],
    )

    # 演示管理员账号（用户名：admin / 密码：admin123）
    from werkzeug.security import generate_password_hash
    db.execute(
        "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
        ("admin", "admin@example.com", generate_password_hash("admin123")),
    )
    db.commit()


def init_db_if_needed(app):
    """Create and seed shop.db on first run. Call with the Flask app object."""
    db_path = app.config["DATABASE"]
    if not os.path.exists(db_path):
        with app.app_context():
            init_db()


def slugify(text):
    """把「长白山红参 Green Tea」转成可用的 URL 别名（保留中文）。"""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")
