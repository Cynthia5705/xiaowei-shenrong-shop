"""结算（模拟支付）与订单确认页。"""

import random

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort)

from database import get_db
from helpers import (current_user, get_cart, save_cart, get_cart_items,
                     shipping_fee)

bp = Blueprint("checkout", __name__, url_prefix="/checkout")

ORDER_STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled"]


@bp.route("/", methods=["GET", "POST"])
def checkout():
    user = current_user()
    if user is None:
        flash("请先登录后再结算。", "warning")
        return redirect(url_for("auth.login", next="/checkout/"))

    lines, subtotal = get_cart_items()
    if not lines:
        flash("购物车是空的。", "warning")
        return redirect(url_for("shop.index"))

    shipping = shipping_fee(subtotal)
    total = subtotal + shipping

    if request.method == "POST":
        # ---- 1. 校验收货信息 -------------------------------------------
        fields = {
            "customer_name": request.form.get("customer_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "address": request.form.get("address", "").strip(),
            "city": request.form.get("city", "").strip(),
            "country": request.form.get("country", "").strip(),
            "postal_code": request.form.get("postal_code", "").strip(),
        }
        card_number = request.form.get("card_number", "").replace(" ", "")

        if not all(fields.values()):
            flash("请填写完整的收货信息。", "error")
        elif len(card_number) != 16 or not card_number.isdigit():
            flash("请输入 16 位卡号（本店为演示环境，任意数字均可）。", "error")
        else:
            db = get_db()
            # ---- 2. 下单前再次核对库存 ---------------------------------
            cart = {int(pid): qty for pid, qty in get_cart().items()}
            rows = db.execute(
                f"SELECT * FROM products WHERE id IN ({','.join('?' * len(cart))})",
                list(cart),
            ).fetchall()
            out_of_stock = [
                row["name"] for row in rows
                if cart[row["id"]] > row["stock"]
            ]
            if out_of_stock:
                flash(f"以下商品库存不足：{'、'.join(out_of_stock)}。请调整购物车。", "error")
            else:
                # ---- 3.「扣款」并生成订单（模拟！） --------------------
                fake_transaction = f"MOCK-{random.randint(10**8, 10**9 - 1):09d}"
                cursor = db.execute(
                    """INSERT INTO orders
                       (user_id, status, total_cents, customer_name, email,
                        address, city, country, postal_code)
                       VALUES (?, 'paid', ?, ?, ?, ?, ?, ?, ?)""",
                    (user["id"], total, fields["customer_name"], fields["email"],
                     fields["address"], fields["city"], fields["country"],
                     fields["postal_code"]),
                )
                order_id = cursor.lastrowid

                # ---- 4. 把商品快照写入 order_items ---------------------
                for row in rows:
                    quantity = cart[row["id"]]
                    db.execute(
                        """INSERT INTO order_items
                           (order_id, product_id, product_name,
                            unit_price_cents, quantity)
                           VALUES (?, ?, ?, ?, ?)""",
                        (order_id, row["id"], row["name"],
                         row["price_cents"], quantity),
                    )
                    # ---- 5. 扣减库存 ----------------------------------
                    db.execute(
                        "UPDATE products SET stock = stock - ? WHERE id = ?",
                        (quantity, row["id"]),
                    )
                db.commit()

                save_cart({})  # 清空购物车
                flash(f"支付成功！交易号 {fake_transaction}", "success")
                return redirect(url_for("checkout.confirmation", order_id=order_id))

    return render_template(
        "checkout.html", lines=lines, subtotal=subtotal,
        shipping=shipping, total=total,
    )


@bp.route("/confirmation/<int:order_id>")
def confirmation(order_id):
    user = current_user()
    if user is None:
        abort(403)

    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        (order_id, user["id"]),
    ).fetchone()
    if order is None:
        abort(404)

    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    return render_template("confirmation.html", order=order, items=items)
