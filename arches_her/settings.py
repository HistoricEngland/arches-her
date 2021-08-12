"""
Django settings for arches_her project.
"""

import os
import arches
import inspect

try:
    from arches.settings import *
except ImportError:
    pass

APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
APP_PATHNAME = "arches-her"
STATICFILES_DIRS = (os.path.join(APP_ROOT, "media"),) + STATICFILES_DIRS

DATATYPE_LOCATIONS.append("arches_her.datatypes")
FUNCTION_LOCATIONS.append("arches_her.functions")
TEMPLATES[0]["DIRS"].append(os.path.join(APP_ROOT, "functions", "templates"))
TEMPLATES[0]["DIRS"].append(os.path.join(APP_ROOT, "widgets", "templates"))
TEMPLATES[0]["DIRS"].insert(0, os.path.join(APP_ROOT, "templates"))
TEMPLATES[0]["OPTIONS"]["context_processors"].append("arches_her.utils.context_processors.project_settings")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "vwo1!nn5s0m)89@pn7^!4a^+_+7mdhk^=&$zrwi(n2lisgi0_w"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ROOT_URLCONF = "arches_her.urls"

# a prefix to append to all elasticsearch indexes, note: must be lower case
ELASTICSEARCH_PREFIX = "arches_her"

SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD = 2000  # The maximum number of instances a user can download from search export without celery
SEARCH_EXPORT_LIMIT = 15000  # The maximum documents ElasticSearch will return in an export - **System Settings**

CELERY_BROKER_URL = "amqp://guest:guest@localhost"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_BACKEND = "django-db"
CELERY_TASK_SERIALIZER = "json"
CELERY_SEARCH_EXPORT_EXPIRES = 60 * 3  # seconds
CELERY_SEARCH_EXPORT_CHECK = 15  # seconds

CELERY_BEAT_SCHEDULE = {
    "delete-expired-search-export": {
        "task": "arches.app.tasks.delete_file",
        "schedule": CELERY_SEARCH_EXPORT_CHECK,
    },
    "notification": {
        "task": "arches.app.tasks.message",
        "schedule": CELERY_SEARCH_EXPORT_CHECK,
        "args": ("Celery Beat is Running",),
    },
}

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": "localhost",
        "NAME": "arches_her",
        "OPTIONS": {},
        "PASSWORD": "postgis",
        "PORT": "5432",
        "POSTGIS_TEMPLATE": "template_postgis",
        "TEST": {"CHARSET": None, "COLLATION": None, "MIRROR": None, "NAME": None},
        "TIME_ZONE": None,
        "USER": "postgres",
    }
}


ALLOWED_HOSTS = []

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(APP_ROOT, "system_settings", "System_Settings.json")
WSGI_APPLICATION = "arches_her.wsgi.application"
STATIC_ROOT = ""

RESOURCE_IMPORT_LOG = os.path.join(APP_ROOT, "logs", "resource_import.log")

# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {"console": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",},},
#     "handlers": {
#         "file": {
#             "level": "WARNING",  # DEBUG, INFO, WARNING, ERROR
#             "class": "logging.FileHandler",
#             "filename": os.path.join(APP_ROOT, "arches.log"),
#             "formatter": "console",
#         },
#         "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "console",},
#     },
#     "loggers": {"arches": {"handlers": ["file", "console"], "level": "DEBUG", "propagate": True}},
# }

############# APPINSIGHTS INTEGRATION USING OPENCENSUS #############

MIDDLEWARE = MIDDLEWARE + [
    "opencensus.ext.django.middleware.OpencensusMiddleware",
]
OPENCENSUS = {
    "TRACE": {
        "SAMPLER": "opencensus.trace.samplers.ProbabilitySampler(rate=1)",
        "EXPORTER": """opencensus.ext.azure.trace_exporter.AzureExporter(
            service_name='arches_her',
        )""",
    }
}
# Add the integrations to use get Postgresql, ElastcSearch requests (httplib) and logging
from opencensus.trace import config_integration

INTEGRATIONS = [
    "postgresql",
    "httplib",
    "logging",
]
config_integration.trace_integrations(INTEGRATIONS)

APPINSIGHTS_KEY = "#{SETTINGS_APPINSIGHTS_KEY}#"  # *** Application Insights key ***

# Set the AppInsights Key as an env variable so it can be used by the logging system
os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = "InstrumentationKey=" + APPINSIGHTS_KEY

LOGGING = {
    "disable_existing_loggers": True,  # False, #<-- if true then make sure that you have a django and py.warnings logger
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "simple": {"format": "[%(asctime)s] %(levelname)s %(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"},
        "verbose": {"format": "[%(asctime)s] %(levelname)s %(message)s [%(name)s.%(funcName)s:%(lineno)d]", "datefmt": "%Y-%m-%d %H:%M:%S"},
        "azure_verbose": {
            "format": "[%(asctime)s] %(levelname)s %(message)s [%(name)s.%(funcName)s:%(lineno)d] traceId=%(traceId)s spanId=%(spanId)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        # "file": { #<-- uncomment if the logging needs to be written to file.
        #    "class": "logging.FileHandler",
        #    "filename": "/arches_her/logs/arches.log",
        #    "level": "DEBUG",
        #    "formatter": 'verbose'
        # },
        "console": {  # writes to the console
            "class": "logging.StreamHandler",
            "level": "INFO",  # <--
            "filters": ["require_debug_true"],  # <-- settings.DEBUG must = True for console to work
            "formatter": "verbose",
        },
        "azure": {  # exports to Azure Monitor. Needs OPENCENSUS elements configured
            "level": "INFO",
            "filters": ["require_debug_false"],  # <-- settings.DEBUG must = False for Azure to receive
            "class": "opencensus.ext.azure.log_exporter.AzureLogHandler",
            "formatter": "azure_verbose",
            "instrumentation_key": APPINSIGHTS_KEY,
        },
    },
    "root": {
        "handlers": [
            "azure",
            "console",
        ],
        "level": "INFO",
    },
    "loggers": {
        "arches": {
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
        },
        "django": {  # <-- must have one django
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
        },
        "django.server": {
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
            "propagate": False,
        },
        "django.requests": {
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
            "propagate": False,
        },
        "py.warnings": {  # <-- replicate default
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
        },
        "": {  # <-- catchall
            "handlers": [
                "azure",
                "console",
            ],
            "level": "INFO",
        },
    },
    "version": 1,
}
###############################################################################

MIDDLEWARE = [
    "arches_her.utils.consultations_middleware.RedirectToConsultations",
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    #'arches.app.utils.middleware.TokenMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "arches.app.utils.middleware.ModifyAuthorizationHeader",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "arches.app.utils.middleware.SetAnonymousUser",
]


# Absolute filesystem path to the directory that will hold user-uploaded files.

MEDIA_ROOT = os.path.join(APP_ROOT)

TILE_CACHE_CONFIG = {
    "name": "Disk",
    "path": os.path.join(APP_ROOT, "tileserver", "cache")
    # to reconfigure to use S3 (recommended for production), use the following
    # template:
    # "name": "S3",
    # "bucket": "<bucket name>",
    # "access": "<access key>",
    # "secret": "<secret key>"
}

CACHES = {
    # 'default': {
    #     'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    #     'LOCATION': os.path.join(APP_ROOT, 'tmp', 'djangocache'),
    #     'OPTIONS': {
    #         'MAX_ENTRIES': 1000
    #     }
    # }
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "127.0.0.1:11211",
    }
}

# Identify the usernames and duration (seconds) for which you want to cache the time wheel
CACHE_BY_USER = {"anonymous": 3600 * 24}

MOBILE_OAUTH_CLIENT_ID = ""
MOBILE_DEFAULT_ONLINE_BASEMAP = {"default": "mapbox://styles/mapbox/streets-v9"}

APP_TITLE = "Arches-HER"
COPYRIGHT_TEXT = "All Rights Reserved."
COPYRIGHT_YEAR = "2020"

try:
    from .package_settings import *
except ImportError:
    pass

try:
    from .settings_local import *
except ImportError:
    pass
