import os
from django.core.exceptions import ImproperlyConfigured
import ast
import requests
import sys


def get_env_variable(var_name):
    msg = "Set the %s environment variable"
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = msg % var_name
        raise ImproperlyConfigured(error_msg)


def get_optional_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        return None


# options are either "PROD" or "DEV" (installing with Dev mode set gets you extra dependencies)
MODE = get_env_variable("DJANGO_MODE")

DEBUG = ast.literal_eval(get_env_variable("DJANGO_DEBUG"))

COUCHDB_URL = "http://{}:{}@{}:{}".format(
    get_env_variable("COUCHDB_USER"), get_env_variable("COUCHDB_PASS"), get_env_variable("COUCHDB_HOST"), get_env_variable("COUCHDB_PORT")
)  # defaults to localhost:5984

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": get_env_variable("PGDBNAME"),
        "USER": get_env_variable("PGUSERNAME"),
        "PASSWORD": get_env_variable("PGPASSWORD"),
        "HOST": get_env_variable("PGHOST"),
        "PORT": get_env_variable("PGPORT"),
        "POSTGIS_TEMPLATE": "template_postgis",
    }
}

CELERY_BROKER_URL = "amqp://{}:{}@rabbitmq_aher".format(
    get_env_variable("RABBITMQ_USER"), get_env_variable("RABBITMQ_PASS")
)  # RabbitMQ --> "amqp://guest:guest@localhost",  Redis --> "redis://localhost:6379/0"

# CANTALOUPE_HTTP_ENDPOINT = "http://{}:{}".format(get_env_variable("CANTALOUPE_HOST"), get_env_variable("CANTALOUPE_PORT"))
ELASTICSEARCH_HTTP_PORT = ast.literal_eval(get_env_variable("ESPORT"))
ELASTICSEARCH_HOSTS = [{"scheme": "http", "host": get_env_variable("ESHOST"), "port": ELASTICSEARCH_HTTP_PORT}] # DEV

USER_ELASTICSEARCH_PREFIX = get_optional_env_variable("ELASTICSEARCH_PREFIX")
if USER_ELASTICSEARCH_PREFIX:
    ELASTICSEARCH_PREFIX = USER_ELASTICSEARCH_PREFIX

# Elasticsearch connection settings for using Elastic Cloud
# Requires following environment variables:
# ELASTIC_CLOUD_ID: deployment_name:deployment_GUID
# ELASTIC_USER: the user for authentication credentials
# ELASTIC_PASSWORD: the password for authenticaion credentials
#
# ELASTICSEARCH_CONNECTION_OPTIONS = {
#    "cloud_id": get_env_variable("ELASTIC_CLOUD_ID"),
#    "ca_certs": False,
#    "verify_certs": False,
#    "ssl_show_warn": False,
#    "timeout": 60,
#    "http_auth": (get_env_variable("ELASTIC_USER"), get_env_variable("ELASTIC_PASSWORD")),
# }

ALLOWED_HOSTS = get_env_variable("DOMAIN_NAMES").split()

USER_SECRET_KEY = get_optional_env_variable("DJANGO_SECRET_KEY")
if USER_SECRET_KEY:
    # Make this unique, and don't share it with anybody.
    SECRET_KEY = USER_SECRET_KEY

STATIC_ROOT = "/static_root"
