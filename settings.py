
#
DEBUG = False

# Zimbra admin
ZIMBRA_ADMIN_URL="https://localhost:7071/service/admin/soap/"
UID = "admin@zimbra."
PASSWD = "somepasswd"
DEFAULT_DOMAIN = "my-domain.com"
PREAUTHKEY = ""


# SMTP Settings
MAILHOST = "my-smpt-domain.com"
FROMADDR  = "some@addr.com"
TOADDRS = ["addr1@some.com", ]
SUBJECT = "The message subject"

# LOGGING
LOG_SETTINGS = {
    'version': 1,
    'disable_existing_loggers': False,
        'handlers': {
        'stream': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
        },
        'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': '/tmp/out1.log',
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 5,
                },
        'file2': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': '/tmp/out2.log',
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 5,
                },
        'smtp': {
            'class': 'logging.handlers.SMTPHandler',
            'level': 'ERROR',
            'formatter': 'standard',
            'mailhost': MAILHOST,
            'fromaddr': FROMADDR,
            'toaddrs': TOADDRS,
            'subject': SUBJECT,
        },
        },
    'formatters': {
        'standard': {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
        'loggers': {
        'Both': {
                'level':'DEBUG',
                'handlers': ['file','stream'],
            'propagate':True,
        },
        'Stream': {
            'level':'WARNING',
            'handlers':['stream'],
            },
        'File': {
            'level':'DEBUG',
            'handlers':['file',],
            },
        'File2': {
            'level':'DEBUG',
            'handlers':['file2',],
            },
        'Mail':{
            'level':'WARNING',
            'handlers':['smtp',],
            },
        },

}
