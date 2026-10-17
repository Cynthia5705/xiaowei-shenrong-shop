"""Shopping cart: add, update quantities, remove, clear."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from database import get_db
from helpers import get_cart, save_cart, get_cart_items, shipping_fee

bp = Blueprint("cart", __name__, url_prefix="/cart")


@bp.route("/")
def view():
    lines, subtotal = get_cart_items()
    shipping = shipping_fee(subtotal)
    return render_template(
        "cart.html", lines=lines, subtotal=subtotal,
        shipping=shipping, total=subtotal + shipping,
    )


@bp.route("/add/<int:product_id>", methods=["POST"])
def add(product_id):
    product = get_db().execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if product is None:
        return redirect(url_for("shop.index"))

    quantity = max(request.form.get("quantity", 1, type=int), 1)

    cart = get_cart()
    key = str(product_id)
    new_qty = cart.get(key, 0) + quantity
    if new_qty > product["stock"]:
        new_qty = product["stock"]
        flash(f"库存仅剩 {product['stock']} 件，已为您调整数量。", "warning")

    if new_qty <= 0:
        flash("抱歉，该商品暂时缺货。", "error")
        return redirect(url_for("shop.product", slug=product["slug"]))

    cart[key] = new_qty
    save_cart(cart)
    flash(f"已将“{product['name']}”加入购物车。", "success")
    # Only follow relative "next" links (avoids open-redirect abuse)
    next_url = request.form.get("next", "")
    return redirect(next_url if next_url.startswith("/") else url_for("cart.view"))


@bp.route("/update", methods=["POST"])
def update():
    cart = get_cart()
    for product_id, value in request.form.items():
        if product_id.startswith("qty_") and product_id[4:].isdigit():
            quantity = max(int(value or 0), 0)
            if quantity == 0:
                cart.pop(product_id[4:], None)
            else:
                cart[product_id[4:]] = quantity
    save_cart(cart)
    flash("购物车已更新。", "success")
    return redirect(url_for("cart.view"))


@bp.route("/remove/<int:product_id>", methods=["POST"])
def remove(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    flash("已移除该商品。", "success")
    return redirect(url_for("cart.view"))


@bp.route("/clear", methods=["POST"])
def clear():
    save_cart({})
    flash("购物车已清空。", "success")
    return redirect(url_for("shop.index"))
