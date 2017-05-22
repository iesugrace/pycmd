#!/usr/bin/python3
import os
import sys


def collect_file_names(args):
    """Collect input files from command line arguments, defaults to
    stdin.
    """
    return [x for x in args if x != '-n'] or ['-']


def gen_writer(args):
    start = 1

    def number_writer(ofile, chunk):
        """Number the lines in data chunk, start from 'start'."""
        nonlocal start
        lines = chunk.splitlines(keepends=True)
        for num, line in enumerate(lines, start):
            prefix = '%6d\t' % num
            ofile.write(prefix.encode() + line)
        start = num + 1

    def default_writer(ofile, chunk):
        ofile.write(chunk)

    if '-n' in args:
        return number_writer
    else:
        return default_writer


def cat(ifile, ofile, writer, bs=1048576):
    """Read line by line when the input file is a tty, otherwise read
    one block.
    """
    if ifile.isatty():
        reader = lambda: ifile.readline()
    else:
        # read a chunk, continue up to the end of the line
        def reader():
            res = ifile.read(bs)
            res += ifile.readline()
            return res

    while True:
        buf = reader()
        if not buf:
            break
        writer(ofile, buf)
        ofile.flush()


def open_file(name):
    if name == '-':
        f = os.fdopen(sys.stdin.fileno(), 'rb')
    else:
        f = open(name, 'rb')
    return f


def run_external_on_condition(cmd, args):
    """Execute external C cat if any argument in the 'other_args'
    found. This is not a good way for argument handling since it can
    not recognize arguments like '-An', a better solution should be
    using the argparse module or something similar.
    """
    other_args = {'-b', '-e', '-s', '-A', '-E', '-t', '-T',
                  '-u', '-v', '--help', '--version'}
    if set(args) & other_args:
        os.execve(cmd, ['cat'] + args, os.environ)


if __name__ == '__main__':
    args = sys.argv[1:]
    run_external_on_condition('/bin/cat', args)
    writer = gen_writer(args)
    files = collect_file_names(args)
    ofile = os.fdopen(sys.stdout.fileno(), 'wb')
    for name in files:
        ifile = open_file(name)
        cat(ifile, ofile, writer)
