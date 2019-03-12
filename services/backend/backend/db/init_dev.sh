#!/bin/bash
set -e 

psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "pragyaam_dev" <<-EOSQL
    CREATE EXTENSION dblink;

    CREATE TABLE "WpZl7jb" (
      id int NOT NULL,
      userid varchar(500) DEFAULT NULL,
      uploaded_time timestamp(0) DEFAULT NULL,
      text text DEFAULT NULL,
      text_required_check text DEFAULT NULL,
      text_validation_check text DEFAULT NULL,
      image_check varchar(250) DEFAULT NULL,
      phone_check int DEFAULT NULL,
      email_text_check varchar(150) DEFAULT NULL,
      number_check int DEFAULT NULL,
      dropdown varchar(200) DEFAULT NULL,
      date_check date DEFAULT NULL,
      dropdown_2 varchar(200) DEFAULT NULL,
      date_checking_column date DEFAULT NULL
    ) ;

    CREATE TABLE "T0UljJy" (
      id int NOT NULL,
      userid varchar(500) DEFAULT NULL,
      uploaded_time timestamp(0) DEFAULT NULL,
      text text DEFAULT NULL,
      text_check text DEFAULT NULL,
      text_length_check text DEFAULT NULL,
      number int DEFAULT NULL,
      number_check int DEFAULT NULL,
      number_value_check int DEFAULT NULL,
      phone int DEFAULT NULL,
      phone_check int DEFAULT NULL,
      email varchar(150) DEFAULT NULL,
      email_check varchar(150) DEFAULT NULL,
      dropdown varchar(200) DEFAULT NULL,
      dropdown_check varchar(200) DEFAULT NULL,
      link_to_another varchar(200) DEFAULT NULL,
      another_column_check varchar(200) DEFAULT NULL
    ) ;

    INSERT INTO "WpZl7jb" (id, userid, uploaded_time, text, text_required_check, text_validation_check, image_check, phone_check, email_text_check, number_check, dropdown, date_check, dropdown_2, date_checking_column) VALUES
    (1, 'Testing Product', '2018-12-10 15:51:43', 'text', 'Required', 'Validation', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (2, 'Testing Product', '2018-12-10 15:55:59', 'Text', 'adwe', 'weqwe', 'weqw', 12421, 'asdw@gmail.com', 12, '1', NULL, NULL, NULL),
    (3, 'Testing Product', '2018-12-10 16:55:50', 'Tect', 'asjdi', 'awjd', 'wajd', 90, 'san@gmail.com', 12, '1', NULL, NULL, NULL),
    (4, 'Testing Product', '2018-12-10 19:33:07', 'weqw', 'wqeqw', 'qweqwe', 'qwe', 0, 'san@gmail.com', 12, '1', '2018-12-12', NULL, '2018-12-12'),
    (5, 'Testing Product', '2018-12-10 19:33:45', 'weqw', 'wqeqw', 'qweqwe', 'qwe', 0, 'san@gmail.com', 12, '1', '2018-12-12', NULL, '2018-12-12'),
    (6, 'Testing Product', '2018-12-10 19:34:01', 'weqw', 'wqeqw', 'qweqwe', 'qwe', 0, 'san@gmail.com', 12, '1', '2018-12-12', NULL, '2018-12-12'),
    (7, 'Testing Product', '2018-12-10 19:52:36', 'weqw', 'wqeqw', 'qweqwe', 'qwe', 90, 'san@gmail.com', 12, '1', '2018-12-12', NULL, '2018-12-12'),
    (8, 'Testing Product', '2018-12-10 19:53:11', 'weqw', 'wqeqw', 'qweqwe', 'qwe', 90, 'san@gmail.com', 12, '1', '2018-12-12', NULL, '2018-12-12');

    INSERT INTO "T0UljJy" (id, userid, uploaded_time, text, text_check, text_length_check, number, number_check, number_value_check, phone, phone_check, email, email_check, dropdown, dropdown_check, link_to_another, another_column_check) VALUES
    (1, 'Testing Product', '2018-12-06 11:30:11', NULL, 'as', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (2, 'Testing Product', '2018-12-06 11:30:20', 'Snagethaa', 'Sangeetha', 'Sangeetha', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (3, 'Testing Product', '2018-12-06 11:37:05', 'Sangeetha', 'Sangeetha', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (4, 'Testing Product', '2018-12-06 12:47:42', '', 'Check', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (5, 'Testing Product', '2018-12-06 12:49:18', NULL, 'Check', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),EOSQLEOSQL
    (6, 'Testing Product', '2018-12-06 12:50:06', NULL, 'Check', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (7, 'Testing Product', '2018-12-06 12:51:33', NULL, 'aqs', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (8, 'Testing Product', '2018-12-06 12:51:39', NULL, 'aqs', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (9, 'Testing Product', '2018-12-06 13:36:18', NULL, 'aqs', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (10, 'Testing Product', '2018-12-06 13:37:08', NULL, 'Nothing', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (11, 'Testing Product', '2018-12-06 13:38:10', NULL, 'Nothing', NULL, NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (12, 'Testing Product', '2018-12-06 13:38:28', NULL, 'Nothing', NULL, NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (13, 'Testing Product', '2018-12-06 13:39:10', NULL, 'Nothing', NULL, NULL, 1, 13, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (14, 'Testing Product', '2018-12-06 13:42:29', NULL, 'qwas', NULL, NULL, 12, NULL, 1, 123, NULL, NULL, NULL, NULL, NULL, NULL),
    (15, 'Testing Product', '2018-12-06 13:44:14', NULL, 'qwqas', NULL, NULL, 12, 12, NULL, 12, NULL, 'sa', NULL, NULL, NULL, NULL),
    (16, 'Testing Product', '2018-12-06 13:45:07', NULL, 'qwqas', NULL, NULL, 12, 12, NULL, 12, NULL, 'sa', NULL, NULL, NULL, NULL),
    (17, 'Testing Product', '2018-12-06 13:45:54', NULL, 'qwqas', NULL, NULL, 12, 12, NULL, 12, NULL, 'sa', NULL, NULL, NULL, NULL),
    (18, 'Testing Product', '2018-12-06 13:46:30', NULL, 'qwqas', NULL, NULL, 12, 12, NULL, 12, NULL, 'sa', NULL, NULL, NULL, NULL),
    (19, 'Testing Product', '2018-12-06 13:52:35', NULL, 'qwqas', NULL, NULL, 12, 12, NULL, 12, NULL, 'sangeetha@gmail.com', NULL, NULL, NULL, NULL),
    (20, 'Testing Product', '2018-12-06 17:51:00', NULL, '12', NULL, NULL, 12, NULL, NULL, 12, NULL, 'javid@gmail.com', NULL, '2', NULL, NULL),
    (21, 'Testing Product', '2018-12-06 17:56:16', NULL, '12', NULL, NULL, 12, NULL, NULL, 12, NULL, 'javid@gmail.com', '12', '2', NULL, NULL),
    (22, 'Testing Product', '2018-12-06 18:45:23', NULL, '12', NULL, NULL, 12, NULL, NULL, 12, NULL, 'sang@gmail.com', NULL, '2', NULL, NULL),
    (23, 'Testing Product', '2018-12-06 18:46:08', NULL, '12', NULL, NULL, 12, NULL, NULL, 12, NULL, 'sang@gmail.com', NULL, '2', NULL, NULL);
EOSQL