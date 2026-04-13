-- Keycloak 用 DB（PERSISTENCE_PROFILE=production 時の KC_DB=postgres で使用）
-- 初回ボリューム初期化時のみ実行される
CREATE USER keycloak WITH PASSWORD 'keycloak_dev_password';
CREATE DATABASE keycloak OWNER keycloak;
