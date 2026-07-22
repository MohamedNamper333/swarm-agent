CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    published INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
INSERT INTO users (id, username, email) VALUES (1, 'alice', 'alice@example.com');
INSERT INTO users (id, username, email) VALUES (2, 'bob', 'bob@example.com');
INSERT INTO posts (id, user_id, title, body, published) VALUES (1, 1, 'Hello World', 'First post', 1);
INSERT INTO posts (id, user_id, title, body, published) VALUES (2, 1, 'Draft Post', 'Work in progress', 0);
INSERT INTO posts (id, user_id, title, body, published) VALUES (3, 2, 'Second Post', 'Bob here', 1);
INSERT INTO tags (id, name) VALUES (1, 'tech');
INSERT INTO tags (id, name) VALUES (2, 'personal');
INSERT INTO post_tags (post_id, tag_id) VALUES (1, 1);
INSERT INTO post_tags (post_id, tag_id) VALUES (2, 2);
INSERT INTO post_tags (post_id, tag_id) VALUES (3, 1);
INSERT INTO post_tags (post_id, tag_id) VALUES (3, 2);
