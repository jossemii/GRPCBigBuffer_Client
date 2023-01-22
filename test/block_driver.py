import os
import sys, unittest

sys.path.append('../src/')
from grpcbigbuffer import buffer_pb2
from grpcbigbuffer.block_builder import build_multiblock, get_position_length
from grpcbigbuffer.client import Enviroment


class TestGetVarintValue(unittest.TestCase):
    def test_simple_varint(self):
        # Test a simple varint with a single byte
        buffer = b"\x7F"
        value = get_position_length(0, buffer)
        self.assertEqual(value, 127)

    def test_multi_byte_varint(self):
        # Test a varint with multiple bytes
        buffer = b"\xC0\x03"
        value = get_position_length(0, buffer)
        self.assertEqual(value, 448)

    def test_max_varint(self):
        # Test the maximum varint value (2**64 - 1)
        buffer = b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x01"
        value = get_position_length(0, buffer)
        self.assertEqual(value, 18446744073709551615)

    def test_varint_at_position(self):
        # Test a varint at a non-zero position in the buffer
        buffer = b"\x00\x00\xC0\x03"
        value = get_position_length(2, buffer)
        self.assertEqual(value, 448)

    def test_generate_wbp_file(self):
        # Assuming that the build_multiblock_directory() function works correctly (tests/block_builder.py is OK)
        from grpcbigbuffer.test_pb2 import Test

        block = buffer_pb2.Buffer.Block()
        h = buffer_pb2.Buffer.Block.Hash()
        h.type = Enviroment.hash_type
        h.value = b'sha512'
        block.hashes.append(h)

        block2 = buffer_pb2.Buffer.Block()
        h = buffer_pb2.Buffer.Block.Hash()
        h.type = Enviroment.hash_type
        h.value = b'sha256'
        block2.hashes.append(h)

        block3 = buffer_pb2.Buffer.Block()
        h = buffer_pb2.Buffer.Block.Hash()
        h.type = Enviroment.hash_type
        h.value = b'sha3256'
        block3.hashes.append(h)

        a = Test()
        a.t1 = b''.join([b'bt1' for i in range(100)])
        a.t2 = block.SerializeToString()

        b = Test()
        b.t1 = block2.SerializeToString()
        b.t2 = b''.join([b'bt2' for i in range(100)])
        b.t3.CopyFrom(a)

        c = Test()
        c.t1 = b''.join([b'ct1' for i in range(100)])
        c.t2 = block3.SerializeToString()

        _object = Test()
        _object.t1 = b''.join([b'mc1' for i in range(100)])
        _object.t2 = b''.join([b'mc2' for i in range(100)])
        _object.t4.append(b)
        _object.t4.append(c)

        object_id, cache_dir = build_multiblock(
            pf_object_with_block_pointers=_object,
            blocks=[b'sha256', b'sha512', b'sha3256']
        )

        # Test generate_wbp_file
        from grpcbigbuffer.block_driver import generate_wbp_file
        os.system('rm ' + cache_dir + '/wbp.bin')
        generate_wbp_file(cache_dir)

        generated = Test()
        with open(cache_dir + '/wbp.bin', 'rb') as f:
            generated.ParseFromString(
                f.read()
            )

        self.assertEqual(
            _object,
            generated
        )


if __name__ == "__main__":
    os.system('rm -rf __cache__/*')
    unittest.main()
