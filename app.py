"""Flask ecommerce demo — application entry point.

Run it with:
    python app.py
then open http://127.0.0.1:5000

Demo admin login:  admin / admin123
"""

from flask import Flask, render_template
import os

from database import close_db, init_db_if_needed
from helpers import inject_globals, format_money, status_label


def create_app():
    app = Flask(__name__)
    # 生产环境请设置环境变量 SECRET_KEY；本地开发用默认值
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    app.config["DATABASE"] = os.environ.get(
        "DATABASE_PATH", os.path.join(app.root_path, "shop.db")
    )

    # Database lifecycle: open per request, close at the end
    app.teardown_appcontext(close_db)

    # Available in every template: {{ current_user }}, {{ cart_count }}
    app.context_processor(inject_globals)

    # Jinja 过滤器：{{ product.price_cents | money }}、{{ order.status | status_label }}
    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["status_label"] = status_label

    # URL -> view mappings, grouped into blueprints
    from shop import bp as shop_bp
    from auth import bp as auth_bp
    from cart import bp as cart_bp
    from checkout import bp as checkout_bp
    from admin import bp as admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(admin_bp)

    # 友好的错误页面
    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="页面不存在。"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="您没有权限访问该页面。"), 403

    # 首次运行时创建并写入演示数据
    init_db_if_needed(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
