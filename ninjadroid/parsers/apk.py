import os
import shutil
import tempfile
from typing import Dict, List
from zipfile import ZipFile, is_zipfile

from ninjadroid.aapt.aapt import Aapt
from ninjadroid.errors.apk_parsing_error import APKParsingError
from ninjadroid.errors.android_manifest_parsing_error import AndroidManifestParsingError
from ninjadroid.errors.cert_parsing_error import CertParsingError
from ninjadroid.errors.parsing_error import ParsingError
from ninjadroid.parsers.apk_interface import APKInterface
from ninjadroid.parsers.android_manifest import AndroidManifest
from ninjadroid.parsers.cert import Cert
from ninjadroid.parsers.dex import Dex
from ninjadroid.parsers.file import File


class APK(File, APKInterface):
    """
    Parser implementation for Android APK package.
    """

    _TEMPORARY_DIR = ".ninjadroid"

    def __init__(self, filepath: str, string_processing: bool = True):
        super(APK, self).__init__(filepath)

        if not self.looks_like_an_apk(filepath):
            raise APKParsingError

        self._files = []  # type: List
        self._extract_and_set_entries(string_processing)

        if len(self._files) == 0 or self._cert is None:
            raise APKParsingError

        self._app_name = Aapt.get_app_name(filepath)

    def _extract_and_set_entries(self, string_processing: bool):
        """
        Extract the APK package entries (e.g. AndroidManifest.xml, CERT.RSA, classes.dex, ...) and
        set the correspondent attributes.

        :param string_processing: If True (default), the URLs and shell commands in the classes.dex will be extracted.
        :return: If one of the APK entries is invalid.
        :raise APKParsingError: 
        """
        exists_invalid_entry = False

        apk_filepath = self.get_file_path()
        with ZipFile(apk_filepath) as apk:
            tmpdir = tempfile.mkdtemp(APK._TEMPORARY_DIR)

            for filename in apk.namelist():
                entry_filepath = apk.extract(filename, tmpdir)

                try:
                    if AndroidManifest.looks_like_a_manifest(filename):
                        self._manifest = AndroidManifest(entry_filepath, True, apk_filepath)
                    elif Cert.looks_like_a_cert(filename):
                        self._cert = Cert(entry_filepath, filename)
                    elif Dex.looks_like_a_dex(filename):
                        self._dex = Dex(entry_filepath, string_processing)
                    else:
                        if not os.path.isdir(entry_filepath):
                            self._files.append(File(entry_filepath, filename))
                except (ParsingError, AndroidManifestParsingError, CertParsingError):
                    exists_invalid_entry = True

            try:
                shutil.rmtree(tmpdir)
            except OSError:
                pass

            if exists_invalid_entry:
                raise APKParsingError

    @staticmethod
    def looks_like_an_apk(filepath: str) -> bool:
        return File.is_a_file(filepath) and is_zipfile(filepath)

    def dump(self) -> Dict:
        dump = super(APK, self).dump()
        dump["app_name"] = self._app_name
        dump["cert"] = self._cert.dump() if self._cert is not None else None
        dump["manifest"] = self._manifest.dump() if self._manifest is not None else None
        dump["dex"] = self._dex.dump() if self._dex is not None else None
        dump["other_files"] = []
        for file in self._files:
            dump["other_files"].append(file.dump())
        return dump

    def get_file_list(self) -> List:
        return self._files

    def get_manifest(self) -> AndroidManifest:
        return self._manifest

    def get_cert(self) -> Cert:
        return self._cert

    def get_dex(self) -> Dex:
        return self._dex

    def get_app_name(self) -> str:
        return self._app_name
