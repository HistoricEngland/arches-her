from django.core.management.base import BaseCommand
from arches.app.models.system_settings import settings
from pathlib import Path
from docx import Document
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("operation", nargs="?")

    def handle(self, *args, **options):
        if options["operation"] == "fix_style_runs":
            self.fix_style_runs()

    def fix_style_runs(self):
        start_folder = Path(settings.ROOT_DIR).parent.parent
        docx_files = list(start_folder.glob("**/docx/*.docx"))
        for filename in docx_files:
            document = self.open_document(filename)
            if not document:
                continue

            save_required = self.process_paragraphs(document)
            self.save_document(document, filename, save_required)

    def open_document(self, filename):
        try:
            return Document(filename)
        except Exception as e:
            message = f"Error opening {filename}: {e}"
            print(message)
            logger.error(message)
            return None

    def process_paragraphs(self, document):
        save_required = False

        for p in document.paragraphs:
            run_text, start_pos, end_pos = self.collect_run_text(p)
            if start_pos + end_pos > 0:
                save_required |= self.replace_runs(p, run_text, start_pos, end_pos)

        return save_required

    def collect_run_text(self, paragraph):
        run_text = ""
        capture = False
        start_pos = end_pos = -1

        for i, r in enumerate(paragraph.runs):
            text = r.text
            if text.startswith("<") and text.endswith(">"):
                break
            if "<" in text:
                capture = True
                start_pos = i
            if capture:
                run_text += text
            if ">" in text:
                capture = False
                end_pos = i

        return run_text, start_pos, end_pos

    def replace_runs(self, paragraph, run_text, start_pos, end_pos):
        save_required = False
        for i, r in enumerate(paragraph.runs):
            if i < start_pos:
                continue
            if i == start_pos:
                if r.text != run_text:
                    r.text = run_text
                    save_required = True
            elif i <= end_pos:
                r.text = ""
                save_required = True

        return save_required

    def save_document(self, document, filename, save_required):
        if save_required:
            try:
                document.save(filename)
                message = f"DOCX style runs fixed in {filename}"
                print(message)
                logger.info(message)
            except Exception as e:
                message = f"Error saving {filename}: {e}"
                print(message)
                logger.error(message)
        else:
            message = f"No broken DOCX style runs found in {filename}"
            print(message)
            logger.info(message)
