
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import HSTORE, INET, JSONB, CITEXT, UUID, ARRAY

# HSTORE stores key-value pair of strings, useful for flexible metadata fields. 
# Both key and value must be strings and the HSTORE extension must be enabled in Postgres.
HSTORE_TYPE = HSTORE() 

# INET stores IPv4 or IPv6 addresses, useful for logging client IPs.
INET_TYPE = INET()

# JSONB stores JSON data in a binary format, allowing for efficient querying and indexing of JSON fields.
JSONB_TYPE = JSONB()

# CITEXT is a case-insensitive text type, useful for fields like email addresses where case should not matter.
# You need to enable the CITEXT extension in Postgres to use this type.
CITEXT_TYPE = CITEXT()

# UUID stores universally unique identifiers, useful for primary keys or any field that benefits from a unique identifier.
UUID_TYPE = UUID(as_uuid=True)  # Store as native UUID type in Postgres, returns Python uuid.UUID objects

# ARRAY stores an array of a specified type, useful for fields that need to store multiple values in a single column.
# You can specify the type of the array elements, e.g., ARRAY(Integer) for an array of integers.
TEXT_ARRAY_TYPE = ARRAY(Text)  