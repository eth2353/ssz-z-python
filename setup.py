"""Build three preset libraries and bundle them into a Python-ABI-independent wheel."""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py

ROOT = Path(__file__).parent.resolve()
UPSTREAM = json.loads((ROOT / "UPSTREAM.json").read_text())
MACOS_ARCHITECTURES = {"arm64": "aarch64", "x86_64": "x86_64"}


class NativeDistribution(Distribution):
    def has_ext_modules(self):
        return True


class BuildPy(build_py):
    def run(self):
        machine = platform.machine().lower()
        if sys.platform == "darwin" and machine in MACOS_ARCHITECTURES:
            target_options = [f"-Dtarget={MACOS_ARCHITECTURES[machine]}-macos"]
            suffix = ".dylib"
        elif sys.platform == "linux" and machine in {"x86_64", "aarch64"}:
            target_options = []
            suffix = ".so"
        else:
            raise RuntimeError("ssz-z-python supports Linux and macOS on x86_64 and ARM64 only")
        super().run()
        build_root = ROOT / "build"
        build_root.mkdir(exist_ok=True)
        env = os.environ.copy()
        env.setdefault("ZIG_GLOBAL_CACHE_DIR", str(ROOT / ".zig-global-cache"))
        package_root = (
            ROOT / "src" / "ssz_z" if self.editable_mode else Path(self.build_lib) / "ssz_z"
        )
        destination = package_root / "_native"
        with TemporaryDirectory(prefix="native-", dir=build_root) as temporary:
            prefix = Path(temporary)
            subprocess.run(  # noqa: S603 - Trusted local command and arguments.
                [
                    sys.executable,
                    "-m",
                    "ziglang",
                    "build",
                    "-Doptimize=ReleaseSafe",
                    "-Dcpu=baseline",
                    *target_options,
                    "-j2",
                    f"-Dpython={sys.executable}",
                    "--prefix",
                    str(prefix),
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
            libraries = []
            for preset in UPSTREAM["bindings"]["presets"]:
                library = prefix / "lib" / f"libssz_z_{preset}{suffix}"
                if not library.is_file():
                    raise RuntimeError(f"Missing native library: {library}")
                libraries.append(library)
            # This directory contains generated artifacts only. Never carry binaries
            # from another build or platform into the new wheel/editable install.
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True)
            for library in libraries:
                shutil.copy2(library, destination / library.name)
        shutil.copy2(ROOT / "UPSTREAM.json", package_root / "_upstream.json")


class NativeWheel(bdist_wheel):
    def get_tag(self):
        _, _, platform_tag = super().get_tag()
        if platform_tag.startswith("macosx_"):
            # The Zig build targets one architecture even with a universal2 Python.
            prefix, major, minor, _ = platform_tag.split("_", maxsplit=3)
            platform_tag = f"{prefix}_{major}_{minor}_{platform.machine().lower()}"
        return "py3", "none", platform_tag


setup(distclass=NativeDistribution, cmdclass={"build_py": BuildPy, "bdist_wheel": NativeWheel})
