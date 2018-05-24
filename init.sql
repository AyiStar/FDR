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
    person_ID CHAR(36),
    weibo_name VARCHAR(255),
    weibo_uid VARCHAR(31),
    last_post_time DATETIME DEFAULT NULL,
    PRIMARY KEY (person_ID)
) DEFAULT CHARSET=utf8;

CREATE TABLE Weibos(
    weibo_ID bigint(12) NOT NULL AUTO_INCREMENT,
    user_ID VARCHAR(31) DEFAULT NULL,
    user_name varchar(255) DEFAULT NULL,
    post_time varchar(255) DEFAULT NULL,
    tweet text CHARACTER SET utf8mb4,
    forwarding text CHARACTER SET utf8mb4,
    num_likes bigint(20) DEFAULT NULL,
    num_forwardings bigint(20) DEFAULT NULL,
    num_comments bigint(20) DEFAULT NULL,
    PRIMARY KEY (weibo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;