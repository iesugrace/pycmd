#!/usr/bin/python3
import sys
import os

from lib import correct_offset, human_size_to_byte, TailLocator
import thinap


class Head:

    def __init__(self, orig_cmd=None, cmd_name=None,
                 bs=None, default_lines=None):
        self.orig_cmd = orig_cmd or '/bin/head'
        self.cmd_name = cmd_name or 'head'
        self.bs = bs or 8192
        self.default_lines = default_lines or 10
        self.ofile = os.fdopen(sys.stdout.fileno(), 'wb')

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

    def run(self, args):
        params = self.parse_args(args)
        options = params[0]
        files = params[1]

        # let the original program handle some options
        if {'quiet', 'verbose', 'help', 'version'} & set(options):
            os.execve(self.orig_cmd, [self.cmd_name] + args, os.environ)

        # mode, amount, forward
        mode, amount, forward = self.comprehend_params(options)

        # when no file specified for reading, use stdin.
        if not files:
            files = ['-']

        # work on each file
        verbose = len(files) > 1
        for n, file in enumerate(files):
            if verbose:
                self.write_header(n, file)
            self.head(file, amount, mode, forward)

    def comprehend_params(self, options):
        """AssertionError will be raised for wrong argument"""
        forward = True
        if 'bytes' in options:
            mode = 'bytes'
            val = options[mode]
            if val[0] == '-':
                forward = False
                val = val[1:]
            amount = human_size_to_byte(val)
        elif 'lines' in options:
            mode = 'lines'
            val = options[mode]
            if val[0] == '-':
                forward = False
                val = val[1:]
            assert val.isdigit(), "invalid number %s" % val
            amount = int(val)
        else:
            mode = 'lines'
            amount = self.default_lines
        return mode, amount, forward

    def write_header(self, n, file):
        if n:
            self.ofile.write(b'\n')
        self.ofile.write(('==> %s <==\n' % file).encode())

    def open_file(self, file):
        if file == '-':
            return os.fdopen(sys.stdin.fileno(), 'rb')
        else:
            return open(file, 'rb')

    def head(self, file, amount, mode='bytes', forward=True):
        ifile = self.open_file(file)

        # apply optimal locating algorithm for seekable file
        if ifile.seekable():
            if forward and mode == 'lines':
                self.copy_first_n_lines(ifile, amount)
                ifile.close()
                return
            elif forward and mode == 'bytes':
                stop_point = ifile.seek(0, 1) + amount
            else:
                stop_point = TailLocator(ifile, mode, amount, self.bs).run()
            self.copy_up_to_byte(ifile, stop_point)
        else:
            assert False, "not implemented"

        correct_offset(ifile)

    def copy_first_n_lines(self, ifile, amount):
        """Copy the first 'amount' lines of the file"""
        ofile = self.ofile
        bs = self.bs
        amount
        while amount:
            chunk = ifile.read(bs)
            if not chunk:
                break

            count = chunk.count(b'\n')  # new-lines in chunk
            if count < amount:
                ofile.write(chunk)
                amount -= count

            # the last chunk
            else:
                pos = -1
                for i in range(amount):
                    pos = chunk.index(b'\n', pos+1)
                pos += 1
                ofile.write(chunk[:pos])
                over_read = len(chunk) - pos

                # move the offset back to the righ place,
                # in order not to affect other processes
                ifile.seek(-over_read, 1)
                break

    def copy_up_to_byte(self, ifile, stop_point):
        """Copy data from pos up to the stop_point"""
        ofile = self.ofile
        bs = self.bs
        pos = ifile.seek(0, 1)
        amount = stop_point - pos
        if bs >= amount:
            ofile.write(ifile.read(amount))
            return

        first = amount % bs
        amount -= first
        ofile.write(ifile.read(first))
        for n in range(amount // bs):
            ofile.write(ifile.read(amount))


if __name__ == '__main__':
    app = Head()
    args = sys.argv[1:]
    app.run(args)
