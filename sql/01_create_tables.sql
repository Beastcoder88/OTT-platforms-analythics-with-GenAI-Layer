CREATE DATABASE IF NOT EXISTS ott_analytics CHARACTER SET utf8mb4;

USE ott_analytics;

DROP TABLE IF EXISTS viewership;
DROP TABLE IF EXISTS content;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT PRIMARY KEY,
    region VARCHAR(30) NOT NULL,
    preferred_language VARCHAR(20) NOT NULL,
    subscription_tier VARCHAR(20) NOT NULL,
    signup_date DATE NOT NULL,
    cancel_date DATE NULL
);

CREATE TABLE content (
    content_id INT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    genre VARCHAR(40) NOT NULL,
    language VARCHAR(20) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    release_year INT NULL
);

CREATE TABLE viewership (
    view_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    content_id INT NOT NULL,
    watch_date DATE NOT NULL,
    watch_minutes INT NOT NULL,
    device VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (content_id) REFERENCES content(content_id)
);

CREATE INDEX idx_view_date ON viewership(watch_date);