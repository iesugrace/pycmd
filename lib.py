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


class TailLocator:

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
