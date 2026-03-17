show databases;
use defaultdb;

create table users(
id int auto_increment primary key,
name varchar(50),
roll varchar(14) unique not null,
password varchar(256) null,
section varchar(10) null,
role enum('user', 'admin') default 'user',
created_at varchar(17) not null,
size_per_file BIGINT default 81920,
max_size BIGINT default 1048576,
last_login varchar(20) null,
status enum('active', 'block', 'deactive', 'requested') default 'deactive'
);



CREATE TABLE stored_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
	user_id int not null,
    file_name VARCHAR(255) NOT NULL,
    file_ext VARCHAR(20) NOT NULL,
    file_size BIGINT UNSIGNED NOT NULL,
    file_data MEDIUMBLOB NOT NULL,
    subject enum('DAA', 'MA', 'PPML'),
    exp_number INT NOT NULL,
    is_public enum('yes', 'no') default 'no',
	uploaded_at VARCHAR(20) NOT NULL,
    status enum('active', 'delete') default 'active',
    FOREIGN KEY (user_id)
	REFERENCES users(id) 
	ON DELETE CASCADE
    ON UPDATE CASCADE
);

drop table stored_files;
drop table users;

select * from users;
select * from stored_files;

update users set status='active' WHERE id = 10;
update users set role='admin' WHERE id = 10;

BEGIN;
DELETE FROM users WHERE id = 1;
COMMIT;
ROLLBACK;



SET SQL_SAFE_UPDATES = 0;
SET SQL_SAFE_UPDATES = 1;