#!/usr/bin/env python
import argparse
import os
import shutil
import sys
from subprocess import call, check_output
import textwrap


try:
    WindowsError
except NameError:
    IS_WIN = False
    PIP = '/bin/pip'
    PIPSI = '/bin/pipsi'
else:
    IS_WIN = True
    PIP = '/Scripts/pip.exe'
    PIPSI = '/Scripts/pipsi.exe'

if sys.version_info.major < 3:
    try:
        import virtualenv  # NOQA
        venv_pkg = 'virtualenv'
        del virtualenv
    except ImportError:
        venv_pkg = None
else:
    venv_pkg = 'venv'

DEFAULT_PIPSI_HOME = os.path.expanduser('~/.local/venvs')
DEFAULT_PIPSI_BIN_DIR = os.path.expanduser('~/.local/bin')


def echo(msg=''):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


def fail(msg):
    sys.stderr.write(msg + '\n')
    sys.stderr.flush()
    sys.exit(1)


def succeed(msg):
    echo(msg)
    sys.exit(0)


def command_exists(cmd):
    with open(os.devnull, 'w') as null:
        try:
            return call(
                [cmd, '--version'],
                stdout=null, stderr=null) == 0
        except OSError:
            return False


def publish_script(venv, bin_dir):
    if IS_WIN:
        for name in os.listdir(venv + '/Scripts'):
            if 'pipsi' in name.lower():
                shutil.copy(venv + '/Scripts/' + name, bin_dir)
    else:
        os.symlink(venv + '/bin/pipsi', bin_dir + '/pipsi')
    echo('Installed pipsi binary in ' + bin_dir)


def install_files(venv, bin_dir, install):
    try:
        os.makedirs(bin_dir)
    except OSError:
        pass

    def _cleanup():
        try:
            shutil.rmtree(venv)
        except (OSError, IOError):
            pass

    if sys.version_info.major < 3:
        executable = sys.executable
    else:
        executable = get_real_python(sys.executable)
        print('sys.executable={} sys.real_prefix={} executable={}'.format(sys.executable, getattr(sys, 'real_prefix', None), executable))
    if call([executable, '-m', venv_pkg, venv]) != 0:
        _cleanup()
        fail('Could not create virtualenv for pipsi :(')

    if call([venv + PIP, 'install', install]) != 0:
        _cleanup()
        fail('Could not install pipsi :(')

    publish_script(venv, bin_dir)


def parse_options(argv):
    bin_dir = os.environ.get('PIPSI_BIN_DIR', DEFAULT_PIPSI_BIN_DIR)
    home_dir = os.environ.get('PIPSI_HOME', DEFAULT_PIPSI_HOME)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bin-dir',
        default=bin_dir,
        help=(
            'Executables will be installed into this folder. '
            'Default: %(default)s'
        ),
    )
    parser.add_argument(
        '--home',
        dest='home_dir',
        default=home_dir,
        help='Virtualenvs are created in this folder. Default: %(default)s',
    )
    parser.add_argument(
        '--src',
        default='pipsi',
        help=(
            'The specific version of pipsi to install. This value is passed '
            'to "pip install <value>". For example, to install from master '
            'use "git+https://github.com/mitsuhiko/pipsi.git#egg=pipsi". '
            'Default: %(default)s'
        ),
    )
    parser.add_argument(
        '--ignore-existing',
        action='store_true',
        help=(
            "ignore versions of pipsi already installed. "
            "Use this to ignore a package manager based install or for testing"
        ),
    )
    return parser.parse_args(argv)


code_for_get_real_python = (
    'import sys; print("{},{}".format('
    'getattr(sys, "real_prefix", ""), '
    'sys.version_info.major))'
)


def get_real_python(python):
    cmd = [python, '-c', code_for_get_real_python]
    out = check_output(cmd)
    if not isinstance(out, str):
        out = out.decode()
    real_prefix, major = out.strip().split(',')
    if not real_prefix:
        return python

    for i in [major, '']:
        real_python = os.path.join(real_prefix, 'bin', 'python' + i)
        if os.path.exists(real_python):
            return real_python
    raise ValueError('Can not find real python under {}'.format(real_prefix))


def main(argv=sys.argv[1:]):
    args = parse_options(argv)

    if command_exists('pipsi') and not args.ignore_existing:
        succeed('You already have pipsi installed')
    else:
        echo('Installing pipsi')

    if venv_pkg is None:
        fail('You need to have virtualenv installed to bootstrap pipsi.')

    venv = os.path.join(args.home_dir, 'pipsi')
    install_files(venv, args.bin_dir, args.src)

    if not command_exists('pipsi'):
        echo(textwrap.dedent(
            '''
            %(sep)s

            Warning:
              It looks like %(bin_dir)s is not on your PATH so pipsi will not
              work out of the box. To fix this problem make sure to add this to
              your .bashrc / .profile file:

              export PATH=%(bin_dir)s:$PATH

            %(sep)s
            ''' % dict(sep='=' * 60, bin_dir=args.bin_dir)
        ))

    succeed('pipsi is now installed.')


if __name__ == '__main__':
    main()
