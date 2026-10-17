"""冒烟测试：对运行中的服务器完整走一遍下单流程。"""

import urllib.request, urllib.parse, http.cookiejar, sys

BASE = "http://127.0.0.1:5000"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

failures = []


def _url(path):
    # 中文查询词需要先做 URL 编码
    return BASE + urllib.parse.quote(path, safe="/?=&%")


def get(path):
    with opener.open(_url(path)) as r:
        return r.status, r.read().decode("utf-8", "replace")


def post(path, data):
    body = urllib.parse.urlencode(data).encode()
    with opener.open(_url(path), data=body) as r:
        return r.status, r.read().decode("utf-8", "replace")


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


# 1. 商品列表
status, html = get("/")
check("商品列表可访问", status == 200 and "长白山六年根红参" in html)

# 2. 分类筛选 + 搜索
status, html = get("/?category=shan-zhen")
check("分类筛选", status == 200 and "黑木耳" in html)
status, html = get("/?q=蜂蜜")
check("关键词搜索", status == 200 and "椴树原蜜" in html)

# 3. 商品详情
status, html = get("/product/changbaishan-hongshen")
check("商品详情页", status == 200 and "¥680.00" in html)

# 4. 不存在的商品 -> 404
try:
    get("/product/nope")
    check("不存在的商品返回 404", False)
except urllib.error.HTTPError as e:
    check("不存在的商品返回 404", e.code == 404)

# 5. 注册 + 登录
status, html = post("/account/register",
                    {"username": "alice", "email": "alice@example.com",
                     "password": "secret123", "confirm": "secret123"})
check("注册", status == 200)
status, html = post("/account/login",
                    {"username": "alice", "password": "secret123"})
check("登录", status == 200 and "欢迎回来，alice" in html)

# 6. 加入购物车：红参 ¥680 ×2 + 黑木耳 ¥68 ×1
post("/cart/add/1", {"quantity": "2"})
post("/cart/add/6", {"quantity": "1"})
status, html = get("/cart/")
check("购物车显示商品", status == 200 and "¥1,428.00" in html)   # 1360 + 68
check("满额免运费", "免运费" in html)

# 7. 修改数量
post("/cart/update", {"qty_1": "1", "qty_6": "1"})
status, html = get("/cart/")
check("更新数量", status == 200 and "¥748.00" in html)          # 680 + 68

# 8. 无效卡号被拦截
status, html = post("/checkout/",
                    {"customer_name": "爱丽丝", "email": "alice@example.com",
                     "address": "长白山北路 88 号", "city": "长春市",
                     "country": "吉林省", "postal_code": "130000",
                     "card_number": "123"})
check("无效卡号被拒绝", "16 位卡号" in html)

# 9. 有效（模拟）卡号下单成功
status, html = post("/checkout/",
                    {"customer_name": "Alice", "email": "alice@example.com",
                     "address": "长白山北路 88 号", "city": "长春市",
                     "country": "吉林省", "postal_code": "130000",
                     "card_number": "4242424242424242"})
check("下单成功", status == 200 and "感谢您的订购，Alice" in html)
check("显示模拟交易号", "MOCK-" in html)

# 10. 库存已扣减（红参原为 30 件）
status, html = get("/product/changbaishan-hongshen")
check("库存已扣减", "库存 29 件" in html)

# 11. 下单后购物车被清空
status, html = get("/cart/")
check("购物车已清空", "购物车还是空的" in html)

# 12. 订单记录
status, html = get("/account/orders")
check("我的订单", status == 200 and "已付款" in html)

# 13. 小额外收运费：香菇 ¥45 + 运费 ¥10 = ¥55
post("/cart/add/8", {"quantity": "1"})
status, html = get("/cart/")
check("未满额收取运费", "¥55.00" in html)
post("/cart/clear", {})

# 14. 未登录无法结算
cj.clear()
status, html = get("/checkout/")
check("未登录跳转登录页", "请先登录" in html)

# 15. 管理员登录 + 数据概览
post("/account/login", {"username": "admin", "password": "admin123"})
status, html = get("/admin/")
check("管理后台数据概览", status == 200 and "销售额" in html)

# 16. 商品管理
status, html = get("/admin/products")
check("商品管理列表", status == 200 and "长白山六年根红参" in html)
status, html = post("/admin/products/new",
                    {"name": "长白山野山参", "description": "测试商品",
                     "price": "9.99", "stock": "5", "emoji": "🌱",
                     "category_id": "1", "slug": "yeshanshen"})
check("新建商品", "长白山野山参" in html)
status, html = get("/product/yeshanshen")
check("新商品出现在商城", status == 200 and "¥9.99" in html)

# 17. 订单管理
status, html = get("/admin/orders")
check("订单管理列表", status == 200 and "#1" in html)
status, html = post("/admin/orders/1", {"status": "shipped"})
check("修改订单状态", "已发货" in html)

# 18. 普通用户无法进入后台
cj.clear()
post("/account/login", {"username": "alice", "password": "secret123"})
status, html = get("/admin/")
check("普通用户无法进入后台", "销售额" not in html)

print()
print(f"{len(failures)} 项失败" if failures else "全部测试通过")
sys.exit(1 if failures else 0)
