"""商城前台：商品列表、分类筛选、搜索、商品详情。"""

from flask import Blueprint, render_template, request, abort

from database import get_db

bp = Blueprint("shop", __name__)

PER_PAGE = 8


@bp.route("/")
def index():
    """商品列表，支持 ?category= 分类筛选、?q= 搜索、?page= 分页。"""
    db = get_db()
    page = max(request.args.get("page", 1, type=int), 1)
    category = request.args.get("category", "")
    query = request.args.get("q", "").strip()

    sql = """
        SELECT p.*, c.name AS category_name, c.slug AS category_slug
        FROM products p LEFT JOIN categories c ON c.id = p.category_id
        WHERE 1=1
    """
    params = []

    if category:
        sql += " AND c.slug = ?"
        params.append(category)
    if query:
        sql += " AND (p.name LIKE ? OR p.description LIKE ? OR c.name LIKE ?)"
        like = f"%{query}%"
        params += [like, like, like]

    total = db.execute(f"SELECT COUNT(*) AS n FROM ({sql})", params).fetchone()["n"]
    sql += " ORDER BY p.id LIMIT ? OFFSET ?"
    params += [PER_PAGE, (page - 1) * PER_PAGE]
    products = db.execute(sql, params).fetchall()

    categories = db.execute(
        """SELECT c.*, COUNT(p.id) AS product_count
           FROM categories c LEFT JOIN products p ON p.category_id = c.id
           GROUP BY c.id ORDER BY c.id"""
    ).fetchall()

    # 页面标题：搜索结果 / 分类名 / 全部商品
    if query:
        heading = f"搜索“{query}”"
    elif category:
        row = db.execute("SELECT name FROM categories WHERE slug = ?", (category,)).fetchone()
        heading = row["name"] if row else "全部商品"
    else:
        heading = "全部商品"

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        active_category=category,
        heading=heading,
        query=query,
        page=page,
        pages=(total + PER_PAGE - 1) // PER_PAGE,
        total=total,
    )


@bp.route("/product/<slug>")
def product(slug):
    db = get_db()
    row = db.execute(
        """SELECT p.*, c.name AS category_name, c.slug AS category_slug
           FROM products p LEFT JOIN categories c ON c.id = p.category_id
           WHERE p.slug = ?""",
        (slug,),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("product.html", product=row)
