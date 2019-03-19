export KEYCLOAK_URL=keycloak.foo.com
export KEYCLOAK_REALM=bar
export SMTP_HOST=smtp.foo.com
export SMTP_PORT=587
export SMTP_SENDER=sender@foo.com
export SMTP_RECEIVER=receiver@bar.com
export SMTP_PASSWORD=superSecretPassword
export KEYCLOAK_USERNAME=admin
export KEYCLOAK_PASSWORD=AnotherSuperSecretPassword

/home/$USER/miniconda3/envs/keycloak-admin/bin/python notifier.py