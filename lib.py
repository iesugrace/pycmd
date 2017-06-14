import sys
import os
import re


def human_size_to_byte(number):
    """
    Convert number of these units to bytes, ignore case:

    b   : 512
    kB  : 1000
    K   : 1024
    mB  : 1000*1000
    m   : 1024*1024
    MB  : 1000*1000
    M   : 1024*1024
    GB  : 1000*1000*1000
    G   : 1024*1024*1024
    TB  : 1000*1000*1000*1000
    T   : 1024*1024*1024*1024
    PB  : 1000*1000*1000*1000*1000
    P   : 1024*1024*1024*1024*1024
    EB  : 1000*1000*1000*1000*1000*1000
    E   : 1024*1024*1024*1024*1024*1024
    ZB  : 1000*1000*1000*1000*1000*1000*1000
    Z   : 1024*1024*1024*1024*1024*1024*1024
    YB  : 1000*1000*1000*1000*1000*1000*1000*1000
    Y   : 1024*1024*1024*1024*1024*1024*1024*1024

    number is of one of these forms:
    123, 123b, 123M, 1G
    """

    mapping = {
        'b'  : 512 ,
        'kb' : 1000,
        'k'  : 1024,
        'mb' : 1000**2,
        'm'  : 1024**2,
        'gb' : 1000**3,
        'g'  : 1024**3,
        'tb' : 1000**4,
        't'  : 1024**4,
        'pb' : 1000**5,
        'p'  : 1024**5,
        'eb' : 1000**6,
        'e'  : 1024**6,
        'zb' : 1000**7,
        'z'  : 1024**7,
        'yb' : 1000**8,
        'y'  : 1024**8,
    }
    unit = re.sub('^[0-9]+', '', number)
    if unit:
        unit = unit.lower()
        assert unit in mapping.keys(), "wrong unit %s " % unit
        amount = int(number[:-len(unit)])
        return mapping[unit] * amount
    else:
        return int(number)


def correct_offset(file):
    """Due to Python cache issue, the real file offset of the
    underlying file descriptor may differ, this function can correct
    it.
    """
    cur = file.seek(0, 1)
    file.seek(0, 2)
    file.seek(cur)


def open_file(file):
    if file == '-':
        return os.fdopen(sys.stdin.fileno(), 'rb')
    else:
        return open(file, 'rb')


class Locator:

    """Search from the end of the file backward, locate the starting
    offset of the specified amount, measured by line, or by byte.
    """

    def __init__(self, ifile, mode, amount, bs=8192):
        """mode can be 'lines' or 'bytes'"""
        assert ifile.seekable(), "input file is not seekable"
        self.orig_pos = ifile.seek(0, 1)
        self.ifile = ifile
        self.mode = mode
        self.amount = amount
        self.bs = bs

    def find_line(self, ifile, chunk, amount):
        """ Find if data chunk contains 'amount' number of lines.

        Return value: (stat, pos, remaining-amount).  If stat is True,
        pos is the result, otherwise pos is not used, remaining-amount
        is for the next run.
        """
        count = chunk.count(b'\n')
        if count <= amount:
            amount -= count
            return False, 0, amount
        else:   # found
            pos = -1
            for i in range(count - amount):
                pos = chunk.index(b'\n', pos+1)
            pos += 1
            diff = len(chunk) - pos
            pos = ifile.seek(-diff, 1)
            return True, pos, 0

    def find_byte(self, ifile, chunk, amount):
        """ Find if data chunk contains 'amount' number of bytes.

        Return value: (stat, pos, remaining-amount).  If stat is True,
        pos is the result, otherwise pos is not used, remaining-amount
        is for the next run.
        """
        length = len(chunk)
        if length < amount:
            amount -= length
            return False, 0, amount
        else:   # found
            pos = ifile.seek(-amount, 1)
            return True, pos, 0

    def find(self, ifile, offset, size, amount):
        """Read 'size' bytes starting from offset to find.

        Return value: (stat, pos, remaining-amount).  If stat is True,
        pos is the result, otherwise pos is not used, remaining-amount
        is for the next run.
        """
        try:
            pos = ifile.seek(offset)
        except OSError:
            assert False, "unkown file seeking failure"

        chunk = ifile.read(size)
        if self.mode == 'lines':
            return self.find_line(ifile, chunk, amount)
        else:
            return self.find_byte(ifile, chunk, amount)

    def run(self):
        """Find the offset of the last 'amount' lines"""
        ifile = self.ifile
        amount = self.amount
        orig_pos = self.orig_pos
        end = ifile.seek(0, 2)   # jump to the end

        # nothing to process, return the original position
        total = end - orig_pos
        if total <= amount:
            correct_offset(ifile)
            return orig_pos

        bs = self.bs

        # process the last block
        remaining = total % bs
        offset = end - remaining
        stat, pos, amount = self.find(ifile, offset, remaining, amount)

        while not stat and offset != orig_pos:
            offset -= bs
            stat, pos, amount = self.find(ifile, offset, bs, amount)

        ifile.seek(self.orig_pos)
        correct_offset(ifile)
        return pos


class Buffer:

    def __init__(self, amount):
        self.min = amount
        self.total = 0
        self.data = []

    def push(self, pair):
        self.data.append(pair)
        self.total += pair[0]

    def pop(self):
        pair = self.data.pop(0)
        self.total -= pair[0]
        return pair

    def cut(self):
        """Pop as many pairs off the head of the self.data as
        self.is_ready() is True, return a combined result.
        """
        count = 0
        data = b''
        while self.is_ready():
            x, y = self.pop()
            count += x
            data += y
        return count, data

    def is_satisfied(self):
        """The minimum amount is satisfied"""
        return self.total >= self.min

    def is_ready(self):
        """The buffer is ready to pop"""
        return self.total - self.data[0][0] >= self.min


class HeadWorkerSL:
    """Seekable, line mode"""

    def __init__(self, ifile, ofile, amount, bs=None):
        self.ifile = ifile
        self.ofile = ofile
        self.amount = amount
        self.bs = bs or 8192

    def read(self):
        return self.ifile.read(self.bs)

    def transform(self, data):
        return data.count(b'\n')

    def is_last(self, count):
        return count >= self.amount

    def action(self, data, count):
        self.ofile.write(data)
        self.amount -= count

    def handle_last(self, data):
        pos = -1
        for i in range(self.amount):
            pos = data.index(b'\n', pos+1)
        pos += 1
        self.ofile.write(data[:pos])
        over_read = len(data) - pos
        try:
            self.ifile.seek(-over_read, 1)
        except Exception:
            pass

    def run(self):
        while self.amount:
            data = self.read()
            if not data:
                break
            count = self.transform(data)
            if self.is_last(count):
                self.handle_last(data)
                break
            else:
                self.action(data, count)


class HeadWorkerSB(HeadWorkerSL):
    """Seekable, byte mode"""

    def transform(self, data):
        return len(data)

    def handle_last(self, data):
        self.ofile.write(data[:self.amount])
        over_read = len(data) - self.amount
        try:
            self.ifile.seek(-over_read, 1)
        except Exception:
            pass


class HeadWorkerTL(HeadWorkerSL):
    """Terminal, line mode"""

    def read(self):
        return self.ifile.readline()

    def action(self, data, count):
        self.ofile.write(data)
        self.amount -= 1
        self.ofile.flush()

    def handle_last(self, data):
        self.ofile.write(data)
        self.ofile.flush()


class HeadWorkerTB(HeadWorkerSB):
    """Terminal, byte mode"""

    def read(self):
        return self.ifile.readline()


class HeadWorkerULIT(HeadWorkerSL):
    """Unseekable, line mode ignore tail"""

    def __init__(self, ifile, ofile, amount, bs=None):
        self.ifile = ifile
        self.ofile = ofile
        self.amount = amount
        self.bs = bs or 8192

    def read(self):
        return self.ifile.read(self.bs)

    def transform(self, data):
        return data.count(b'\n')

    def fill(self):
        """Fill up the buffer with content from self.ifile"""
        amount = self.amount
        buffer = Buffer(amount)
        while True:
            data = self.read()
            if not data:
                break
            count = self.transform(data)
            buffer.push((count, data))
            if buffer.is_satisfied():
                break
        return buffer

    def step(self, buffer):
        """Read and process the self.ifile step by step,
        return False if nothing left in self.ifile.
        """
        data = self.read()
        if not data:
            return False
        count = self.transform(data)
        buffer.push((count, data))
        if buffer.is_ready():
            x, data = buffer.cut()
            self.proc(data)
        return True

    def proc(self, data):
        self.ofile.write(data)
        self.ofile.flush()

    def handle_last(self, buffer):
        while True:
            x, data = buffer.pop()
            if buffer.is_satisfied():
                self.proc(data)
            else:
                diff = buffer.min - buffer.total
                lines = data.splitlines(keepends=True)
                self.ofile.writelines(lines[:-diff])
                break
        self.ofile.flush()

    def run(self):
        buffer = self.fill()
        if buffer.is_satisfied():
            while self.step(buffer):
                pass
            self.handle_last(buffer)


class HeadWorkerTLIT(HeadWorkerULIT):
    """Terminal, line mode ignore tail"""

    def read(self):
        return self.ifile.readline()


class HeadWorkerUBIT(HeadWorkerULIT):
    """Unseekable, byte mode ignore tail"""

    def transform(self, data):
        return len(data)

    def handle_last(self, buffer):
        while True:
            x, data = buffer.pop()
            if buffer.is_satisfied():
                self.ofile.write(data)
            else:
                diff = buffer.min - buffer.total
                self.ofile.write(data[:-diff])
                break
        self.ofile.flush()


class HeadWorkerTBIT(HeadWorkerUBIT):
    """Terminal, byte mode ignore tail"""

    def read(self):
        return self.ifile.readline()


class Mixin:

    def copy_to_end(self):
        while True:
            chunk = self.read()
            if not chunk:
                break
            self.ofile.write(chunk)


class TailWorkerSLIH(HeadWorkerSL, Mixin):
    """Seekable, line mode, ignore head"""

    def __init__(self, ifile, ofile, amount, bs=None):
        super(TailWorkerSLIH, self).__init__(ifile, ofile, amount, bs)
        if amount > 0:
            self.amount -= 1

    def action(self, data, count):
        self.amount -= count

    def handle_last(self, data):
        pos = -1
        for i in range(self.amount):
            pos = data.index(b'\n', pos+1)
        pos += 1
        self.ofile.write(data[pos:])
        self.copy_to_end()


class TailWorkerSBIH(TailWorkerSLIH):
    """Seekable, byte mode, ignore head"""

    def transform(self, data):
        return len(data)

    def handle_last(self, data):
        self.ofile.write(data[self.amount:])
        self.copy_to_end()


class TailWorkerSB(TailWorkerSLIH):

    def __init__(self, ifile, ofile, bs=None):
        self.ifile = ifile
        self.ofile = ofile
        self.bs = bs or 8192

    def run(self):
        self.copy_to_end()


class TailWorkerULIH(HeadWorkerULIT, Mixin):
    """Unseekable, line mode ignore head"""

    def proc(self, data):
        """Just ignore the data"""

    def handle_last(self, buffer):
        while True:
            x, data = buffer.pop()
            if not buffer.is_satisfied():
                diff = buffer.min - buffer.total
                self.split_and_proc(data, diff)
                for x, data in buffer.data:
                    self.ofile.write(data)
                break

    def split_and_proc(self, data, diff):
        lines = data.splitlines(keepends=True)
        self.ofile.writelines(lines[-diff:])


class TailWorkerUBIH(TailWorkerULIH):
    """Unseekable, byte mode ignore head"""

    def read(self):
        return self.ifile.read(self.bs)

    def transform(self, data):
        return len(data)

    def split_and_proc(self, data, diff):
        self.ofile.write(data[-diff:])


class TailWorkerTLIH(TailWorkerULIH):
    """Terminal, line mode ignore head"""

    def read(self):
        return self.ifile.readline()


class TailWorkerTBIH(TailWorkerTLIH):
    """Terminal, byte mode ignore head"""

    def transform(self, data):
        return len(data)

    def split_and_proc(self, data, diff):
        self.ofile.write(data[-diff:])


class TailWorkerTL(TailWorkerSLIH):
    """Terminal, line mode, ignore head"""

    def read(self):
        return self.ifile.readline()

    def handle_last(self, data):
        self.copy_to_end()


class TailWorkerTB(TailWorkerTL):
    """Terminal, byte mode, ignore head"""

    def transform(self, data):
        return len(data)

    def handle_last(self, data):
        self.ofile.write(data[self.amount:])
        self.copy_to_end()


class GrepNameDetermined(Exception): pass
class GrepStatusDetermined(Exception): pass


class GrepWorker:

    # VT100 color code
    c_fname = b'\x1b[35m'           # magenta
    c_sep = b'\x1b[36m'             # cyan
    c_lnum = b'\x1b[32m'            # green
    c_match = b'\x1b[31m\x1b[1m'    # bold red
    c_off = b'\x1b[0m'              # turn off color

    sep_line = b'--\n'
    c_sep_line = c_sep + b'--' + c_off + b'\n'

    def __init__(self, pattern, options, ifile, ofile, bs=None):
        self.pattern = pattern
        self.options = options
        self.ifile = ifile
        self.ofile = ofile
        self.bs = bs or 8192
        self.nr = 0     # number of records
        self.fname = self.make_fname(ifile.name)
        self.status = False

        # Invert the sense of matching
        if ('invert' in options and 'file_match' not in options
                and 'count' not in options):
            self.on_match, self.on_not_match = self.on_not_match, self.on_match

        # set on_match method for -q option
        if 'quiet' in options:
            self.on_match = self.quiet_on_match

        # set reader for tty input file
        if ifile.isatty():
            self.read = self.read_tty
            self.write = self.write_tty

        # setup color output
        color = options['color']
        if color == 'always' or self.ofile.isatty() and color == 'auto':
            self.sep_line = self.c_sep_line
            self.make_fname_str = self.make_color_fname_str
            self.make_lnum_str = self.make_color_lnum_str
            self.make_matcher = self.make_color_matcher

        self.matcher = self.make_matcher(options)

    def insert_line_number(self, lines, num, sep=b':'):
        """Insert line number to the head of each line"""
        num = str(num).encode()
        num_str = self.make_lnum_str(num, sep)
        return (b'%s%s' % (num_str, line) for line in lines)

    def insert_file_name(self, lines, fname, sep=b':'):
        """Insert file name to the head of each line"""
        fname_str = self.make_fname_str(fname, sep)
        return (b'%s%s' % (fname_str, line) for line in lines)

    def make_lnum_str(self, num, sep):
        return num + sep

    def make_fname_str(self, fname, sep):
        return fname + sep

    def make_color_lnum_str(self, num, sep):
        return self.c_lnum + num + self.c_sep + sep + self.c_off

    def make_color_fname_str(self, fname, sep):
        return self.c_fname + fname + self.c_sep + sep + self.c_off

    def quiet_on_match(self, *args, **kargs):
        raise GrepStatusDetermined

    def read(self):
        """Return an enumerate object with line number"""
        lines = self.ifile.readlines(self.bs)
        if not lines:
            return None
        count = len(lines)
        res = enumerate(lines, self.nr + 1)
        self.nr += count
        return res

    def read_tty(self):
        """Read the terminal, line by line"""
        line = self.ifile.readline()
        if not line:
            return None
        self.nr += 1
        return [(self.nr, line)]

    def make_normal_matcher(self, options):
        # handle -w option, match word boundary
        pat = self.pattern
        if 'word_regexp' in self.options:
            pat = r'\b%s\b' % pat

        # handle -i option, ignore case
        flags = 0
        if 'ignore_case' in self.options:
            flags |= re.IGNORECASE
        pat = re.compile(pat.encode(), flags)

        return pat

    def make_matcher(self, options):
        pat = self.make_normal_matcher(options)
        class C:
            def findall(self, line):
                return pat.findall(line), line
        return C()

    def make_color_matcher(self, options):
        pat = self.make_normal_matcher(options)
        c_match = self.c_match
        c_off = self.c_off
        class C:
            def findall(self, line):
                matches = pat.findall(line)
                if matches:
                    matches = [c_match + x + c_off for x in matches]
                    line = re.sub(pat, self.apply_color, line)
                return matches, line
            def apply_color(self, m):
                return c_match + m.group() + c_off

        return C()

    def make_fname(self, name):
        """Make a file name for output"""
        if name == 0:
            name = '(standard input)'.encode()
        else:
            name = str(name).encode()
        return name

    def format_output(self, lines, lnum, options, sep=b':'):
        """Format lines for output"""
        # handle -n option, show line number
        if 'line_number' in options:
            lines = self.insert_line_number(lines, lnum, sep)

        # insert file name if necessary
        if options['with_filename']:
            lines = self.insert_file_name(lines, self.fname, sep)

        return lines

    def write(self, lines):
        self.ofile.writelines(lines)

    def write_tty(self, lines):
        """Write to terminal, flush after every write"""
        self.ofile.writelines(lines)
        self.ofile.flush()

    def on_match(self, matches, line, lnum):
        self.status = True
        # handle -o option, show only the matched part
        if 'only_matching' in self.options:
            lines = (x + b'\n' for x in matches)
        else:
            lines = [line]
        lines = self.format_output(lines, lnum, self.options)
        self.write(lines)

    def on_not_match(self, *args, **kargs):
        return None

    def run(self):
        while True:
            lines_data = self.read()
            if not lines_data:
                break
            for n, line in lines_data:
                matches, line = self.matcher.findall(line)
                if matches:
                    self.on_match(matches, line, n)
                else:
                    self.on_not_match(matches, line, n)
        return self.status


class GrepWorkerAgg(GrepWorker):

    def __init__(self, *args, **kargs):
        super(GrepWorkerAgg, self).__init__(*args, **kargs)
        self.match_count = 0

    def format_output(self, lines, options):
        """Format lines for output"""
        # insert file name if necessary
        if options['with_filename']:
            lines = self.insert_file_name(lines, self.fname)
        return lines

    def on_match(self, matches, line, lnum):
        self.status = True
        self.match_count += 1

    def run(self):
        status = super(GrepWorkerAgg, self).run()
        lines = [str(self.match_count).encode() + b'\n']
        lines = self.format_output(lines, self.options)
        self.write(lines)
        return status


class GrepWorkerFileName(GrepWorker):

    def on_match(self, matches, line, lnum):
        raise GrepNameDetermined

    def run(self):
        try:
            super(GrepWorkerFileName, self).run()
            status = False
        except GrepNameDetermined:
            self.write([self.fname + b'\n'])
            status = True
        return status


class GrepWorkerContext(GrepWorker):

    def __init__(self, *args, **kargs):
        super(GrepWorkerContext, self).__init__(*args, **kargs)
        self.before = self.options.get('before', 0)
        self.after = self.options.get('after', 0)
        self.b_buf = []
        self.a_counter = 0
        self.last_written_lnum = 0

    def write_separator(self, lnum):
        last_lnum = self.last_written_lnum
        first_lnum = self.b_buf[0][0] if self.b_buf else lnum
        if last_lnum and first_lnum - last_lnum > 1:
            self.write([self.sep_line])

    def on_match(self, matches, line, lnum):
        # the 'before' buffer may contain more lines than needed,
        # truncate it before writing the separator in order not
        # to interfere the line number calculation.
        if self.before:
            self.b_buf = self.b_buf[-self.before:]
        else:
            self.b_buf.clear()
        self.write_separator(lnum)
        self.write_b_buffer()
        super(GrepWorkerContext, self).on_match(matches, line, lnum)
        self.last_written_lnum = lnum
        self.reset_a_counter()

    def on_not_match(self, matches, line, lnum):
        if self.a_counter:
            if 'only_matching' not in self.options:
                lines = self.format_output([line], lnum, self.options, b'-')
                self.write(lines)
            self.last_written_lnum = lnum
            self.a_counter -= 1
        else:
            self.b_buf.append((lnum, line))

    def reset_a_counter(self):
        self.a_counter = self.after

    def write_b_buffer(self):
        """Write out the 'before' buffer"""
        if not self.b_buf:
            return

        # write only when -o option is not presented,
        if 'only_matching' not in self.options:
            for lnum, line in self.b_buf:
                lines = self.format_output([line], lnum, self.options, b'-')
                self.write(lines)

        self.last_written_lnum = self.b_buf[-1][0]
        self.b_buf.clear()

    def run(self):
        bs = self.before
        while True:
            self.b_buf = self.b_buf[-bs:]
            lines_data = self.read()
            if not lines_data:
                break
            for n, line in lines_data:
                matches, line = self.matcher.findall(line)
                if matches:
                    self.on_match(matches, line, n)
                else:
                    self.on_not_match(matches, line, n)
        return self.status


def recursive_walk(worker, names, pattern, options):
    """Process all regular files, descend into directories. When
    the -q option is provided, the first match will trigger an
    exception named GrepStatusDetermined."""

    def processor(names, pattern, options, worker):
        status_list = []
        for name in names:
            if os.path.isfile(name):
                status = worker(name, pattern, options)
                status_list.append(status)
            elif os.path.isdir(name):
                try:
                    sub_names = os.listdir(name)
                except Exception as e:
                    print(str(e), file=sys.stderr)
                    status_list.append(False)
                else:
                    sub_names = [os.path.join(name, x) for x in sub_names]
                    names.extend(sub_names)
        return status_list

    return walk(worker, names, pattern, options, processor)


def walk(worker, names, pattern, options, processor=None):
    """Each file shall be a regular file. When the -q option is
    provided, the first match will trigger an exception named
    GrepStatusDetermined."""
    if not processor:
        def processor(names, pattern, options, worker):
            status_list = []
            for name in names:
                status = worker(name, pattern, options)
                status_list.append(status)
            return status_list

    try:
        status_list = processor(names, pattern, options, worker)
    except GrepStatusDetermined:
        status_list = [True]

    if 'quiet' in options:
        return any(status_list)
    else:
        return all(status_list)
