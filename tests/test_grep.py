import os
import sys
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile

import pexpect

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__name__), '..'))
sys.path.insert(0, BASEDIR)

from grep import Grep


class Mixin:

    def setup_class(cls):
        cls.ifile_name = NamedTemporaryFile().name
        cls.ofile_name = NamedTemporaryFile().name
        ifile = open(cls.ifile_name, 'w')
        text = """In the beginning God created the heaven and the earth.
And the earth was without form, and void; and darkness [was] upon the face of the deep. And the Spirit of God moved upon the face of the waters.
And God said, Let there be light: and there was light.
And God saw the light, that [it was] good: and God divided the light from the darkness.
And God called the light Day, and the darkness he called Night. And the evening and the morning were the first day.
And God said, Let there be a firmament in the midst of the waters, and let it divide the waters from the waters.
And God made the firmament, and divided the waters which [were] under the firmament from the waters which [were] above the firmament: and it was so.
And God called the firmament Heaven. And the evening and the morning were the second day.
And God said, Let the waters under the heaven be gathered together unto one place, and let the dry [land] appear: and it was so.
And God called the dry [land] Earth; and the gathering together of the waters called he Seas: and God saw that [it was] good.
And God said, Let the earth bring forth grass, the herb yielding seed, [and] the fruit tree yielding fruit after his kind, whose seed [is] in itself, upon the earth: and it was so.
And the earth brought forth grass, [and] herb yielding seed after his kind, and the tree yielding fruit, whose seed [was] in itself, after his kind: and God saw that [it was] good.
And the evening and the morning were the third day.
And God said, Let there be lights in the firmament of the heaven to divide the day from the night; and let them be for signs, and for seasons, and for days, and years:
And let them be for lights in the firmament of the heaven to give light upon the earth: and it was so.
And God made two great lights; the greater light to rule the day, and the lesser light to rule the night: [he made] the stars also.
And God set them in the firmament of the heaven to give light upon the earth,
And to rule over the day and over the night, and to divide the light from the darkness: and God saw that [it was] good.
And the evening and the morning were the fourth day.
And God said, Let the waters bring forth abundantly the moving creature that hath life, and fowl [that] may fly above the earth in the open firmament of heaven.
And God created great whales, and every living creature that moveth, which the waters brought forth abundantly, after their kind, and every winged fowl after his kind: and God saw that [it was] good.
And God blessed them, saying, Be fruitful, and multiply, and fill the waters in the seas, and let fowl multiply in the earth.
And the evening and the morning were the fifth day.
And God said, Let the earth bring forth the living creature after his kind, cattle, and creeping thing, and beast of the earth after his kind: and it was so.
And God made the beast of the earth after his kind, and cattle after their kind, and every thing that creepeth upon the earth after his kind: and God saw that [it was] good.
And God said, Let us make man in our image, after our likeness: and let them have dominion over the fish of the sea, and over the fowl of the air, and over the cattle, and over all the earth, and over every creeping thing that creepeth upon the earth.
So God created man in his [own] image, in the image of God created he him; male and female created he them.
And God blessed them, and God said unto them, Be fruitful, and multiply, and replenish the earth, and subdue it: and have dominion over the fish of the sea, and over the fowl of the air, and over every living thing that moveth upon the earth.
And God said, Behold, I have given you every herb bearing seed, which [is] upon the face of all the earth, and every tree, in the which [is] the fruit of a tree yielding seed; to you it shall be for meat.
And to every beast of the earth, and to every fowl of the air, and to every thing that creepeth upon the earth, wherein [there is] life, [I have given] every green herb for meat: and it was so.
And God saw every thing that he had made, and, behold, [it was] very good. And the evening and the morning were the sixth day.
"""
        ifile.writelines(text)
        ifile.close()

    def teardown_class(cls):
        os.unlink(cls.ifile_name)
        os.unlink(cls.ofile_name)

    def setup_method(self):
        self.ofile = open(self.ofile_name, 'wb')

    def get_result(self):
        with open(self.ofile_name, 'rb') as f:
            read_data = f.read()
            f.close()
        return read_data

    def get_correct_data(self, cmd, args):
        p = Popen([cmd] + args, stdout=PIPE)
        data = p.stdout.read()
        p.stdout.close()
        p.wait()
        return data


class TestGrep(Mixin):

    """ilncowEABCRqv"""

    def test_ignore_case(self):
        """ -i option """
        app = Grep(output_file=self.ofile)
        args = ['-i', 'Heaven', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_file_with_matches(self):
        """ -l option """
        app = Grep(output_file=self.ofile)
        args = ['-l', 'earth', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_file_with_matches_no(self):
        """ -l option """
        app = Grep(output_file=self.ofile)
        args = ['-l', 'not exists', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_line_number(self):
        """ -n option """
        app = Grep(output_file=self.ofile)
        args = ['-n', 'firmament', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_count(self):
        """ -c option """
        app = Grep(output_file=self.ofile)
        args = ['-c', 'God', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_only_matching(self):
        """ -o option """
        app = Grep(output_file=self.ofile)
        args = ['-o', 'water', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_word_regexp(self):
        """ -w option """
        app = Grep(output_file=self.ofile)
        args = ['-ow', 'day', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_with_filename(self):
        """ -H option """
        app = Grep(output_file=self.ofile)
        args = ['-H', 'evening', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_no_filename(self):
        """ -h option """
        app = Grep(output_file=self.ofile)
        args = ['-h', 'morning', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_opt_n_o(self):
        """ -n with -o options """
        app = Grep(output_file=self.ofile)
        args = ['-no', 'God', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_opt_n_H(self):
        """ -n with -H options """
        app = Grep(output_file=self.ofile)
        args = ['-nH', 'God', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_opt_o_H(self):
        """ -o with -H options """
        app = Grep(output_file=self.ofile)
        args = ['-oH', 'God', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_opt_n_o_H(self):
        """ -n with -o and -H options """
        app = Grep(output_file=self.ofile)
        args = ['-noH', 'God', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    def test_block_size(self):
        app = Grep(bs=1, output_file=self.ofile)
        args = ['-l', 'water', self.ifile_name]
        app.run(args)
        read_data = self.get_result()
        correct_data = self.get_correct_data('grep', args)
        assert read_data == correct_data

    # def test_after(self):
    #     """ -A option """
    #     app = Grep(output_file=self.ofile)
    #     args = ['-A1', 'water', self.ifile_name]
    #     app.run(args)
    #     read_data = self.get_result()
    #     correct_data = self.get_correct_data('grep', args)
    #     assert read_data == correct_data

    # def test_before(self):
    #     """ -B option """
    #     app = Grep(output_file=self.ofile)
    #     args = ['-B1', 'water', self.ifile_name]
    #     app.run(args)
    #     read_data = self.get_result()
    #     correct_data = self.get_correct_data('grep', args)
    #     assert read_data == correct_data

    # def test_context(self):
    #     """ -C option """
    #     app = Grep(output_file=self.ofile)
    #     args = ['-C1', 'water', self.ifile_name]
    #     app.run(args)
    #     read_data = self.get_result()
    #     correct_data = self.get_correct_data('grep', args)
    #     assert read_data == correct_data

    #     self.setup_method()
    #     app = Grep(output_file=self.ofile)
    #     args = ['-C2', 'water', self.ifile_name]
    #     app.run(args)
    #     read_data = self.get_result()
    #     correct_data = self.get_correct_data('grep', args)
    #     assert read_data == correct_data

    # def test_after_before_context(self):
    #     """ -A, -B and C options """
    #     app = Grep(output_file=self.ofile)
    #     args = ['-A1', '-B2', '-C3', 'water', self.ifile_name]
    #     app.run(args)
    #     read_data = self.get_result()
    #     correct_data = self.get_correct_data('grep', args)
    #     assert read_data == correct_data
