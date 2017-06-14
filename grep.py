#!/home/joshua/.pyenv/versions/3.6.1/bin/python3.6
import sys
import os

import thinap
from lib import (open_file, GrepWorker, GrepWorkerAgg, GrepWorkerFileName,
                 GrepWorkerContext, recursive_walk, walk)


class Grep:

    def __init__(self, orig_cmd=None, cmd_name=None,
                 bs=None, output_file=None):
        self.orig_cmd = orig_cmd or '/bin/grep'
        self.cmd_name = cmd_name or 'grep'
        self.bs = bs or 8192
        self.ofile = output_file or os.fdopen(sys.stdout.fileno(), 'wb')

    def parse_args(self, args):
        request = {'ignore_case': {'flag': ['-i', '--ignore-case']},
                   'file_match': {'flag': ['-l', '--files-with-matches']},
                   'line_number': {'flag': ['-n', '--line-number']},
                   'count': {'flag': ['-c', '--count']},
                   'only_matching': {'flag': ['-o', '--only-matching']},
                   'word_regexp': {'flag': ['-w', '--word-regexp']},
                   'after': {'flag': ['-A', '--after-context'], 'arg': 1},
                   'before': {'flag': ['-B', '--before-context'], 'arg': 1},
                   'context': {'flag': ['-C', '--context'], 'arg': 1},
                   'drecursive': {'flag': ['-R', '--dereference-recursive']},
                   'quiet': {'flag': ['-q', '--quiet', '--silent']},
                   'invert': {'flag': ['-v', '--invert-match']},
                   'with_filename': {'flag': '-H', 'multi': True, 'order': True},
                   'no_filename': {'flag': '-h', 'multi': True, 'order': True},
        }
        p = thinap.ArgParser()
        return p.parse_args(args, request, preserve=True)

    def exec_orig(self, args):
        os.execve(self.orig_cmd, [self.cmd_name] + args, os.environ)

    def run(self, args):
        params = self.parse_args(args)

        # let the original program handle some options
        if params[-1]:
            self.exec_orig(sys.argv[1:])

        pattern, files, options = self.comprehend_params(params)

        # when no file specified for reading, use stdin.
        if not files:
            files = ['-']

        # work on each file
        if 'drecursive' in options:
            status = recursive_walk(self.work, files, pattern, options)
        else:
            status = walk(self.work, files, pattern, options)

        self.ofile.close()
        return status

    def comprehend_params(self, params):
        """AssertionError will be raised for wrong argument"""
        options = params[0]
        before = after = None
        if 'context' in options:
            v = options['context']
            assert v.isdigit(), "invalid argument for -C: %s" % v
            before = after = int(v)
        if 'after' in options:
            v = options['after']
            assert v.isdigit(), "invalid argument for -A: %s" % v
            after = int(v)
        if 'before' in options:
            v = options['before']
            assert v.isdigit(), "invalid argument for -B: %s" % v
            before = int(v)
        if before is not None:
            options['before'] = before
        if after is not None:
            options['after'] = after

        x = params[1]
        assert x, "pattern is required"
        pattern = x[0]
        files = x[1:]

        # show the file name or not?
        with_filename = False
        if 'drecursive' in options or len(files) > 1:
            with_filename = True
        # if both -h and -H are supplied, the right-most takes effect.
        if 'with_filename' in options and 'no_filename' in options:
            yes_idx = options['with_filename'][-1][0]
            no_idx = options['no_filename'][-1][0]
            with_filename = yes_idx > no_idx
            del options['no_filename']
        elif 'with_filename' in options:
            with_filename = True
        elif 'no_filename' in options:
            with_filename = False
            del options['no_filename']
        options['with_filename'] = with_filename

        # remove the argument position info
        pattern = pattern[-1]
        files = [a for n,a in files]
        return pattern, files, options

    def work(self, file, pattern, options):
        try:
            ifile = open_file(file)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return False

        if 'count' in options:
            worker = GrepWorkerAgg
        elif 'file_match' in options:
            worker = GrepWorkerFileName
        elif set(['after', 'before', 'context']) & set(options.keys()):
            worker = GrepWorkerContext
        else:
            worker = GrepWorker
        status = worker(pattern, options, ifile, self.ofile, self.bs).run()

        ifile.close()
        return status


if __name__ == '__main__':
    app = Grep()
    args = sys.argv[1:]
    try:
        status = app.run(args)
    except Exception as e:
        print(e)
        exit(1)
    else:
        code = 0 if status else 1
        exit(code)
