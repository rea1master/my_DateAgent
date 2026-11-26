"""构建本地 SQLite 数据库:建表 + 生成种子数据

用法:python app/data/init_db.py
产物:app/data/dataagent.db
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "dataagent.db"
BASE_DT = datetime(2023, 1, 1)


def dts(days: int = 0, hours: int = 0) -> str:
    return (BASE_DT + timedelta(days=days, hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


REGIONS = [
    ("北京", "北京"), ("上海", "上海"), ("广东", "广州"), ("广东", "深圳"),
    ("浙江", "杭州"), ("江苏", "南京"), ("四川", "成都"), ("湖北", "武汉"),
    ("陕西", "西安"), ("重庆", "重庆"), ("天津", "天津"), ("湖南", "长沙"),
    ("河南", "郑州"), ("山东", "青岛"), ("福建", "厦门"), ("辽宁", "沈阳"),
    ("安徽", "合肥"), ("江西", "南昌"), ("云南", "昆明"), ("贵州", "贵阳"),
]

BRANDS = [
    ("华为", 1987, "中国"), ("小米", 2010, "中国"), ("苹果", 1976, "美国"),
    ("三星", 1938, "韩国"), ("联想", 1984, "中国"), ("戴尔", 1984, "美国"),
    ("索尼", 1946, "日本"), ("OPPO", 2004, "中国"), ("vivo", 2009, "中国"),
    ("海尔", 1984, "中国"), ("美的", 1968, "中国"), ("格力", 1991, "中国"),
]

SUPPLIERS = [
    ("华南电子供应链", 3, "s1@supply.com"), ("华东数码贸易", 5, "s2@supply.com"),
    ("华北家电批发", 1, "s3@supply.com"), ("西南百货供应", 7, "s4@supply.com"),
    ("华中服饰批发", 8, "s5@supply.com"), ("东北食品供应链", 16, "s6@supply.com"),
    ("西北日用品", 9, "s7@supply.com"), ("华南服饰城", 4, "s8@supply.com"),
    ("华东办公用品", 6, "s9@supply.com"), ("北京综合物资", 1, "s10@supply.com"),
]

CATEGORIES = [
    ("电子产品", None), ("手机", 1), ("电脑", 1),
    ("家电", None), ("电视", 4), ("冰箱", 4),
    ("服装", None), ("男装", 7), ("女装", 7),
    ("食品", None), ("零食", 10), ("饮料", 10),
]

CARRIERS = [
    ("顺丰", "express"), ("圆通", "standard"), ("中通", "standard"),
    ("京东物流", "express"), ("韵达", "standard"),
]


def price_of(product_id: int) -> float:
    return float(100 + (product_id * 37) % 900)


def build() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    con.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))
    cur = con.cursor()

    # ---------- 维度 ----------
    cur.executemany(
        "INSERT INTO regions (region_id, province, city) VALUES (?,?,?)",
        [(i + 1, p, c) for i, (p, c) in enumerate(REGIONS)],
    )
    cur.executemany(
        "INSERT INTO brands (brand_id, name, founded_year, country) VALUES (?,?,?,?)",
        [(i + 1, n, y, c) for i, (n, y, c) in enumerate(BRANDS)],
    )
    cur.executemany(
        "INSERT INTO suppliers (supplier_id, name, region_id, contact_email) VALUES (?,?,?,?)",
        [(i + 1, n, r, e) for i, (n, r, e) in enumerate(SUPPLIERS)],
    )
    cur.executemany(
        "INSERT INTO categories (category_id, name, parent_id) VALUES (?,?,?)",
        [(i + 1, n, p) for i, (n, p) in enumerate(CATEGORIES)],
    )
    cur.executemany(
        "INSERT INTO carriers (carrier_id, name, type) VALUES (?,?,?)",
        [(i + 1, n, t) for i, (n, t) in enumerate(CARRIERS)],
    )

    # ---------- 用户 ----------
    users = []
    for i in range(1, 301):
        users.append((
            i, f"用户{i}", f"user{i}@example.com", f"138{i:08d}",
            (i % 20) + 1,
            "male" if i % 2 == 0 else "female",
            18 + (i * 7) % 43,
            dts(i % 900),
            "disabled" if i % 17 == 0 else "active",
        ))
    cur.executemany(
        "INSERT INTO users (user_id,name,email,phone,region_id,gender,age,registered_at,status) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        users,
    )

    # ---------- 商品 ----------
    products = []
    for i in range(1, 151):
        price = price_of(i)
        products.append((
            i, f"商品{i}", (i % 12) + 1, (i % 12) + 1, (i % 10) + 1,
            price, round(price * 0.6, 2), (i * 13) % 500,
            "off_shelf" if i % 23 == 0 else "on_sale",
            dts(i % 300),
        ))
    cur.executemany(
        "INSERT INTO products (product_id,name,category_id,brand_id,supplier_id,price,cost,stock,status,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        products,
    )

    # ---------- 商品属性 EAV ----------
    attrs = []
    for i in range(1, 301):
        k = i % 3
        if k == 0:
            name, value = "颜色", ["黑色", "白色", "蓝色", "红色"][i % 4]
        elif k == 1:
            name, value = "尺码", ["S", "M", "L"][i % 3]
        else:
            name, value = "材质", ["棉", "聚酯纤维", "皮革"][i % 3]
        attrs.append((i, (i % 150) + 1, name, value))
    cur.executemany(
        "INSERT INTO product_attributes (attribute_id,product_id,attr_name,attr_value) VALUES (?,?,?,?)",
        attrs,
    )

    # ---------- 优惠券 ----------
    coupons = []
    for i in range(1, 13):
        typ = "percent" if i % 2 == 0 else "fixed"
        val = 0.9 if typ == "percent" else 10.0
        coupons.append((
            i, f"CODE{i}", typ, val, 100.0,
            dts(0), "2024-12-31 00:00:00",
            "expired" if i % 6 == 0 else "active",
        ))
    cur.executemany(
        "INSERT INTO coupons (coupon_id,code,type,discount_value,min_amount,valid_from,valid_until,status) "
        "VALUES (?,?,?,?,?,?,?,?)",
        coupons,
    )

    # ---------- 订单明细(先生成,用于回填订单金额) ----------
    order_items = []
    for i in range(1, 1601):
        order_id = (i - 1) // 2 + 1
        pid = (i % 150) + 1
        qty = (i % 4) + 1
        unit = price_of(pid)
        order_items.append((i, order_id, pid, qty, unit, round(unit * qty, 2)))

    totals = {}
    for row in order_items:
        totals[row[1]] = totals.get(row[1], 0.0) + row[5]

    # ---------- 订单(金额直接算好) ----------
    orders = []
    status_map = {0: "cancelled", 1: "pending", 2: "paid", 3: "shipped"}
    for i in range(1, 801):
        m = i % 10
        status = status_map.get(m, "delivered")
        total = round(totals.get(i, 0.0), 2)
        coupon_id = ((i % 12) + 1) if i % 4 == 0 else None
        if status in ("cancelled", "pending"):
            # 未支付/已取消:没有实际支付
            discount = 0.0
            pay = 0.0
        else:
            discount = round(total * 0.1, 2) if coupon_id is not None else 0.0
            pay = round(total - discount, 2)
        created = dts(i % 700)
        paid = None if m in (0, 1) else dts(i % 700, 2)
        orders.append((
            i, (i * 7 % 300) + 1, status, total, discount, pay,
            coupon_id, (i % 20) + 1, created, paid,
        ))
    cur.executemany(
        "INSERT INTO orders (order_id,user_id,status,total_amount,discount_amount,pay_amount,coupon_id,region_id,created_at,paid_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        orders,
    )
    cur.executemany(
        "INSERT INTO order_items (item_id,order_id,product_id,quantity,unit_price,subtotal) VALUES (?,?,?,?,?,?)",
        order_items,
    )

    # ---------- 支付 / 物流 ----------
    methods = ["alipay", "wechat", "card", "cod"]
    payments, shipments = [], []
    for o in orders:
        oid, _, status, _, _, pay, _, _, _, paid = o
        if status in ("paid", "shipped", "delivered"):
            payments.append((oid, oid, methods[oid % 4], pay, "success", paid))
            ship_status = "delivered" if status == "delivered" else ("shipped" if status == "shipped" else "pending")
            delivered_at = None
            if status == "delivered":
                delivered_at = (datetime.strptime(paid, "%Y-%m-%d %H:%M:%S") + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            shipments.append((oid, oid, (oid % 5) + 1, f"SF{oid}", ship_status, paid, delivered_at))
    cur.executemany(
        "INSERT INTO payments (payment_id,order_id,method,amount,status,paid_at) VALUES (?,?,?,?,?,?)",
        payments,
    )
    cur.executemany(
        "INSERT INTO shipments (shipment_id,order_id,carrier_id,tracking_no,status,shipped_at,delivered_at) "
        "VALUES (?,?,?,?,?,?,?)",
        shipments,
    )

    # ---------- 退款 ----------
    reasons = ["质量问题", "尺码不合适", "不想要了", "发错货"]
    refund_status = ["refunded", "approved", "rejected", "applied"]
    refunds = []
    for i in range(1, 61):
        refunds.append((
            i, (i * 3 % 800) + 1, None,
            round((i * 7 % 100) + 10, 2),
            reasons[i % 4], refund_status[i % 4], dts(150 + i % 300),
        ))
    cur.executemany(
        "INSERT INTO refunds (refund_id,order_id,item_id,amount,reason,status,created_at) VALUES (?,?,?,?,?,?,?)",
        refunds,
    )

    # ---------- 评价 ----------
    contents = ["非常满意", "还不错", "一般", "不太满意", "差评"]
    reviews = []
    for i in range(1, 251):
        reviews.append((
            i, (i * 5 % 800) + 1, (i % 150) + 1, (i * 7 % 300) + 1,
            (i % 5) + 1, contents[i % 5], dts(150 + i % 300),
        ))
    cur.executemany(
        "INSERT INTO reviews (review_id,order_id,product_id,user_id,rating,content,created_at) VALUES (?,?,?,?,?,?,?)",
        reviews,
    )

    con.commit()

    print(f"建库完成:{DB_PATH}\n")
    print("各表行数:")
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]
    for t in tables:
        n = cur.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        print(f"  {t:<20} {n:>6}")

    con.close()


if __name__ == "__main__":
    build()
