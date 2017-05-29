#!/usr/bin/python3
import sys
import os

from lib import correct_offset, human_size_to_byte, TailLocator
import thinap


class Head:

    def __init__(self, orig_cmd=None, cmd_name=None,
                 bs=None, default_lines=None, output_file=None):
        self.orig_cmd = orig_cmd or '/bin/head'
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

        self.ofile.close()

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
            elif forward and mode == 'bytes':
                self.copy_first_n_bytes(ifile, amount)
            else:
                stop_point = TailLocator(ifile, mode, amount, self.bs).run()
                pos = ifile.seek(0, 1)
                amount = stop_point - pos
                self.copy_first_n_bytes(ifile, amount)
            correct_offset(ifile)
        elif ifile.isatty():
            if forward and mode == 'lines':
                self.copy_first_n_lines_tty(ifile, amount)
            elif forward and mode == 'bytes':
                self.copy_first_n_bytes(ifile, amount)
            elif mode == 'lines':
                self.leave_last_n_lines_tty(ifile, amount)
            else:
                self.leave_last_n_bytes_tty(ifile, amount)
        else:
            if forward and mode == 'lines':
                self.copy_first_n_lines_nonseekable(ifile, amount)
            elif forward and mode == 'bytes':
                self.copy_first_n_bytes(ifile, amount)
            elif mode == 'lines':
                self.leave_last_n_lines(ifile, amount)
            else:
                self.leave_last_n_bytes(ifile, amount)

        ifile.close()

    def copy_first_n_lines(self, ifile, amount):
        """Copy the first 'amount' lines of the file"""
        ofile = self.ofile
        bs = self.bs
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

    def copy_first_n_lines_nonseekable(self, ifile, amount):
        """Copy the first 'amount' lines of the unseekable file"""
        ofile = self.ofile
        bs = self.bs
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
                break

    def copy_first_n_lines_tty(self, ifile, amount):
        """Copy the first 'amount' lines from the terminal,
        one line at a time.
        """
        ofile = self.ofile
        while amount:
            line = ifile.readline()
            if not line:
                break
            ofile.write(line)
            ofile.flush()
            if amount > 1:
                amount -= 1
            else:
                break

    def leave_last_n_lines(self, ifile, amount):
        """Copy but leave the last N lines, ifile is not seekable"""
        ofile = self.ofile
        bs = self.bs
        ready = LineBuffer(bs, amount)
        buffer = LineBuffer(bs, amount)

        while buffer.fill(ifile):
            if buffer.is_ready():
                list(map(ofile.write, ready.data))
                ready = buffer
                buffer = LineBuffer(bs, amount)

        chunk = b''.join(ready.data + buffer.data)
        lines = chunk.splitlines(keepends=True)
        if amount:
            lines = lines[:-amount]
        ofile.writelines(lines)

    def leave_last_n_lines_tty(self, ifile, amount):
        """Copy but leave the last N lines"""
        ofile = self.ofile
        bs = self.bs
        ready = LineBufferTty(bs, amount)
        buffer = LineBufferTty(bs, amount)

        while buffer.fill(ifile):
            if buffer.is_ready():
                ofile.writelines(ready.data)
                ofile.flush()
                ready = buffer
                buffer = LineBufferTty(bs, amount)

        lines = ready.data + buffer.data
        if amount:
            lines = lines[:-amount]
        ofile.writelines(lines)

    def leave_last_n_bytes(self, ifile, amount):
        """Copy but leave the last N bytes, ifile is not seekable"""
        ofile = self.ofile
        bs = self.bs
        ready = ByteBuffer(bs, amount)
        buffer = ByteBuffer(bs, amount)

        while buffer.fill(ifile):
            if buffer.is_ready():
                list(map(ofile.write, ready.data))
                ready = buffer
                buffer = ByteBuffer(bs, amount)

        chunk = b''.join(ready.data + buffer.data)
        if amount:
            chunk = chunk[:-amount]
        ofile.write(chunk)

    def leave_last_n_bytes_tty(self, ifile, amount):
        """Copy but leave the last N bytes"""
        ofile = self.ofile
        bs = self.bs
        ready = ByteBufferTty(bs, amount)
        buffer = ByteBufferTty(bs, amount)

        while buffer.fill(ifile):
            if buffer.is_ready():
                ofile.writelines(ready.data)
                ofile.flush()
                ready = buffer
                buffer = ByteBufferTty(bs, amount)

        chunk = b''.join(ready.data + buffer.data)
        if amount:
            chunk = chunk[:-amount]
        ofile.write(chunk)

    def copy_first_n_bytes(self, ifile, amount):
        """Copy 'amount' bytes from ifile"""
        ofile = self.ofile
        bs = self.bs
        if bs >= amount:
            ofile.write(ifile.read(amount))
            return

        first = amount % bs
        amount -= first
        ofile.write(ifile.read(first))
        for n in range(amount // bs):
            ofile.write(ifile.read(bs))


class LineBuffer:
    """For keeping the last N lines of the input file"""

    def __init__(self, bs, amount):
        self.bs = bs
        self.amount = amount
        self.total = 0
        self.data = []

    def fill(self, ifile):
        chunk = ifile.read(self.bs)
        if chunk:
            self.data.append(chunk)
            self.total += self.count(chunk)
            return True
        else:
            return False

    def count(self, chunk):
        return chunk.count(b'\n')

    def is_ready(self):
        return self.total >= self.amount


class ByteBuffer(LineBuffer):

    def count(self, chunk):
        return len(chunk)


class LineBufferTty:
    """For keeping the last N lines of the terminal"""

    def __init__(self, bs, amount):
        self.bs = bs
        self.amount = amount
        self.total = 0
        self.total_bytes = 0
        self.data = []

    def fill(self, ifile):
        line = ifile.readline()
        if line:
            self.data.append(line)
            self.total += self.count(line)
            self.total_bytes += len(line)
            return True
        else:
            return False

    def count(self, chunk):
        return 1

    def is_ready(self):
        return self.total >= self.amount and self.total_bytes >= self.bs


class ByteBufferTty(LineBufferTty):

    def count(self, line):
        return len(line)


if __name__ == '__main__':
    app = Head()
    args = sys.argv[1:]
    app.run(args)
