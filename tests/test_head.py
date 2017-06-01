import os
import sys
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile

import pexpect

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__name__), '..'))
sys.path.insert(0, BASEDIR)

from head import Head


class Mixin:

    def setup_class(cls):
        cls.ifile_name = NamedTemporaryFile().name
        cls.ofile_name = NamedTemporaryFile().name
        ifile = open(cls.ifile_name, 'w')
        lines = ['a0b0c0d0e\n', 'f0g0h0i0j\n', 'k0l0m0n0o\n',
                 'p0q0r0s0t\n', 'u0v0w0x0y\n', 'z0A0B0C0D\n',
                 'E0F0G0H0I\n', 'J0K0L0M0N\n', 'O0P0Q0R0S\n',
                 'T0U0V0W0X\n']
        ifile.writelines(lines)
        ifile.close()

    def teardown_class(cls):
        os.unlink(cls.ifile_name)
        os.unlink(cls.ofile_name)

    def setup_method(self):
        self.ofile = open(self.ofile_name, 'wb')

    def get_result(self):
        with open(self.ofile_name) as f:
            read_data = f.read()
            f.close()
        return read_data

    def get_correct_data(self, count, direct=True):
        with open(self.ifile_name) as f:
            data = f.read()
            if direct:
                correct_data = data[:count]
            else:
                correct_data = data[:-count]
            f.close()
        return correct_data


class PipeMixin(Mixin):

    def setup_method(self):
        self.pipe = Popen(['cat', self.ifile_name], stdout=PIPE)
        self.ofile = open(self.ofile_name, 'wb')

    def teardown_method(self):
        self.pipe.wait()


class TerminalMixin:

    def setup_method(self):
        self.input_data = ['a0b0c0d0e\n', 'f0g0h0i0j\n', 'k0l0m0n0o\n',
                           'p0q0r0s0t\n', 'u0v0w0x0y\n', 'z0A0B0C0D\n',
                           'E0F0G0H0I\n', 'J0K0L0M0N\n', 'O0P0Q0R0S\n',
                           'T0U0V0W0X\n']


class TestHead(Mixin):

    def test_bs1_line5(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_line5(self):
        app = Head(bs=200, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs1_bytes50(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_bytes50(self):
        app = Head(bs=200, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs1_len10_byte(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_len10_byte(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs1_len10_line(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_len10_line(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_amount50_size100(self):
        app = Head(output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_amount200_size100(self):
        app = Head(output_file=self.ofile)
        args = ['-c200', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(200)
        assert read_data == correct_data


class TestHeadFileSize(Mixin):

    def test_bs1_size100_byte(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_size100_byte(self):
        app = Head(bs=200, output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs1_size100_line(self):
        app = Head(bs=1, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_bs200_size100_line(self):
        app = Head(bs=200, output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data


class TestModeAndDirection(Mixin):

    def test_line_direct(self):
        app = Head(output_file=self.ofile)
        args = ['-n5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_byte_direct(self):
        app = Head(output_file=self.ofile)
        args = ['-c50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_line_indirect(self):
        app = Head(output_file=self.ofile)
        args = ['-n', '-5', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50, direct=False)
        assert read_data == correct_data

    def test_byte_indirect(self):
        app = Head(output_file=self.ofile)
        args = ['-c', '-50', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50, direct=False)
        assert read_data == correct_data


class TestPipeInput(PipeMixin):

    def test_line_direct(self):
        app = Head(output_file=self.ofile)
        args = ['-n5']
        sys.stdin = self.pipe.stdout
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_byte_direct(self):
        app = Head(output_file=self.ofile)
        args = ['-c50']
        sys.stdin = self.pipe.stdout
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50)
        assert read_data == correct_data

    def test_line_indirect(self):
        app = Head(output_file=self.ofile)
        args = ['-n', '-5']
        sys.stdin = self.pipe.stdout
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50, direct=False)
        assert read_data == correct_data

    def test_byte_indirect(self):
        app = Head(output_file=self.ofile)
        args = ['-c', '-50']
        sys.stdin = self.pipe.stdout
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data(50, direct=False)
        assert read_data == correct_data


class TestTerminalInput(TerminalMixin):

    def test_line_direct(self):
        c = pexpect.spawn('../head.py -n5', echo=False)
        for line in self.input_data:
            c.send(line)
        c.sendcontrol('d')
        c.expect(pexpect.EOF)
        read_data = c.before.replace(b'\r\n', b'\n').decode()
        correct_data = ''.join(self.input_data[:5])
        assert read_data == correct_data

    def test_byte_direct(self):
        c = pexpect.spawn('../head.py -c50', echo=False)
        for line in self.input_data:
            c.send(line)
        c.sendcontrol('d')
        c.expect(pexpect.EOF)
        read_data = c.before.replace(b'\r\n', b'\n').decode()
        correct_data = ''.join(self.input_data[:5])
        assert read_data == correct_data

    def test_line_indirect(self):
        c = pexpect.spawn('../head.py -n -3', echo=False)
        for line in self.input_data:
            c.send(line)
        c.sendcontrol('d')
        c.expect(pexpect.EOF)
        read_data = c.before.replace(b'\r\n', b'\n').decode()
        correct_data = ''.join(self.input_data[:7])
        assert read_data == correct_data

    def test_byte_indirect(self):
        c = pexpect.spawn('../head.py -c -10', echo=False)
        for line in self.input_data:
            c.send(line)
        c.sendcontrol('d')
        c.expect(pexpect.EOF)
        read_data = c.before.replace(b'\r\n', b'\n').decode()
        correct_data = ''.join(self.input_data)[:-10]
        assert read_data == correct_data

    def test_buffer(self):
        c = pexpect.spawn('../head.py -n -3', echo=False)
        line = self.input_data[0]
        c.send(line)
        index = c.expect([pexpect.TIMEOUT, line], timeout=0.1)
        assert index == 0
        for n in range(9):
            c.send(line)
        c.sendcontrol('d')
        c.expect(pexpect.EOF)
        read_data = c.before.replace(b'\r\n', b'\n').decode()
        correct_data = line * 7
        assert read_data == correct_data
