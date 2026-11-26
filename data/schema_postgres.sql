-- =============================================================================
-- DataAgent 电商样例库 Schema  (PostgreSQL 16)
-- 15 张表：10 张核心交易表 + 5 张支持表（维度/EAV）
--
-- 设计原则（对 Text-to-SQL 友好）：
--   1. 外键命名统一 xxx_id（user_id/order_id/product_id），LLM 靠命名就能猜对 join
--   2. 每张表/关键列都有 COMMENT —— 这是 W2 schema 检索的 embedding 素材，
--      没有 COMMENT 的表对检索器是"隐形"的
--   3. 适度反规范化：orders 冗余金额字段，单表聚合题不用 join；
--      明细保留在 order_items（规范化），多表 join 题有得做
--   4. 时间列全覆盖，统一 TIMESTAMPTZ，支撑时间窗口题
--   5. 金额用 NUMERIC（不用 FLOAT），状态用受控枚举值
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;   -- W2 schema 检索用 pgvector

-- ============================================================
-- 支持表（维度 + EAV）
-- ============================================================

-- 地区维度：省份 + 城市
CREATE TABLE regions (
    region_id BIGSERIAL PRIMARY KEY,
    province  VARCHAR(32) NOT NULL,
    city      VARCHAR(64) NOT NULL,
    UNIQUE (province, city)
);
COMMENT ON TABLE regions IS '地区维度：省份+城市，用于收货地址与地域分析';

-- 品牌维度
CREATE TABLE brands (
    brand_id     BIGSERIAL PRIMARY KEY,
    name         VARCHAR(64) NOT NULL UNIQUE,
    founded_year SMALLINT,
    country      VARCHAR(32)
);
COMMENT ON TABLE brands IS '品牌维度';

-- 供应商维度
CREATE TABLE suppliers (
    supplier_id   BIGSERIAL PRIMARY KEY,
    name          VARCHAR(64) NOT NULL UNIQUE,
    region_id     BIGINT REFERENCES regions(region_id),
    contact_email VARCHAR(128)
);
COMMENT ON TABLE suppliers IS '供应商维度';

-- 商品分类（parent_id 自关联，支持父子层级）
CREATE TABLE categories (
    category_id BIGSERIAL PRIMARY KEY,
    name        VARCHAR(64) NOT NULL UNIQUE,
    parent_id   BIGINT REFERENCES categories(category_id)
);
COMMENT ON TABLE categories IS '商品分类，parent_id 自关联支持父子层级（如 电子 > 手机）';

-- 物流公司维度
CREATE TABLE carriers (
    carrier_id BIGSERIAL PRIMARY KEY,
    name       VARCHAR(32) NOT NULL UNIQUE,
    type       VARCHAR(16)                -- express / standard
);
COMMENT ON TABLE carriers IS '物流公司维度（顺丰/圆通/京东物流...）';

-- ============================================================
-- 用户 / 商品
-- ============================================================

CREATE TABLE users (
    user_id       BIGSERIAL PRIMARY KEY,
    name          VARCHAR(64) NOT NULL,
    email         VARCHAR(128) NOT NULL UNIQUE,
    phone         VARCHAR(20),
    region_id     BIGINT REFERENCES regions(region_id),
    gender        VARCHAR(8),             -- male / female
    age           SMALLINT,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status        VARCHAR(16) NOT NULL DEFAULT 'active'
);
COMMENT ON TABLE users IS '用户表';

CREATE TABLE products (
    product_id  BIGSERIAL PRIMARY KEY,
    name        VARCHAR(128) NOT NULL,
    category_id BIGINT NOT NULL REFERENCES categories(category_id),
    brand_id    BIGINT REFERENCES brands(brand_id),
    supplier_id BIGINT REFERENCES suppliers(supplier_id),
    price       NUMERIC(10,2) NOT NULL,
    cost        NUMERIC(10,2) NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    status      VARCHAR(16) NOT NULL DEFAULT 'on_sale',  -- on_sale / off_shelf
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE products IS '商品表（SKU 粒度）';
COMMENT ON COLUMN products.price IS '售价（元）';
COMMENT ON COLUMN products.cost IS '成本价（元），用于毛利 = price - cost 计算';

-- 商品属性 EAV（颜色/尺码/材质等）
CREATE TABLE product_attributes (
    attribute_id BIGSERIAL PRIMARY KEY,
    product_id   BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    attr_name    VARCHAR(32) NOT NULL,
    attr_value   VARCHAR(64) NOT NULL
);
COMMENT ON TABLE product_attributes IS '商品属性 EAV 表（颜色/尺码/材质等）';

-- ============================================================
-- 交易
-- ============================================================

CREATE TABLE coupons (
    coupon_id      BIGSERIAL PRIMARY KEY,
    code           VARCHAR(32) NOT NULL UNIQUE,
    type           VARCHAR(16) NOT NULL,               -- fixed / percent
    discount_value NUMERIC(10,2) NOT NULL,
    min_amount     NUMERIC(12,2) NOT NULL DEFAULT 0,
    valid_from     TIMESTAMPTZ NOT NULL,
    valid_until    TIMESTAMPTZ NOT NULL,
    status         VARCHAR(16) NOT NULL DEFAULT 'active'
);
COMMENT ON TABLE coupons IS '优惠券定义表';
COMMENT ON COLUMN coupons.discount_value IS 'fixed 为立减金额(元)；percent 为折扣率(0~1)';
COMMENT ON COLUMN coupons.min_amount IS '使用门槛：订单满多少元可用';

CREATE TABLE orders (
    order_id        BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(user_id),
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending/paid/shipped/delivered/cancelled
    total_amount    NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    pay_amount      NUMERIC(12,2) NOT NULL,
    coupon_id       BIGINT REFERENCES coupons(coupon_id),
    region_id       BIGINT REFERENCES regions(region_id),
    created_at      TIMESTAMPTZ NOT NULL,
    paid_at         TIMESTAMPTZ
);
COMMENT ON TABLE orders IS '订单主表';
COMMENT ON COLUMN orders.total_amount IS '商品总额（优惠前）';
COMMENT ON COLUMN orders.pay_amount IS '实付金额 = total_amount - discount_amount';
COMMENT ON COLUMN orders.region_id IS '收货地区（下单时快照）';

CREATE TABLE order_items (
    item_id    BIGSERIAL PRIMARY KEY,
    order_id   BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    subtotal   NUMERIC(12,2) NOT NULL
);
COMMENT ON TABLE order_items IS '订单明细表';
COMMENT ON COLUMN order_items.unit_price IS '下单时单价（快照，防止商品改价影响历史订单）';

CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    order_id   BIGINT NOT NULL REFERENCES orders(order_id),
    method     VARCHAR(16) NOT NULL,                   -- alipay/wechat/card/cod
    amount     NUMERIC(12,2) NOT NULL,
    status     VARCHAR(16) NOT NULL DEFAULT 'success',
    paid_at    TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE payments IS '支付流水表';

CREATE TABLE refunds (
    refund_id  BIGSERIAL PRIMARY KEY,
    order_id   BIGINT NOT NULL REFERENCES orders(order_id),
    item_id    BIGINT REFERENCES order_items(item_id),
    amount     NUMERIC(12,2) NOT NULL,
    reason     VARCHAR(128),
    status     VARCHAR(16) NOT NULL DEFAULT 'applied',  -- applied/approved/rejected/refunded
    created_at TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE refunds IS '退款表';

CREATE TABLE shipments (
    shipment_id  BIGSERIAL PRIMARY KEY,
    order_id     BIGINT NOT NULL REFERENCES orders(order_id),
    carrier_id   BIGINT REFERENCES carriers(carrier_id),
    tracking_no  VARCHAR(64),
    status       VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending/shipped/delivered
    shipped_at   TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ
);
COMMENT ON TABLE shipments IS '物流/发货表';

CREATE TABLE reviews (
    review_id  BIGSERIAL PRIMARY KEY,
    order_id   BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    user_id    BIGINT NOT NULL REFERENCES users(user_id),
    rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content    TEXT,
    created_at TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE reviews IS '商品评价表';
COMMENT ON COLUMN reviews.rating IS '评分 1~5 星';

-- ============================================================
-- 索引（建在评测查询会打到的列上：外键 + 时间列）
-- ============================================================
CREATE INDEX idx_orders_user       ON orders(user_id);
CREATE INDEX idx_orders_created    ON orders(created_at);
CREATE INDEX idx_orders_status     ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_prod  ON order_items(product_id);
CREATE INDEX idx_payments_order    ON payments(order_id);
CREATE INDEX idx_payments_paid     ON payments(paid_at);
CREATE INDEX idx_refunds_order     ON refunds(order_id);
CREATE INDEX idx_shipments_order   ON shipments(order_id);
CREATE INDEX idx_reviews_product   ON reviews(product_id);
CREATE INDEX idx_reviews_rating    ON reviews(rating);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand    ON products(brand_id);
