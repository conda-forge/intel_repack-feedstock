import argparse
import glob
import os
import os.path
import re
import shutil
import string
import subprocess
import sys
import tempfile
import yaml
import zipfile


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run(cmd):
    proc = subprocess.run(cmd, check=True)
    if proc.returncode != 0:
        raise (RuntimeError(f"Error running: {' '.join(cmd)}"))


def shell(cmd):
    subprocess.run(cmd, shell=True, check=True)


def unzip(filename, include=None, dir="."):
    zf = zipfile.ZipFile(filename)
    members = [
        name
        for name in zf.namelist()
        if include is not None and name.startswith(include)
    ]
    zf.extractall(dir, members)


def chdir_glob(dir, pattern):
    old_cwd = os.getcwd()
    os.chdir(dir)
    # If you use iglob, it runs AFTER the following os.chdir()
    files = glob.glob(pattern, recursive=True)
    os.chdir(old_cwd)
    return files


class Tarball:
    _re = re.compile(r"^([A-Za-z0-9_.-]+?)_(\d+)\.(\d+)\.(\d+)(|\.tgz)$")

    def __init__(self, filename):
        if "/" in filename:
            filename = os.path.basename(filename)
        match = self._re.search(filename)
        if match is None:
            raise (RuntimeError(f"Filename: {filename} does not match"))
        self.name, self.year, self.revision, self.build, _ = match.groups()

        self.version_regex = re.sub(r"\.", r"\\.", self.version())
        self.rpmversion_regex = re.sub(r"\.", r"\\.", self.rpmversion())

    def __repr__(self):
        return f'Tarball("{self.name}_{self.version()}.tgz")'

    def __str__(self):
        return f"{self.name}_{self.version()}.tgz"

    def version(self):
        return f"{self.year}.{self.revision}.{self.build}"

    def rpmversion(self):
        return f"{self.year}.{self.revision}-{self.build}"


class Exeball:
    _re = re.compile(r"^([A-Za-z0-9_.-]+?)_(\d+)\.(\d+)\.(\d+)\.exe")

    def __init__(self, filename):
        if "/" in filename or "\\" in filename:
            filename = os.path.basename(filename)
        match = self._re.search(filename)
        if match is None:
            raise (RuntimeError(f"Filename: {filename} does not match"))
        self.name, self.year, self.revision, self.build = match.groups()

        self.version_regex = re.sub(r"\.", r"\\.", self.version())
        self.msi_regex = r"\d+\.\d+\.\d+\.\d+\.msi$"

    def __repr__(self):
        return f'Tarball("{self.name}_{self.version()}.tgz")'

    def __str__(self):
        return f"{self.name}_{self.version()}.tgz"

    def version(self):
        return f"{self.year}.{self.revision}.{self.build}"


class Dmgball:
    _re = re.compile(r"^([A-Za-z0-9_.-]+?)_(\d+)\.(\d+)\.(\d+)\.dmg$")

    def __init__(self, filename):
        if "/" in filename:
            filename = os.path.basename(filename)
        match = self._re.search(filename)
        if match is None:
            raise (RuntimeError(f"Filename: {filename} does not match"))
        self.name, self.year, self.revision, self.build = match.groups()

        self.version_regex = re.sub(r"\.", r"\\.", self.version())

    def __repr__(self):
        return f'Tarball("{self.name}_{self.version()}.tgz")'

    def __str__(self):
        return f"{self.name}_{self.version()}.tgz"

    def version(self):
        return f"{self.year}.{self.revision}.{self.build}"


class PercentTemplate(string.Template):
    delimiter = "%"


def subs(name, archive, base="", prefix=""):
    t = PercentTemplate(name)
    if type(archive) is Tarball:
        return t.substitute(
            version=archive.version(),
            rpmversion=archive.rpmversion(),
            base=base,
            prefix=prefix,
        )
    elif type(archive) is Exeball:
        return t.substitute(
            version=archive.version(), base=base, prefix=prefix,
        )
    elif type(archive) is Dmgball:
        return t.substitute(
            version=archive.version(), base=base, prefix=prefix,
        )
    else:
        raise (RuntimeError(f"subs called with type {repr(type(archive))}"))


def ensure_dir(path):
    head, tail = os.path.split(path)
    os.makedirs(head, exist_ok=True)


def subst_copy(src, dest, tar, base="", prefix=""):
    with open(src, "r") as s:
        with open(dest, "w") as d:
            for line in s:
                d.write(subs(line, tar, base, prefix))


def file_copy(src, dest):
    if os.path.isdir(src):
        return
    ensure_dir(dest)
    shutil.copy2(src, dest)


class Operator:
    def __init__(
        self, base, src_dir, output_dir, archive=None, origin=None, recipe=None
    ):
        self.base = base
        self.src = src_dir
        self.dst = output_dir
        self.archive = archive
        self.origin = origin
        self.recipe = recipe

    def operation(self, op, op_args):
        print(f"operation {op}")
        if "_" in op:
            # allow for multiple operations of the same type
            op, _ = op.split("_", maxsplit=1)
        if op == "prefix":
            for prefix, patterns in op_args.items():
                basedir = os.path.join(self.src, self.base, prefix)
                for pattern in patterns:
                    for f in chdir_glob(basedir, pattern):
                        print(f" {f}")
                        origin = os.path.join(basedir, f)
                        target = os.path.join(self.dst, f)
                        file_copy(origin, target)
        elif op == "copy":
            for src, dest in op_args:
                origin = os.path.join(self.src, self.base, src)
                target = os.path.join(self.dst, dest)
                file_copy(origin, target)
        elif op == "sourcecopy":
            if self.origin is None:
                eprint(" origin not set")
                sys.exit(3)
            for src, dest in op_args:
                origin = subs(
                    os.path.join(self.src, src), self.archive, base=self.base
                )
                target = os.path.join(self.origin, dest)
                print(f" {src} -> {dest}")
                file_copy(origin, target)
        elif op == "recipecopy":
            if self.recipe is None:
                eprint(" recipe not set")
                sys.exit(3)
            for src, dest in op_args:
                origin = subs(
                    os.path.join(self.recipe, src),
                    self.archive,
                    base=self.base,
                )
                target = os.path.join(self.dst, dest)
                print(f" {src} -> {dest}")
                subst_copy(
                    origin,
                    target,
                    self.archive,
                    base=self.base,
                    prefix=self.dst,
                )
        elif op == "copies":
            src = op_args["from"]
            dest = op_args["to"]
            files = op_args["files"]
            basedir = os.path.join(self.src, self.base, src)
            print(f"{src} -> {dest}")
            print(f" base = {basedir}")
            for pattern in files:
                print(f"pat: {pattern}")
                for f in chdir_glob(basedir, pattern):
                    origin = os.path.join(basedir, f)
                    target = os.path.join(self.dst, dest, f)
                    print(f" {f}")
                    file_copy(origin, target)
        elif op == "rpms":
            if self.archive is None:
                eprint(" tar not set")
                sys.exit(3)
            for rpm, instructions in op_args.items():
                print("  ", subs(rpm, self.archive))
                self.extract_rpm(
                    os.path.join(self.src, "rpm", subs(rpm, self.archive)),
                    instructions,
                )
        elif op == "msis":
            if self.archive is None:
                eprint(" exe not set")
                sys.exit(3)
            for msi, instructions in op_args.items():
                print("  ", subs(msi, self.archive))
                self.extract_msi(
                    os.path.join(self.src, "installs"),
                    subs(msi, self.archive),
                    instructions,
                )
        elif op == "tars":
            if self.archive is None:
                eprint(" dmg not set")
                sys.exit(3)
            print("opargs:", repr(op_args))
            for tar, instructions in op_args.items():
                print(" +", tar)
                print(" -", subs(tar, self.archive))
                self.extract_tar(
                    self.src, subs(tar, self.archive), instructions,
                )
        else:
            eprint(f"Unknown operation: {op}")
            sys.exit(9)

    def extract_rpm(self, rpmfile, instructions):
        with tempfile.TemporaryDirectory() as tmpdir:
            eprint(f"Unpacking {rpmfile} into {tmpdir}")
            shell(f"rpm2archive < {rpmfile} | tar -xzC {tmpdir}")

            operator = Operator(
                self.base,
                tmpdir,
                self.dst,
                self.archive,
                self.origin,
                self.recipe,
            )
            for op, op_args in instructions.items():
                operator.operation(op, op_args)

    def extract_tar(self, origin, tarpattern, instructions):
        print("@ pattern:", tarpattern)
        print("@ origin:", origin)
        for tarfile in chdir_glob(origin, f"**/{tarpattern}"):
            with tempfile.TemporaryDirectory() as tmpdir:
                eprint(f"Unpacking {tarfile} into {tmpdir}")
                run(
                    ["tar", "-xf", os.path.join(origin, tarfile), "-C", tmpdir]
                )
                operator = Operator(
                    self.base,
                    tmpdir,
                    self.dst,
                    self.archive,
                    self.origin,
                    self.recipe,
                )
                for op, op_args in instructions.items():
                    operator.operation(op, op_args)

    def extract_msi(self, origin, msipattern, instructions):
        for msifile in chdir_glob(origin, f"**/{msipattern}"):
            with tempfile.TemporaryDirectory() as tmpdir:
                eprint(f"Unpacking {msifile} into {tmpdir}")
                run(
                    [
                        "msiexec",
                        "/a",
                        os.path.join(origin, msifile),
                        "/qb",
                        f"TARGETDIR={tmpdir}",
                    ]
                )
                operator = Operator(
                    self.base,
                    tmpdir,
                    self.dst,
                    self.archive,
                    self.origin,
                    self.recipe,
                )
                for op, op_args in instructions.items():
                    operator.operation(op, op_args)


def extract_linux64(args, requires, base_pattern, tars_directory):
    tars = requires["tars"]
    for targlob, components in tars.items():
        wildcard = os.path.join(tars_directory, targlob)
        tarlist = glob.glob(wildcard)
        if len(tarlist) == 1:
            tarfile = tarlist[0]
            tar = Tarball(tarfile)
            print(f"Found: {tar} {tar.rpmversion()}")
            base = subs(base_pattern, tar)
            with tempfile.TemporaryDirectory() as tmpdir:
                eprint(f"Unpacking {tarfile} into {tmpdir}")
                run(
                    [
                        "tar",
                        "-xf",
                        tarfile,
                        "-C",
                        tmpdir,
                        "--strip-components=1",
                        "--wildcards",
                        "*.rpm",
                    ]
                )
                print(f"  - {base}")
                operator = Operator(
                    base,
                    tmpdir,
                    args.output,
                    archive=tar,
                    origin=tars_directory,
                    recipe=args.recipe,
                )
                for op, op_args in components.items():
                    operator.operation(op, op_args)
        elif len(tarlist) > 1:
            eprint(f"More than one file matches: {wildcard}")
            sys.exit(2)
        else:
            # Try for an unpacked directory
            wild, ext = os.path.splitext(wildcard)
            wildlist = glob.glob(wild)
            if len(wildlist) == 1:
                directory = wildlist[0]
                if not os.path.isdir(directory):
                    eprint(f"{directory} is not a directory")
                    sys.exit(2)
                tar = Tarball(directory)
                base = subs(base_pattern, tar)
                rpmdir = os.path.join(directory, "rpm")
                if not os.path.isdir(rpmdir):
                    eprint("f{rpmdir} is not a directory")
                    sys.exit(2)
                operator = Operator(
                    base,
                    directory,
                    args.output,
                    archive=tar,
                    origin=tars_directory,
                    recipe=args.recipe,
                )
                for op, op_args in components.items():
                    operator.operation(op, op_args)


def extract_win64(args, requires, base_pattern, exes_directory):
    exes = requires["exes"]
    print(repr(exes))
    print(f"src: {exes_directory}")
    for exeglob, components in exes.items():
        wildcard = os.path.join(exes_directory, exeglob)
        exelist = glob.glob(wildcard)
        if len(exelist) == 1:
            exefile = exelist[0]
            exe = Exeball(exefile)
            print(f"Found: {exe} {exe.version()}")
            base = subs(base_pattern, exe)
            with tempfile.TemporaryDirectory() as tmpdir:
                eprint(f"Unpacking {exefile} into {tmpdir}")
                unzip(exefile, include="installs", dir=tmpdir)
                print(f"  - {base}")
                operator = Operator(
                    base,
                    tmpdir,
                    args.output,
                    archive=exe,
                    origin=exes_directory,
                    recipe=args.recipe,
                )
                for op, op_args in components.items():
                    operator.operation(op, op_args)
        elif len(exelist) > 1:
            eprint(f"More than one file matches: {wildcard}")
            sys.exit(2)


def extract_osx64(args, requires, base_pattern, dmgs_directory):
    dmgs = requires["dmgs"]
    print(repr(dmgs))
    print(f"src: {dmgs_directory}")
    for dmgglob, components in dmgs.items():
        wildcard = os.path.join(dmgs_directory, dmgglob)
        dmglist = glob.glob(wildcard)
        if len(dmglist) == 1:
            dmgfile = dmglist[0]
            dmg = Dmgball(dmgfile)
            print(f"Found: {dmg} {dmg.version()}")
            base = subs(base_pattern, dmg)
            with tempfile.TemporaryDirectory() as tmpdir:
                eprint(f"Unpacking {dmgfile} into {tmpdir}")
                run(
                    [
                        "hdiutil",
                        "attach",
                        dmgfile,
                        "-readonly",
                        "-mountpoint",
                        tmpdir,
                    ]
                )
                try:
                    print(f"  - {base}")
                    operator = Operator(
                        base,
                        tmpdir,
                        args.output,
                        archive=dmg,
                        origin=dmgs_directory,
                        recipe=args.recipe,
                    )
                    for op, op_args in components.items():
                        operator.operation(op, op_args)
                finally:
                    run(["hdiutil", "detach", tmpdir])
        elif len(dmglist) > 1:
            eprint(f"More than one file matches: {wildcard}")
            sys.exit(2)


def extract_package(args, requirements):
    package_name = args.package
    requires = requirements["packages"][package_name]
    if args.arch == "linux-64":
        extract_linux64(
            args,
            requires=requires,
            base_pattern=requirements["base"],
            tars_directory=args.tarballs,
        )
    elif args.arch == "win-64":
        extract_win64(
            args,
            requires=requires,
            base_pattern=requirements["base"],
            exes_directory=args.tarballs,
        )
    elif args.arch == "osx-64":
        extract_osx64(
            args,
            requires=requires,
            base_pattern=requirements["base"],
            dmgs_directory=args.tarballs,
        )
    else:
        eprint(f"unrecognised arch: {args.arch}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Extract MKL packages")
    parser.add_argument(
        "-a",
        "--arch",
        help="architecture (eg. win-64, linux-64)",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--tarballs",
        help="directory containing Intel tarballs",
        metavar="D",
        default=os.environ.get("SRC_DIR", None),
        required="SRC_DIR" not in os.environ,
    )
    parser.add_argument(
        "-r",
        "--recipe",
        help="directory containing build recipe",
        metavar="D",
        default=os.environ.get("RECIPE_DIR", None),
        required="SRC_DIR" not in os.environ,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="directory to unpack to",
        metavar="D",
        default=os.environ.get("PREFIX", None),
        required="PREFIX" not in os.environ,
    )
    parser.add_argument(
        "-i",
        "--instructions",
        help="YAML format file of instructions",
        metavar="f",
    )
    parser.add_argument(
        "-p",
        "--package",
        help="package to assemble",
        metavar="N",
        default=os.environ.get("PKG_NAME", None),
        required="PKG_NAME" not in os.environ,
    )
    parser.add_argument(
        "dummy", nargs="*", help="Extra arguments which will be discarded"
    )
    args = parser.parse_args()

    if args.arch not in ["linux-64", "win-64", "osx-64"]:
        eprint(f"Unknown architecture {args.arch}")
        sys.exit(1)

    if not args.instructions:
        args.instructions = f"repack.{args.arch}.yaml"

    print(f"Opening {args.instructions}")
    with open(args.instructions) as f:
        requirements = yaml.safe_load(f)

    if args.package not in requirements["packages"]:
        eprint(f"missing {args.package}!")
        sys.exit(1)

    if not os.path.isdir(args.tarballs):
        eprint(f"{args.tarballs} is not a directory")
        sys.exit(1)

    if sys.platform == "linux" and "BUILD_PREFIX" in os.environ:
        # This ought not to be needed. Listed build dependencies
        # should be automatically added to the PATH by conda build.
        os.environ["PATH"] += ":" + os.path.join(
            os.environ["BUILD_PREFIX"], "bin"
        )

    extract_package(args, requirements)


if __name__ == "__main__":
    main()
