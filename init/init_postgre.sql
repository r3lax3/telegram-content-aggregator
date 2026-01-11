CREATE USER scrapper_user WITH ENCRYPTED PASSWORD 'strong_password';
CREATE DATABASE scrapper_db OWNER scrapper_user;
GRANT ALL PRIVILEGES ON DATABASE scrapper_db TO scrapper_user;

CREATE USER bot_user WITH ENCRYPTED PASSWORD 'strong_password';
CREATE DATABASE bot_db OWNER bot_user;
GRANT ALL PRIVILEGES ON DATABASE bot_db TO bot_user;
