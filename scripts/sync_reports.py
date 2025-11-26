#!/usr/bin/env python3
"""
Reports Sync Script
Monitors /Users/wonny/Dev/joungwon.stocks/reports for new files
Copies all files to /Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock
"""
import os
import shutil
from pathlib import Path
from datetime import datetime


class ReportSyncer:
    def __init__(self):
        self.source_dir = Path('/Users/wonny/Dev/joungwon.stocks/reports')
        self.source_charts_dir = Path('/Users/wonny/Dev/joungwon.stocks/charts')
        self.target_dir = Path('/Users/wonny/Dev/joungwon.stocks.report/research_report/holding_stock')
        self.log_file = Path('/Users/wonny/Dev/joungwon.stocks/logs/sync_reports.log')

        # Create directories if not exist
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.source_charts_dir.mkdir(parents=True, exist_ok=True)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """Write log message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

    def sync_directory(self, source_dir: Path, dir_name: str):
        """Sync files from a specific directory"""
        # Get all files in source directory
        source_files = list(source_dir.glob('*'))
        source_files = [f for f in source_files if f.is_file()]

        if not source_files:
            self.log(f"📭 No files to sync in {dir_name}/")
            return 0, 0, 0

        self.log(f"📊 Found {len(source_files)} file(s) in {dir_name}/")

        copied_count = 0
        skipped_count = 0
        error_count = 0

        for source_file in source_files:
            target_file = self.target_dir / source_file.name

            try:
                # Check if file already exists and is identical
                if target_file.exists():
                    # Compare file size and modification time
                    source_stat = source_file.stat()
                    target_stat = target_file.stat()

                    if (source_stat.st_size == target_stat.st_size and
                        source_stat.st_mtime <= target_stat.st_mtime):
                        self.log(f"⏭️  Skipped: {source_file.name}")
                        skipped_count += 1
                        continue

                # Copy file
                shutil.copy2(source_file, target_file)
                file_size = source_file.stat().st_size / 1024  # KB
                self.log(f"✅ Copied: {source_file.name} ({file_size:.1f} KB)")
                copied_count += 1

            except Exception as e:
                self.log(f"❌ Error copying {source_file.name}: {e}")
                error_count += 1

        return copied_count, skipped_count, error_count

    def sync_charts_folder(self):
        """Sync charts folder (recursive)"""
        if not self.source_charts_dir.exists():
            self.log("📭 charts/ directory does not exist")
            return 0, 0, 0

        # Create charts folder in target if needed
        target_charts_dir = self.target_dir / 'charts'
        target_charts_dir.mkdir(exist_ok=True)

        copied_count = 0
        skipped_count = 0
        error_count = 0

        # Recursively copy charts folder
        try:
            for item in self.source_charts_dir.rglob('*'):
                if item.is_file():
                    # Calculate relative path
                    rel_path = item.relative_to(self.source_charts_dir)
                    target_file = target_charts_dir / rel_path

                    # Create parent directory if needed
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Check if file already exists and is identical
                    if target_file.exists():
                        source_stat = item.stat()
                        target_stat = target_file.stat()

                        if (source_stat.st_size == target_stat.st_size and
                            source_stat.st_mtime <= target_stat.st_mtime):
                            skipped_count += 1
                            continue

                    # Copy file
                    shutil.copy2(item, target_file)
                    file_size = item.stat().st_size / 1024  # KB
                    self.log(f"✅ Copied chart: {rel_path} ({file_size:.1f} KB)")
                    copied_count += 1

        except Exception as e:
            self.log(f"❌ Error syncing charts folder: {e}")
            error_count += 1

        return copied_count, skipped_count, error_count

    def sync_files(self):
        """Sync all files from source to target directory"""
        try:
            self.log("=" * 80)
            self.log("📁 Report Sync Started")

            total_copied = 0
            total_skipped = 0
            total_errors = 0

            # Sync reports/ directory
            self.log("\n📂 Syncing reports/")
            copied, skipped, errors = self.sync_directory(self.source_dir, "reports")
            total_copied += copied
            total_skipped += skipped
            total_errors += errors

            # Sync charts/ folder
            self.log("\n📂 Syncing charts/")
            copied, skipped, errors = self.sync_charts_folder()
            total_copied += copied
            total_skipped += skipped
            total_errors += errors

            # Summary
            self.log("\n" + "-" * 80)
            self.log(f"📊 Sync Summary:")
            self.log(f"   ✅ Copied: {total_copied} file(s)")
            self.log(f"   ⏭️  Skipped: {total_skipped} file(s)")
            self.log(f"   ❌ Errors: {total_errors} file(s)")
            self.log("=" * 80)

        except Exception as e:
            self.log(f"❌ Sync failed: {e}")
            import traceback
            self.log(traceback.format_exc())


def main():
    """Main function"""
    syncer = ReportSyncer()
    syncer.sync_files()


if __name__ == '__main__':
    main()
