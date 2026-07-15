#!/usr/bin/env python3
"""
Validation Error Analyzer for HAPI Validation Results

Analyzes validation results and creates a summary report of validation errors,
normalizing field names and error messages by removing numeric array indices.
"""

import json
import re
import logging
from collections import defaultdict
from typing import Dict, List
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationErrorAnalyzer:
    def __init__(self):
        self.field_errors = defaultdict(int)
        self.error_messages = defaultdict(int)
        self.field_error_combinations = defaultdict(int)
        self.total_errors = 0
        self.total_invalid_records = 0
        self.examples = defaultdict(list)

        self.total_records_processed = 0
        self.unique_failed_resources = set()
        self.monument_sources_only_resources = set()
        self.monument_sources_required_pattern = (
            "The record.monument sources field is required.||RequiredUnless"
        )

        self._field_name_cache = {}
        self._error_message_cache = {}
        self._examples_max_size = 5
        self._cache_max_size = 10000

        self._array_index_pattern = re.compile(r"\.\d+")
        self._array_index_msg_pattern = re.compile(r"(\w+)\.\d+\b")

    def normalize_field_name(self, field_name: str) -> str:
        if field_name not in self._field_name_cache:
            if len(self._field_name_cache) >= self._cache_max_size:
                self._field_name_cache.clear()
            self._field_name_cache[field_name] = self._array_index_pattern.sub(
                "", field_name)
        return self._field_name_cache[field_name]

    def normalize_error_message(self, message: str) -> str:
        if message not in self._error_message_cache:
            if len(self._error_message_cache) >= self._cache_max_size:
                self._error_message_cache.clear()
            normalized = self._array_index_msg_pattern.sub(r"\1", message)
            self._error_message_cache[message] = normalized
        return self._error_message_cache[message]

    def process_error_entry(self, error_entry: Dict) -> None:
        for record_id, field_errors in error_entry.items():
            self.unique_failed_resources.add(record_id)

            if not isinstance(field_errors, dict):
                continue

            is_monument_sources_only = self._is_monument_sources_only_error(
                field_errors)
            if is_monument_sources_only:
                self.monument_sources_only_resources.add(record_id)

            for field_name, error_messages in field_errors.items():
                normalized_field = self.normalize_field_name(field_name)

                for message in error_messages:
                    normalized_message = self.normalize_error_message(message)

                    self.field_errors[normalized_field] += 1
                    self.error_messages[normalized_message] += 1
                    self.field_error_combinations[(
                        normalized_field, normalized_message)] += 1
                    self.total_errors += 1

                    examples_list = self.examples[normalized_message]
                    if len(examples_list) < self._examples_max_size:
                        examples_list.append(
                            {
                                "original_field": field_name,
                                "original_message": message,
                                "record_id": record_id,
                            }
                        )

    def _is_monument_sources_only_error(self, field_errors: Dict) -> bool:
        if not isinstance(field_errors, dict):
            return False
        total_error_count = 0
        has_monument_sources_error = False

        for field_name, error_messages in field_errors.items():
            for message in error_messages:
                total_error_count += 1
                if message == self.monument_sources_required_pattern:
                    has_monument_sources_error = True

        return total_error_count == 1 and has_monument_sources_error

    def _process_single_record_fast(self, record_id: str, field_errors: Dict) -> None:
        self.unique_failed_resources.add(record_id)

        if self._is_monument_sources_only_error(field_errors):
            self.monument_sources_only_resources.add(record_id)

        for field_name, error_messages in field_errors.items():
            normalized_field = self.normalize_field_name(field_name)

            for message in error_messages:
                normalized_message = self.normalize_error_message(message)

                self.field_errors[normalized_field] += 1
                self.error_messages[normalized_message] += 1
                self.field_error_combinations[(
                    normalized_field, normalized_message)] += 1
                self.total_errors += 1

                examples_list = self.examples[normalized_message]
                if len(examples_list) < self._examples_max_size:
                    examples_list.append(
                        {
                            "original_field": field_name,
                            "original_message": message,
                            "record_id": record_id,
                        }
                    )

    def generate_report(self, field_limit=20, message_limit=20, combo_limit=15) -> str:
        report_lines = []

        report_lines.append("=" * 80)
        report_lines.append("VALIDATION ERROR ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 40)
        report_lines.append(
            f"Resources processed: {self.total_records_processed:,}")
        report_lines.append(
            f"Total unique failed resources: {len(self.unique_failed_resources):,}")

        actual_failure_count = len(
            self.unique_failed_resources) - len(self.monument_sources_only_resources)

        report_lines.append(
            f"Resources with monument sources-only errors: {len(self.monument_sources_only_resources):,}")
        report_lines.append(
            f"Resources that will not appear in HG: {actual_failure_count:,}")
        report_lines.append(
            f"Resource that will appear in HG: {self.total_records_processed - actual_failure_count:,}")
        report_lines.append(
            f"Total invalid records: {self.total_invalid_records:,}")
        report_lines.append(f"Total validation errors: {self.total_errors:,}")
        report_lines.append(
            f"Unique error messages: {len(self.error_messages):,}")
        report_lines.append(
            f"Unique fields with errors: {len(self.field_errors):,}")
        report_lines.append(
            f"Avg errors per invalid record: {self.total_errors / max(1, self.total_invalid_records):.2f}")
        report_lines.append("")

        field_title = f"{'ALL' if field_limit == 0 else f'TOP {field_limit}'} FIELDS WITH MOST ERRORS"
        report_lines.append(field_title)
        report_lines.append("-" * 40)
        report_lines.append(f"{'Field Name':<50} {'Count':>10} {'%':>8}")
        report_lines.append("-" * 70)

        top_fields = sorted(self.field_errors.items(),
                            key=lambda x: x[1], reverse=True)
        if field_limit > 0:
            top_fields = top_fields[:field_limit]

        for field, count in top_fields:
            percentage = (count / self.total_errors) * 100
            report_lines.append(
                f"{field:<50} {count:>10,} {percentage:>7.1f}%")
        report_lines.append("")

        message_title = f"{'ALL' if message_limit == 0 else f'TOP {message_limit}'} MOST COMMON ERROR MESSAGES"
        report_lines.append(message_title)
        report_lines.append("-" * 40)
        report_lines.append(f"{'Count':>8} {'%':>8} Error Message")
        report_lines.append("-" * 80)

        top_messages = sorted(self.error_messages.items(),
                              key=lambda x: x[1], reverse=True)
        if message_limit > 0:
            top_messages = top_messages[:message_limit]

        for message, count in top_messages:
            percentage = (count / self.total_errors) * 100
            report_lines.append(f"{count:>8,} {percentage:>7.1f}% {message}")
        report_lines.append("")

        combo_title = f"{'ALL' if combo_limit == 0 else f'TOP {combo_limit}'} FIELD + ERROR MESSAGE COMBINATIONS"
        report_lines.append(combo_title)
        report_lines.append("-" * 40)
        report_lines.append(f"{'Count':>8} {'Field':<30} Error Message")
        report_lines.append("-" * 80)

        top_combos = sorted(self.field_error_combinations.items(),
                            key=lambda x: x[1], reverse=True)
        if combo_limit > 0:
            top_combos = top_combos[:combo_limit]

        for (field, message), count in top_combos:
            display_field = field if len(field) <= 30 else field[:27] + "..."
            report_lines.append(f"{count:>8,} {display_field:<30} {message}")
        report_lines.append("")

        report_lines.append("EXAMPLES OF TOP ERROR MESSAGES")
        report_lines.append("-" * 40)

        for message, count in top_messages[:5]:
            report_lines.append(f"\nMessage: {message}")
            report_lines.append(f"Occurrences: {count:,}")
            report_lines.append("Examples:")

            examples = self.examples.get(message, [])
            for i, example in enumerate(examples[:3], 1):
                report_lines.append(
                    f"  {i}. Field: {example['original_field']}")
                report_lines.append(f"     Record: {example['record_id']}")
                if example["original_message"] != message:
                    report_lines.append(
                        f"     Original: {example['original_message']}")

        return "\n".join(report_lines)

    def export_csv(self, output_dir: str = ".") -> None:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        with open(output_path / "field_errors.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Error_Count", "Percentage"])
            for field, count in sorted(self.field_errors.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.total_errors) * 100
                writer.writerow([field, count, f"{percentage:.2f}"])

        with open(output_path / "error_messages.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Error_Message", "Count", "Percentage"])
            for message, count in sorted(self.error_messages.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.total_errors) * 100
                writer.writerow([message, count, f"{percentage:.2f}"])

        with open(output_path / "field_message_combinations.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Error_Message", "Count", "Percentage"])
            for (field, message), count in sorted(self.field_error_combinations.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.total_errors) * 100
                writer.writerow([field, message, count, f"{percentage:.2f}"])
