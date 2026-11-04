#!/usr/bin/env python
"""Run the idempotent demo catalog seeder."""

import os
import sys
from pathlib import Path

import django
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
django.setup()

if __name__ == "__main__":
    call_command("seed_data")
