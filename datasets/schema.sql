-- Схема учебного маркетплейса.
-- Намеренно только первичные ключи, CHECK и UNIQUE: вторичных индексов нет —
-- их ты будешь проектировать сам в уроке 04. Внешние ключи вешаются после загрузки
-- (см. constraints.sql) — так быстрее, и это стандартный приём массовой загрузки.

DROP TABLE IF EXISTS events, reviews, payments, order_items, orders,
                     products, sellers, categories, users, _meta CASCADE;

CREATE TABLE _meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);

CREATE TABLE users (
    id           bigint PRIMARY KEY,
    email        text        NOT NULL UNIQUE,
    full_name    text        NOT NULL,
    country      char(2)     NOT NULL,
    city         text,                       -- NULL: пользователь не указал город
    referred_by  bigint,                     -- кто пригласил (дерево рефералов)
    created_at   timestamptz NOT NULL
);

CREATE TABLE categories (
    id         int  PRIMARY KEY,
    name       text NOT NULL,
    parent_id  int                           -- NULL у корневых категорий
);

CREATE TABLE sellers (
    id          bigint PRIMARY KEY,
    name        text        NOT NULL,
    country     char(2)     NOT NULL,
    created_at  timestamptz NOT NULL
);

CREATE TABLE products (
    id           bigint PRIMARY KEY,
    seller_id    bigint        NOT NULL,
    category_id  int           NOT NULL,
    name         text          NOT NULL,
    price        numeric(12,2) NOT NULL CHECK (price > 0),
    is_active    boolean       NOT NULL,
    created_at   timestamptz   NOT NULL
);

CREATE TABLE orders (
    id                bigint PRIMARY KEY,
    user_id           bigint      NOT NULL,
    status            text        NOT NULL CHECK (status IN
                        ('created','paid','shipped','delivered','cancelled','refunded')),
    shipping_country  char(2)     NOT NULL,
    promo_code        text,                  -- NULL: без промокода
    created_at        timestamptz NOT NULL
);

CREATE TABLE order_items (
    order_id    bigint        NOT NULL,
    product_id  bigint        NOT NULL,
    quantity    int           NOT NULL CHECK (quantity > 0),
    unit_price  numeric(12,2) NOT NULL CHECK (unit_price > 0),  -- цена на момент покупки
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE payments (
    id          bigint PRIMARY KEY,
    order_id    bigint        NOT NULL,
    method      text          NOT NULL CHECK (method IN ('card','sbp','wallet')),
    status      text          NOT NULL CHECK (status IN ('succeeded','failed','refunded')),
    amount      numeric(12,2) NOT NULL CHECK (amount > 0),
    created_at  timestamptz   NOT NULL
);

CREATE TABLE reviews (
    id          bigint PRIMARY KEY,
    user_id     bigint      NOT NULL,
    product_id  bigint      NOT NULL,
    rating      smallint    NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body        text,                        -- NULL: оценка без текста
    created_at  timestamptz NOT NULL,
    UNIQUE (user_id, product_id)
);

CREATE TABLE events (
    id          bigint PRIMARY KEY,
    session_id  bigint      NOT NULL,
    user_id     bigint,                      -- NULL: анонимный посетитель
    event_type  text        NOT NULL CHECK (event_type IN
                  ('view','add_to_cart','checkout','purchase')),
    product_id  bigint,                      -- NULL у checkout
    created_at  timestamptz NOT NULL
);
