"""Build three preset libraries and bundle them into a Python-ABI-independent wheel."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Distribution, setup
from setuptools.command.build_py import build_py
from wheel.bdist_wheel import bdist_wheel

ROOT = Path(__file__).parent.resolve()


class NativeDistribution(Distribution):
    def has_ext_modules(self):
        return True


class BuildPy(build_py):
    def run(self):
        super().run()
        prefix = ROOT / "build" / "native"
        env = os.environ.copy()
        env.setdefault("ZIG_GLOBAL_CACHE_DIR", str(ROOT / ".zig-global-cache"))
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ziglang",
                "build",
                "-Doptimize=ReleaseSafe",
                "-Dcpu=baseline",
                "-j2",
                "--prefix",
                str(prefix),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        destination = (
            ROOT / "src" / "ssz_z" / "_native"
            if self.editable_mode
            else Path(self.build_lib) / "ssz_z" / "_native"
        )
        destination.mkdir(parents=True, exist_ok=True)
        libraries = [p for p in prefix.rglob("*ssz_z_*") if p.suffix in {".so", ".dylib", ".dll"}]
        if len(libraries) != 3:
            raise RuntimeError(f"Expected three preset libraries, found {libraries}")
        for library in libraries:
            shutil.copy2(library, destination / library.name)


class NativeWheel(bdist_wheel):
    def get_tag(self):
        _, _, platform = super().get_tag()
        return "py3", "none", platform


setup(distclass=NativeDistribution, cmdclass={"build_py": BuildPy, "bdist_wheel": NativeWheel})
