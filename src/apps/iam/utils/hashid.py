from hashids import Hashids

hashids = Hashids(salt="your_salt_here", min_length=8)

def encode_id(id: int) -> str:
    return hashids.encode(id)

def decode_id(hashid: str) -> int| None:
    decoded = hashids.decode(hashid)
    return decoded[0] if decoded else None