"""Admin panel: dashboard, product CRUD, order management.

Everything here requires a signed-in user with is_admin = 1.
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash)

from database import get_db, slugify
from helpers import admin_required, status_label
from checkout import ORDER_STATUSES

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def dashboard():
    db = get_db()
    stats = {
        "products": db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"],
        "customers": db.execute(
            "SELECT COUNT(*) AS n FROM users WHERE is_admin = 0").fetchone()["n"],
        "orders": db.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"],
        "revenue_cents": db.execute(
            """SELECT COALESCE(SUM(total_cents), 0) AS n FROM orders
               WHERE status != 'cancelled'"""
        ).fetchone()["n"],
    }
    recent_orders = db.execute(
        """SELECT o.*, u.username FROM orders o
           JOIN users u ON u.id = o.user_id
           ORDER BY o.id DESC LIMIT 5"""
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@bp.route("/products")
@admin_required
def products():
    rows = get_db().execute(
        """SELECT p.*, c.name AS category_name FROM products p
           LEFT JOIN categories c ON c.id = p.category_id
           ORDER BY p.id DESC"""
    ).fetchall()
    return render_template("admin/products.html", products=rows)


def _product_form_data():
    """Validate the product form; returns (data, error)."""
    name = request.form.get("name", "").strip()
    data = {
        "name": name,
        "slug": request.form.get("slug", "").strip() or slugify(name),
        "description": request.form.get("description", "").strip(),
        "price": request.form.get("price", type=float),
        "stock": request.form.get("stock", 0, type=int),
        "emoji": request.form.get("emoji", "📦").strip() or "📦",
        "category_id": request.form.get("category_id", type=int),
    }
    if not name:
        return data, "请填写商品名称。"
    if data["price"] is None or data["price"] < 0:
        return data, "请输入有效的价格。"
    return data, None


@bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "POST":
        data, error = _product_form_data()
        if error:
            flash(error, "error")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO products
                   (name, slug, description, price_cents, stock, emoji, category_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (data["name"], data["slug"], data["description"],
                 round(data["price"] * 100), data["stock"],
                 data["emoji"], data["category_id"]),
            )
            db.commit()
            flash("商品已创建。", "success")
            return redirect(url_for("admin.products"))

    categories = get_db().execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("admin/product_form.html", product=None, categories=categories)


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("未找到该商品。", "error")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        data, error = _product_form_data()
        if error:
            flash(error, "error")
        else:
            db.execute(
                """UPDATE products SET name = ?, slug = ?, description = ?,
                   price_cents = ?, stock = ?, emoji = ?, category_id = ?
                   WHERE id = ?""",
                (data["name"], data["slug"], data["description"],
                 round(data["price"] * 100), data["stock"],
                 data["emoji"], data["category_id"], product_id),
            )
            db.commit()
            flash("商品已更新。", "success")
            return redirect(url_for("admin.products"))

    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("admin/product_form.html", product=product, categories=categories)


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    flash("商品已删除。", "success")
    return redirect(url_for("admin.products"))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@bp.route("/orders")
@admin_required
def orders():
    rows = get_db().execute(
        """SELECT o.*, u.username,
                  (SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.id) AS item_count
           FROM orders o JOIN users u ON u.id = o.user_id
           ORDER BY o.id DESC"""
    ).fetchall()
    return render_template("admin/orders.html", orders=rows)


@bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
@admin_required
def order_detail(order_id):
    db = get_db()
    order = db.execute(
        "SELECT o.*, u.username FROM orders o JOIN users u ON u.id = o.user_id WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    if order is None:
        flash("未找到该订单。", "error")
        return redirect(url_for("admin.orders"))

    if request.method == "POST":
        status = request.form.get("status", "")
        if status in ORDER_STATUSES:
            db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            db.commit()
            flash(f"订单 #{order_id} 状态已更新为「{status_label(status)}」。", "success")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    return render_template(
        "admin/order_detail.html", order=order, items=items,
        statuses=ORDER_STATUSES,
    )
