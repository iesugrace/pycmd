#!/usr/bin/python3
import sys
import os

import thinap
from numberutils import human_size_to_byte


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
        # apply optimal locating algorithm
        if ifile.seekable():
            if forward and mode == 'lines':
                self.copy_first_n_lines(ifile, amount)
                return
            elif forward and mode == 'bytes':
                stop_point = amount
            elif mode == 'lines':
                stop_point = self.find_start_of_last_n_lines(ifile, amount)
            elif mode == 'bytes':
                stop_point = self.find_start_of_last_n_bytes(ifile, amount)
            self.copy_up_to_byte(ifile, stop_point)
        else:
            if forward:
                ...
            else:
                ...

        # 1. read first N lines (read, check if exceeds line count, then write,
        # and keep line counts), before writing the final block, check the
        # total bytes count.
        #
        # All the following three are the same: set a stop point first:
        #
        # 2. read first N bytes (set a stop point, then read and write)
        # 3. read except the last N lines (find the stop point, convert to 'except last N bytes')
        # 4. read except the last N bytes (check if exceeds the stop point)

    def copy_first_n_lines(self, ifile, amount):
        """Copy the first 'amount' lines of the file"""
        ifile.seek(0)
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
                # in order not to affect other process
                ifile.seek(-over_read, 1)
                break

    def copy_up_to_byte(self, ifile, stop_point):
        """Copy data from pos up to the stop_point"""
        ofile = self.ofile
        bs = self.bs
        pos = 0
        amount = stop_point - pos
        ifile.seek(0)
        if bs >= amount:
            ofile.write(ifile.read(amount))
            return

        #
        # debug: use a loop to loop a specified times,
        # stop before the stop_point
        #
        check_point = amount - bs
        while True:
            chunk = ifile.read(bs)
            if not chunk:
                break
            ofile.write(chunk)
            pos += len(chunk)
            if pos >= check_point:
                ofile.write(ifile.read(stop_point - pos))
                break

    def find_start_of_last_n_lines(self, ifile, amount):
        """Find the offset of the last 'amount' lines"""
        def find_backward(ifile, size, amount):
            try:
                offset = ifile.seek(-size, 1)
            except OSError:
                cur_pos = ifile.seek(0, 1)
                if cur_pos == 0:    # at the beginning of file
                    return True, 0, None
                elif cur_pos < size:    # less bytes left, expeted
                    offset = ifile.seek(0)
                    size = cur_pos
                else:
                    assert False, "unkown file seeking failure"

            chunk = ifile.read(size)
            if not chunk:
                return True, offset, None
            count = chunk.count(b'\n')

            # in "line" mode, count equal to amount is not a sign
            # of 'found'.
            if count <= amount:
                amount -= count
                return False, offset, amount
            else:   # found
                offset = -1
                for i in range(count - amount):
                    offset = chunk.index(b'\n', offset+1)
                offset += 1
                diff = len(chunk) - offset
                offset = ifile.seek(-diff, 1)
                return True, offset, None

        bs = self.bs
        end = ifile.seek(0, 2)

        # in order to align the offset with the beginning of the file,
        # the first try is less than the block size.
        last_bs = end % bs
        stat, offset, amount = find_backward(ifile, last_bs, amount)
        if stat:
            return offset

        while not stat:
            stat, offset, amount = find_backward(ifile, bs, amount)

        return offset

    def find_start_of_last_n_bytes(self, ifile, amount):
        """Find the offset of the last 'amount' bytes"""
        def find_backward(ifile, size, amount):
            try:
                offset = ifile.seek(-size, 1)
            except OSError:
                cur_pos = ifile.seek(0, 1)
                if cur_pos == 0:    # at the beginning of file
                    return True, 0, None
                elif cur_pos < size:    # less bytes left, expeted
                    offset = ifile.seek(0)
                    size = cur_pos
                else:
                    assert False, "unkown file seeking failure"

            chunk = ifile.read(size)
            if not chunk:
                return True, offset, None
            length = len(chunk)
            if length < amount:
                amount -= length
                return False, offset, amount
            else:   # found
                offset = ifile.seek(-amount, 1)
                return True, offset, None


class TailSearcher:

    """Search from the end of the file backward, locate the starting
    offset of the specified amount, measured by line, or by byte.
    """

    def __init__(self, ifile, mode, amount):
        """mode can be 'line' or 'byte'"""
        assert ifile.seekable(), "input file is not seekable"
        self.orig_pos = ifile.seek(0, 1)
        self.ifile = ifile
        self.mode = mode
        self.amount = amount

    def find_line(self, chunk amount):
        """ Find if data chunk contains 'amount' number of lines.

        Return value: (stat, offset, remaining-amount).
        If the stat is True, the offset is the result, otherwise
        it's useless. 'remaining-amount' is for the next run.
        """
        count = chunk.count(b'\n')
        if count <= amount:
            amount -= count
            return False, 0, amount
        else:   # found
            offset = -1
            for i in range(count - amount):
                offset = chunk.index(b'\n', offset+1)
            offset += 1
            diff = len(chunk) - offset
            offset = ifile.seek(-diff, 1)
            return True, offset, 0

    def find_byte(self, chunk amount):
        """ Find if data chunk contains 'amount' number of bytes.

        Return value: (stat, offset, remaining-amount).
        If the stat is True, the offset is the result, otherwise
        it's useless. 'remaining-amount' is for the next run.
        """
        length = len(chunk)
        if length < amount:
            amount -= length
            return False, 0, amount
        else:   # found
            offset = ifile.seek(-amount, 1)
            return True, offset, 0

    def find(self, size, amount):
        """Read 'size' bytes from file (if possible) to find

        Return value: (stat, offset, remaining-amount).
        If the stat is True, the offset is the result, otherwise
        it's useless. 'remaining-amount' is for the next run.
        """
        ifile = self.ifile
        try:
            offset = ifile.seek(-size, 1)
        except OSError:
            cur_pos = ifile.seek(0, 1)
            if cur_pos == 0:    # at the beginning of file
                return True, 0, 0
            elif cur_pos < size:    # less bytes left
                offset = ifile.seek(0)
                size = cur_pos
            else:
                assert False, "unkown file seeking failure"

        chunk = ifile.read(size)
        if self.mode == 'line':
            return self.find_line(chunk, amount)
        else:
            return self.find_byte(chunk, amount)

    def run(self):
        """Find the offset of the last 'amount' lines"""
        ifile = self.ifile
        bs = self.bs
        end = ifile.seek(0, 2)
        while not stat:
            stat, offset, amount = self.find(ifile, bs, amount)
        ifile.seek(self.orig_pos)
        return offset


if __name__ == '__main__':
    app = Head()
    args = sys.argv[1:]
    app.run(args)
