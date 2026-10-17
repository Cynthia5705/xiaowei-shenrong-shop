"""Authentication: register, login, logout."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from helpers import current_user

bp = Blueprint("auth", __name__, url_prefix="/account")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not username or not email or not password:
            error = "请填写所有字段。"
        elif password != confirm:
            error = "两次输入的密码不一致。"
        elif len(username) < 3:
            error = "用户名至少需要 3 个字符。"
        elif len(password) < 6:
            error = "密码至少需要 6 位。"

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:  # UNIQUE 约束冲突
                error = "该用户名或邮箱已被注册。"
            else:
                flash("注册成功，请登录！", "success")
                return redirect(url_for("auth.login"))

        flash(error, "error")

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("用户名或密码错误。", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"欢迎回来，{user['username']}！", "success")
            # Send the user to ?next=... if provided, otherwise home
            next_url = request.args.get("next", "")
            if next_url.startswith("/"):  # only allow relative paths
                return redirect(next_url)
            return redirect(url_for("shop.index"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("已退出登录，期待再次光临！", "success")
    return redirect(url_for("shop.index"))


@bp.route("/orders")
def orders():
    """当前用户的订单记录。"""
    user = current_user()
    if user is None:
        flash("请先登录。", "warning")
        return redirect(url_for("auth.login"))

    orders = get_db().execute(
        """SELECT o.*, COUNT(i.id) AS item_count
           FROM orders o LEFT JOIN order_items i ON i.order_id = o.id
           WHERE o.user_id = ? GROUP BY o.id ORDER BY o.id DESC""",
        (user["id"],),
    ).fetchall()
    return render_template("orders.html", orders=orders)
