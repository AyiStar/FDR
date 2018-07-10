DROP DATABASE IF EXISTS FDR;
CREATE DATABASE IF NOT EXISTS FDR;

use FDR;

CREATE TABLE IF NOT EXISTS Persons(
    person_ID CHAR(36),
    name VARCHAR(20) DEFAULT NULL,
    last_meet_time DATETIME DEFAULT NULL,
    PRIMARY KEY (person_ID)
) DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS Meets(
    meet_ID BIGINT UNSIGNED AUTO_INCREMENT,
    meet_time DATETIME,
    meet_place VARCHAR(255),
    person_ID CHAR(36) NOT NULL,
    PRIMARY KEY (meet_ID)
)DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS Vectors(
    vector_ID BIGINT UNSIGNED AUTO_INCREMENT,
    vector BLOB NOT NULL,
    person_ID CHAR(36) NOT NULL,
    PRIMARY KEY (vector_ID)
) DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS WeiboAccounts(
    weibo_account_ID BIGINT UNSIGNED AUTO_INCREMENT,
    person_ID CHAR(36) NOT NULL,
    weibo_name VARCHAR(255) NOT NULL,
    weibo_uid VARCHAR(31) NOT NULL,
    last_post_time DATETIME DEFAULT NULL,
    PRIMARY KEY (weibo_account_ID)
) DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS Weibos(
    weibo_ID bigint NOT NULL AUTO_INCREMENT,
    user_ID VARCHAR(31) DEFAULT NULL,
    user_name VARCHAR(255) DEFAULT NULL,
    post_time VARCHAR(255) DEFAULT NULL,
    tweet text CHARACTER SET utf8mb4,
    forwarding text CHARACTER SET utf8mb4,
    num_likes bigint(20) DEFAULT NULL,
    num_forwardings bigint(20) DEFAULT NULL,
    num_comments bigint(20) DEFAULT NULL,
    PRIMARY KEY (weibo_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS Relations(
    relation_ID bigint NOT NULL AUTO_INCREMENT,
    person1_ID CHAR(36) NOT NULL,
    person2_ID CHAR(36) NOT NULL,
    relation_type VARCHAR(31) NOT NULL,
    PRIMARY KEY (relation_ID)
)DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS WeiboHotWords(
    weibo_hot_word_ID bigint NOT NULL AUTO_INCREMENT,
    weibo_uid VARCHAR(31) NOT NULL,
    hot_word VARCHAR(31) NOT NULL,
    frequency int UNSIGNED NOT NULL,
    description text CHARACTER SET utf8mb4,
    PRIMARY KEY (weibo_hot_word_ID)
)DEFAULT CHARSET=utf8;