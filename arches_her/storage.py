from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
import logging
import inspect

logger = logging.getLogger(__name__)


class NonStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_name = self.__class__.__name__

    def hashed_name(self, name, content=None, filename=None):
        """
        Override hashed_name to avoid raising errors when a file is missing.
        """
        method_name = inspect.currentframe().f_code.co_name

        try:
            # Call the original hashed_name method
            return super().hashed_name(name, content, filename)

        except ValueError as e:
            # Log a warning for the missing file and return the original name (no hashing)
            logger.warning(f"{self.class_name}.{method_name} - File not found, skipping hash for {name}: {e}")
            return name  # Return the un-hashed name
        except Exception as e:
            logger.error(f"{self.class_name}.{method_name} - Unexpected error hashing {name}: {e}", exc_info=True)
            return name  # Return the un-hashed name to avoid disruption

    def post_process(self, paths, dry_run=False, **options):
        """
        Override post_process to handle missing files gracefully.
        """
        method_name = inspect.currentframe().f_code.co_name

        try:
            results = super().post_process(paths, dry_run, **options)
            for result in results:
                yield result
        except ValueError as e:
            logger.warning(f"{self.class_name}.{method_name} - Skipping missing file during post-processing: {e}")
            # Continue processing despite missing files
        except Exception as e:
            logger.error(f"{self.class_name}.{method_name} - Unexpected error during post-processing: {e}", exc_info=True)
