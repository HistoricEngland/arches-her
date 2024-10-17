from arches.setup import get_version
import os

__software_version__ = None
software_version = os.getenv("KEYSTONE-SOFTWARE-VERSION", None)

if software_version:
    software_version_tuple = tuple(item.strip()
                                   for item in software_version.split(','))
    __software_version__ = get_version(software_version_tuple)
