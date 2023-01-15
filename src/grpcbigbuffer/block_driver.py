import json
import os.path
from typing import Union, List, Tuple, Dict

from grpcbigbuffer.client import read_multiblock_directory
from grpcbigbuffer.disk_stream import encode_bytes

WITHOUT_BLOCK_POINTERS_FILE_NAME = 'wbp.bin'
METADATA_FILE_NAME = '_.json'
BLOCK_LENGTH = 36


def transform_dictionary_format(d: Dict[str, List[int]]) -> Dict[int, List[str]]:
    return {valor: [clave for clave in d if valor in d[clave]] for valor in
            set([valor for clave in d for valor in d[clave]])}


def get_pruned_block_length(block_name: str) -> int:
    block_size: int = os.path.getsize(block_name)
    return block_size + len(encode_bytes(block_size)) - BLOCK_LENGTH - len(encode_bytes(BLOCK_LENGTH))


def get_position_length(varint_pos: int, buffer: bytes) -> int:
    """
    Returns the value of the varint at the given position in the Protobuf buffer.
    """
    value = 0
    shift = 0
    index = varint_pos
    while True:
        byte = buffer[index]
        value |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
        index += 1
    return value


def recalculate_block_length(position: int, blocks_names: List[str], buffer: bytes) -> int:
    return get_position_length(position, buffer) - sum([
        get_pruned_block_length(block_name) for block_name in blocks_names
    ])


def set_varint_value(varint_pos: int, buffer: bytes, new_value: int) -> bytes:
    """
    Sets the value of the varint at the given position in the Protobuf buffer to the given value and returns the modified buffer.
    """
    # Convert the given value to a varint and store it in a bytes object
    varint_bytes = []
    while True:
        byte = new_value & 0x7F
        new_value >>= 7
        varint_bytes.append(byte | 0x80 if new_value > 0 else byte)
        if new_value == 0:
            break
    varint_bytes = bytes(varint_bytes)

    # Calculate the number of bytes to remove from the original varint
    original_varint_bytes = buffer[varint_pos:]
    original_varint_length = 0
    while (original_varint_bytes[original_varint_length] & 0x80) != 0:
        original_varint_length += 1
    original_varint_length += 1

    # Remove the original varint and append the new one
    return buffer[:varint_pos] + varint_bytes + buffer[varint_pos + original_varint_length:]


def generate_new_buffer(lengths: Dict[int, int], buffer: bytes) -> bytes:
    for varint_pos, new_value in lengths.items():
        buffer = set_varint_value(varint_pos, buffer, new_value)

    return buffer


def generate_wbp_file(dirname: str):
    with open(dirname + '/' + METADATA_FILE_NAME, 'r') as f:
        _json: List[Union[
            int,
            Tuple[str, List[int]]
        ]] = json.load(f)

    buffer = b''.join([i for i in read_multiblock_directory(dirname)])

    blocks: Dict[str, List[int]] = {t[0]: t[1] for t in _json if type(t) == list}

    lengths_with_pointers: Dict[int, List[str]] = transform_dictionary_format(blocks)

    recalculated_lengths: Dict[int, int] = {
        length_position: recalculate_block_length(length_position, blocks_names, buffer)
        for length_position, blocks_names in lengths_with_pointers.items()
    }

    print('\n_json -> ', _json)
    print('\nbuffer wihtout blocks -< ', buffer)
    print('\nblocks -< ', blocks)
    print('\nlengths_wth pointers -> ', lengths_with_pointers)
    print('\nrecalculated lengths -> ', recalculated_lengths)

    with open(dirname + '/' + WITHOUT_BLOCK_POINTERS_FILE_NAME, 'wb') as f:
        f.write(
            generate_new_buffer(recalculated_lengths, buffer)
        )
