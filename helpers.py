"""Shared helpers: money formatting, current user, cart access, decorators."""

from functools import wraps

from flask import g, redirect, session, url_for, flash

from database import get_db

# ---------------------------------------------------------------------------
# 金额（以「分」为单位存储整数，避免浮点数误差）
# ---------------------------------------------------------------------------

FREE_SHIPPING_THRESHOLD = 19900  # 满 ¥199 免运费
FLAT_SHIPPING_FEE = 1000         # 否则运费 ¥10


def format_money(cents):
    """68000 -> '¥680.00'"""
    return f"¥{cents / 100:,.2f}"


def shipping_fee(subtotal_cents):
    """购物车为空不收运费；满额免运费。"""
    if subtotal_cents <= 0:
        return 0
    return 0 if subtotal_cents >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING_FEE


# ---------------------------------------------------------------------------
# 订单状态：数据库存英文键，界面显示中文
# ---------------------------------------------------------------------------

STATUS_LABELS = {
    "pending": "待付款",
    "paid": "已付款",
    "shipped": "已发货",
    "delivered": "已完成",
    "cancelled": "已取消",
}


def status_label(status):
    return STATUS_LABELS.get(status, status)


# ---------------------------------------------------------------------------
# 当前登录用户（缓存在 g 上，每个请求只查询一次）
# ---------------------------------------------------------------------------

def current_user():
    if "user" not in g:
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
        else:
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    return g.user


# ---------------------------------------------------------------------------
# 购物车（保存在浏览器 session 中，形如 {商品id: 数量}）
# ---------------------------------------------------------------------------

def get_cart():
    """返回原始购物车字典，例如 {3: 2, 7: 1}。"""
    return session.get("cart", {})


def save_cart(cart):
    session["cart"] = cart
    session.modified = True


def get_cart_items():
    """返回带上商品信息的购物车明细，以及商品小计。

    每行：{"product": sqlite3.Row, "quantity": int, "line_total": int}
    返回 (lines, subtotal_cents)。
    """
    # session 中的键经过 JSON 序列化会变成字符串，这里统一转回整数
    cart = {int(product_id): qty for product_id, qty in get_cart().items()}
    if not cart:
        return [], 0

    db = get_db()
    placeholders = ",".join("?" * len(cart))
    products = db.execute(
        f"SELECT * FROM products WHERE id IN ({placeholders})",
        list(cart.keys()),
    ).fetchall()

    lines, subtotal = [], 0
    for product in products:
        quantity = cart[product["id"]]
        line_total = product["price_cents"] * quantity
        subtotal += line_total
        lines.append({
            "product": product,
            "quantity": quantity,
            "line_total": line_total,
        })
    lines.sort(key=lambda line: line["product"]["id"])
    return lines, subtotal


def cart_count():
    """购物车中的商品总件数（显示在导航栏）。"""
    return sum(get_cart().values())


# ---------------------------------------------------------------------------
# 装饰器
# ---------------------------------------------------------------------------

def login_required(view):
    """未登录时跳转到登录页。"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("请先登录。", "warning")
            return redirect(url_for("auth.login", next=path_hint()))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """仅允许管理员访问。"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("请先登录。", "warning")
            return redirect(url_for("auth.login"))
        if not user["is_admin"]:
            flash("仅限管理员访问。", "error")
            return redirect(url_for("shop.index"))
        return view(*args, **kwargs)
    return wrapped


def path_hint():
    from flask import request
    return request.path


# ---------------------------------------------------------------------------
# Jinja 全局变量：让每个模板都能用 cart_count / current_user
# ---------------------------------------------------------------------------

def inject_globals():
    return {"cart_count": cart_count(), "current_user": current_user()}
