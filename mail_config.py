# mail_config.py

MAILGUN_SMTP_SERVER = "smtp.mailgun.org"
MAILGUN_SMTP_PORT = 587
MAILGUN_SMTP_LOGIN = "johnnymonitor.mailgun.org@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
MAILGUN_SMTP_PASSWORD = "99Pushups%"

MAILGUN_DOMAIN = MAILGUN_SMTP_LOGIN.split("@", 1)[1]
FROM_EMAIL = f"alerts@{MAILGUN_DOMAIN}"
TO_EMAILS = ["johnny.monitor@gmx.com"]

MAILGUN_CONFIG = {
    "server": MAILGUN_SMTP_SERVER,
    "port": MAILGUN_SMTP_PORT,
    "login": MAILGUN_SMTP_LOGIN,
    "password": MAILGUN_SMTP_PASSWORD,
    "from_email": FROM_EMAIL,
    "to_emails": TO_EMAILS,
}
