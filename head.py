#!/usr/bin/python3
import sys
import os

from lib import (human_size_to_byte, correct_offset, Locator, HeadWorkerSL,
                 HeadWorkerSB, HeadWorkerTL, HeadWorkerTB, HeadWorkerULIT,
                 HeadWorkerTLIT, HeadWorkerUBIT, HeadWorkerTBIT)
import thinap


class Head:

    def __init__(self, orig_cmd=None, cmd_name=None,
                 bs=None, default_lines=None, output_file=None):
        self.orig_cmd = orig_cmd or '/usr/bin/head'
        self.cmd_name = cmd_name or 'head'
        self.bs = bs or 8192
        self.default_lines = default_lines or 10
        self.ofile = output_file or os.fdopen(sys.stdout.fileno(), 'wb')

    def parse_args(self, args):
        request = {'bytes': {'flag': ['-c', '--bytes'], 'arg': 1},
                   'lines': {'flag': ['-n', '--lines'], 'arg': 1},
                   'quiet': {'flag': ['-q', '--quiet', '--silent']},
                   'verbose': {'flag': ['-v', '--verbose']},
                   'help': {'flag': '--help'},
                   'version': {'flag': '--version'},
        }
        p = thinap.ArgParser()
        return p.parse_args(args, request)

    def exec_orig_on_condition(self, options):
        excluded = {'quiet', 'verbose', 'help', 'version'}
        if excluded & set(options):
            os.execve(self.orig_cmd, [self.cmd_name] + args, os.environ)

    def run(self, args):
        params = self.parse_args(args)
        options = params[0]
        files = params[1]

        # let the original program handle some options
        self.exec_orig_on_condition(options)

        # mode, amount, direct
        mode, amount, direct = self.comprehend_params(options)

        # when no file specified for reading, use stdin.
        if not files:
            files = ['-']

        # work on each file
        verbose = len(files) > 1
        for n, file in enumerate(files):
            if verbose:
                self.write_header(n, file)
            self.work(file, amount, mode, direct)

        self.ofile.close()

    def comprehend_params(self, options):
        """AssertionError will be raised for wrong argument"""
        direct = True
        if 'bytes' in options:
            mode = 'bytes'
            val = options[mode]
            if val[0] == '-':
                direct = False
                val = val[1:]
            amount = human_size_to_byte(val)
        elif 'lines' in options:
            mode = 'lines'
            val = options[mode]
            if val[0] == '-':
                direct = False
                val = val[1:]
            assert val.isdigit(), "invalid number %s" % val
            amount = int(val)
        else:
            mode = 'lines'
            amount = self.default_lines
        return mode, amount, direct

    def write_header(self, n, file):
        if n:
            self.ofile.write(b'\n')
        self.ofile.write(('==> %s <==\n' % file).encode())

    def open_file(self, file):
        if file == '-':
            return os.fdopen(sys.stdin.fileno(), 'rb')
        else:
            return open(file, 'rb')

    def work(self, file, amount, mode='bytes', direct=True):
        ifile = self.open_file(file)

        if ifile.seekable():
            if direct and mode == 'lines':
                HeadWorkerSL(ifile, self.ofile, amount, self.bs).run()
            elif direct and mode == 'bytes':
                HeadWorkerSB(ifile, self.ofile, amount, self.bs).run()
            else:
                # apply optimal locating algorithm for seekable file
                stop_point = Locator(ifile, mode, amount, self.bs).run()
                pos = ifile.seek(0, 1)
                amount = stop_point - pos
                HeadWorkerSB(ifile, self.ofile, amount, self.bs).run()
            correct_offset(ifile)

        elif ifile.isatty():
            if direct and mode == 'lines':
                HeadWorkerTL(ifile, self.ofile, amount).run()
            elif direct and mode == 'bytes':
                HeadWorkerTB(ifile, self.ofile, amount).run()
            elif mode == 'lines':
                HeadWorkerTLIT(ifile, self.ofile, amount).run()
            else:
                HeadWorkerTBIT(ifile, self.ofile, amount).run()

        else:
            if direct and mode == 'lines':
                HeadWorkerSL(ifile, self.ofile, amount, self.bs).run()
            elif direct and mode == 'bytes':
                HeadWorkerSB(ifile, self.ofile, amount, self.bs).run()
            elif mode == 'lines':
                HeadWorkerULIT(ifile, self.ofile, amount, self.bs).run()
            else:
                HeadWorkerUBIT(ifile, self.ofile, amount, self.bs).run()

        ifile.close()


if __name__ == '__main__':
    app = Head()
    args = sys.argv[1:]
    try:
        app.run(args)
    except AssertionError as e:
        print(e)
        exit(1)
