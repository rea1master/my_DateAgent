-- =============================================================================
-- DataAgent 电商样例库 Schema —— SQLite 版
-- 由 PostgreSQL 版 schema.sql 转写，零依赖、本地即用
-- 差异:
--   * BIGSERIAL → INTEGER PRIMARY KEY(种子数据显式给 id)
--   * TIMESTAMPTZ → TEXT(存 'YYYY-MM-DD HH:MM:SS',便于 strftime)
--   * 金额用 DECIMAL(12,2)，SQLite 按 NUMERIC 亲和性存储
-- =============================================================================

PRAGMA foreign_keys = ON;

-- ---------- 支持表(维度) ----------
CREATE TABLE regions (
    region_id INTEGER PRIMARY KEY,
    province  TEXT NOT NULL,
    city      TEXT NOT NULL,
    UNIQUE (province, city)
);

CREATE TABLE brands (
    brand_id     INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    founded_year INTEGER,
    country      TEXT
);

CREATE TABLE suppliers (
    supplier_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    region_id     INTEGER REFERENCES regions(region_id),
    contact_email TEXT
);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    parent_id   INTEGER REFERENCES categories(category_id)
);

CREATE TABLE carriers (
    carrier_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    type       TEXT
);

-- ---------- 用户 / 商品 ----------
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    region_id     INTEGER REFERENCES regions(region_id),
    gender        TEXT,
    age           INTEGER,
    registered_at TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    brand_id    INTEGER REFERENCES brands(brand_id),
    supplier_id INTEGER REFERENCES suppliers(supplier_id),
    price       DECIMAL(10,2) NOT NULL,
    cost        DECIMAL(10,2) NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'on_sale',
    created_at  TEXT NOT NULL
);

CREATE TABLE product_attributes (
    attribute_id INTEGER PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    attr_name    TEXT NOT NULL,
    attr_value   TEXT NOT NULL
);

-- ---------- 交易 ----------
CREATE TABLE coupons (
    coupon_id      INTEGER PRIMARY KEY,
    code           TEXT NOT NULL UNIQUE,
    type           TEXT NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    min_amount     DECIMAL(12,2) NOT NULL DEFAULT 0,
    valid_from     TEXT NOT NULL,
    valid_until    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    status          TEXT NOT NULL DEFAULT 'pending',
    total_amount    DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    pay_amount      DECIMAL(12,2) NOT NULL,
    coupon_id       INTEGER REFERENCES coupons(coupon_id),
    region_id       INTEGER REFERENCES regions(region_id),
    created_at      TEXT NOT NULL,
    paid_at         TEXT
);

CREATE TABLE order_items (
    item_id    INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal   DECIMAL(12,2) NOT NULL
);

CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    method     TEXT NOT NULL,
    amount     DECIMAL(12,2) NOT NULL,
    status     TEXT NOT NULL DEFAULT 'success',
    paid_at    TEXT NOT NULL
);

CREATE TABLE refunds (
    refund_id  INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    item_id    INTEGER REFERENCES order_items(item_id),
    amount     DECIMAL(12,2) NOT NULL,
    reason     TEXT,
    status     TEXT NOT NULL DEFAULT 'applied',
    created_at TEXT NOT NULL
);

CREATE TABLE shipments (
    shipment_id  INTEGER PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(order_id),
    carrier_id   INTEGER REFERENCES carriers(carrier_id),
    tracking_no  TEXT,
    status       TEXT NOT NULL DEFAULT 'pending',
    shipped_at   TEXT,
    delivered_at TEXT
);

CREATE TABLE reviews (
    review_id  INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content    TEXT,
    created_at TEXT NOT NULL
);
