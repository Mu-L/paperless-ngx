# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-03-05 00:40
from __future__ import unicode_literals

import gnupg
import os
import re
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.db import migrations
from django.utils.termcolors import colorize as colourise  # Spelling hurts me


class GnuPG(object):
    """
    A handy singleton to use when handling encrypted files.
    """

    gpg = gnupg.GPG(gnupghome=settings.GNUPG_HOME)

    @classmethod
    def decrypted(cls, file_handle):
        return cls.gpg.decrypt_file(
            file_handle, passphrase=settings.PASSPHRASE).data

    @classmethod
    def encrypted(cls, file_handle):
        return cls.gpg.encrypt_file(
            file_handle,
            recipients=None,
            passphrase=settings.PASSPHRASE,
            symmetric=True
        ).data


def move_documents_and_create_thumbnails(apps, schema_editor):

    os.makedirs(os.path.join(settings.MEDIA_ROOT, "documents", "originals"), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "documents", "thumbnails"), exist_ok=True)

    documents = os.listdir(os.path.join(settings.MEDIA_ROOT, "documents"))

    if set(documents) == {"originals", "thumbnails"}:
        return

    print(colourise(
        "\n\n"
        "  This is a one-time only migration to generate thumbnails for all of your\n"
        "  documents so that future UIs will have something to work with.  If you have\n"
        "  a lot of documents though, this may take a while, so a coffee break may be\n"
        "  in order."
        "\n", opts=("bold",)
    ))

    try:
        os.makedirs(settings.SCRATCH_DIR)
    except FileExistsError:
        pass

    for f in sorted(documents):

        if not f.endswith("gpg"):
            continue

        print("    {} {} {}".format(
            colourise("*", fg="green"),
            colourise("Generating a thumbnail for", fg="white"),
            colourise(f, fg="cyan")
        ))

        thumb_temp = tempfile.mkdtemp(
            prefix="paperless", dir=settings.SCRATCH_DIR)
        orig_temp = tempfile.mkdtemp(
            prefix="paperless", dir=settings.SCRATCH_DIR)

        orig_source = os.path.join(settings.MEDIA_ROOT, "documents", f)
        orig_target = os.path.join(orig_temp, f.replace(".gpg", ""))

        with open(orig_source, "rb") as encrypted:
            with open(orig_target, "wb") as unencrypted:
                unencrypted.write(GnuPG.decrypted(encrypted))

        subprocess.Popen((
            settings.CONVERT_BINARY,
            "-scale", "500x5000",
            "-alpha", "remove",
            orig_target,
            os.path.join(thumb_temp, "convert-%04d.png")
        )).wait()

        thumb_source = os.path.join(thumb_temp, "convert-0000.png")
        thumb_target = os.path.join(
            settings.MEDIA_ROOT,
            "documents",
            "thumbnails",
            re.sub(r"(\d+)\.\w+(\.gpg)", "\\1.png\\2", f)
        )
        with open(thumb_source, "rb") as unencrypted:
            with open(thumb_target, "wb") as encrypted:
                encrypted.write(GnuPG.encrypted(unencrypted))

        shutil.rmtree(thumb_temp)
        shutil.rmtree(orig_temp)

        shutil.move(
            os.path.join(settings.MEDIA_ROOT, "documents", f),
            os.path.join(settings.MEDIA_ROOT, "documents", "originals", f),
        )


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0011_auto_20160303_1929'),
    ]

    operations = [
        migrations.RunPython(move_documents_and_create_thumbnails),
    ]
