ALTER TABLE users       ADD FOREIGN KEY (referred_by) REFERENCES users (id);
ALTER TABLE categories  ADD FOREIGN KEY (parent_id)   REFERENCES categories (id);
ALTER TABLE products    ADD FOREIGN KEY (seller_id)   REFERENCES sellers (id);
ALTER TABLE products    ADD FOREIGN KEY (category_id) REFERENCES categories (id);
ALTER TABLE orders      ADD FOREIGN KEY (user_id)     REFERENCES users (id);
ALTER TABLE order_items ADD FOREIGN KEY (order_id)    REFERENCES orders (id);
ALTER TABLE order_items ADD FOREIGN KEY (product_id)  REFERENCES products (id);
ALTER TABLE payments    ADD FOREIGN KEY (order_id)    REFERENCES orders (id);
ALTER TABLE reviews     ADD FOREIGN KEY (user_id)     REFERENCES users (id);
ALTER TABLE reviews     ADD FOREIGN KEY (product_id)  REFERENCES products (id);
ALTER TABLE events      ADD FOREIGN KEY (user_id)     REFERENCES users (id);
ALTER TABLE events      ADD FOREIGN KEY (product_id)  REFERENCES products (id);

ANALYZE;
