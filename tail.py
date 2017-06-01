#!/usr/bin/python3
import sys
import os

from head import Head
from lib import (human_size_to_byte, correct_offset, Locator, TailWorkerSLIH,
                 TailWorkerSBIH, TailWorkerSB, TailWorkerULIH, TailWorkerUBIH,
                 TailWorkerTLIH, TailWorkerTBIH, TailWorkerTL, TailWorkerTB)
import thinap


class Tail(Head):

    def __init__(self, orig_cmd=None, cmd_name=None,
                 bs=None, default_lines=None, output_file=None):
        super(Tail, self).__init__(orig_cmd, cmd_name, bs,
                                   default_lines, output_file)
        self.orig_cmd = orig_cmd or '/usr/bin/tail'
        self.cmd_name = cmd_name or 'tail'

    def parse_args(self, args):
        request = {'bytes': {'flag': ['-c', '--bytes'], 'arg': 1},
                   'lines': {'flag': ['-n', '--lines'], 'arg': 1},
                   'quiet': {'flag': ['-q', '--quiet', '--silent']},
                   'verbose': {'flag': ['-v', '--verbose']},
                   'help': {'flag': '--help'},
                   'version': {'flag': '--version'},
                   'follow': {'flag': ['-f', '-F', '--follow']},
                   'maxuc': {'flag': '--max-unchanged-stats'},
                   'pid': {'flag': '--pid'},
                   'retry': {'flag': '--retry'},
                   'interval': {'flag': ['-s', '--sleep-interval']},
        }
        p = thinap.ArgParser()
        return p.parse_args(args, request)

    def exec_orig_on_condition(self, options):
        excluded = {'follow', 'maxuc', 'pid', 'retry', 'interval',
                    'quiet', 'verbose', 'help', 'version'}
        if excluded & set(options):
            os.execve(self.orig_cmd, [self.cmd_name] + args, os.environ)

    def comprehend_params(self, options):
        """AssertionError will be raised for wrong argument"""
        direct = True
        if 'bytes' in options:
            mode = 'bytes'
            val = options[mode]
            if val[0] == '+':
                direct = False
                val = val[1:]
            amount = human_size_to_byte(val)
        elif 'lines' in options:
            mode = 'lines'
            val = options[mode]
            if val[0] == '+':
                direct = False
                val = val[1:]
            assert val.isdigit(), "invalid number %s" % val
            amount = int(val)
        else:
            mode = 'lines'
            amount = self.default_lines
        return mode, amount, direct

    def work(self, file, amount, mode='bytes', direct=True):
        ifile = self.open_file(file)

        if ifile.seekable():
            if direct:
                # apply optimal locating algorithm for seekable file
                start_point = Locator(ifile, mode, amount, self.bs).run()
                ifile.seek(start_point)
                TailWorkerSB(ifile, self.ofile, self.bs).run()
            elif mode == 'lines':
                TailWorkerSLIH(ifile, self.ofile, amount, self.bs).run()
            elif mode == 'bytes':
                TailWorkerSBIH(ifile, self.ofile, amount, self.bs).run()

        elif ifile.isatty():
            if direct and mode == 'lines':
                TailWorkerTLIH(ifile, self.ofile, amount, self.bs).run()
            elif direct and mode == 'bytes':
                TailWorkerTBIH(ifile, self.ofile, amount, self.bs).run()
            elif mode == 'lines':
                TailWorkerTL(ifile, self.ofile, amount, self.bs).run()
            else:
                TailWorkerTB(ifile, self.ofile, amount, self.bs).run()

        else:
            if direct and mode == 'lines':
                TailWorkerULIH(ifile, self.ofile, amount, self.bs).run()
            elif direct and mode == 'bytes':
                TailWorkerUBIH(ifile, self.ofile, amount, self.bs).run()
            elif mode == 'lines':
                TailWorkerSLIH(ifile, self.ofile, amount, self.bs).run()
            else:
                TailWorkerSBIH(ifile, self.ofile, amount, self.bs).run()

        ifile.close()


if __name__ == '__main__':
    app = Tail()
    args = sys.argv[1:]
    try:
        app.run(args)
    except AssertionError as e:
        print(e)
        exit(1)
