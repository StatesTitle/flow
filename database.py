import collections
import pymssql

from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from settings import (
    RESWARE_DATABASE_NAME, RESWARE_DATABASE_PASSWORD, RESWARE_DATABASE_PORT,
    RESWARE_DATABASE_SERVER, RESWARE_DATABASE_USER, ACTION_LIST_DEF_ID
)
@contextmanager
def _connect_to_db():
    with pymssql.connect(
        RESWARE_DATABASE_SERVER,
        RESWARE_DATABASE_USER,
        RESWARE_DATABASE_PASSWORD,
        RESWARE_DATABASE_NAME,
        port=RESWARE_DATABASE_PORT,
        as_dict=True
    ) as conn:
        yield conn


def tableclass(table, lookup=None, one_to_many=False, **kwargs):
    def wrap(cls, lookup=lookup):
        dataclass(cls, **kwargs)
        cls.table = table
        if lookup is None:
            if any((f.name == 'id' for f in fields(cls))):
                lookup = 'id'
            else:
                raise Exception(f"Pass a lookup field into tableclass on {cls} if there isn't an id field")

        if isinstance(lookup, str):
            def create_key(self):
                return getattr(self, lookup)
        else:
            def create_key(self):
                return tuple((getattr(self, field) for field in lookup))

        cls.create_key = create_key
        cls.one_to_many = one_to_many
        return cls
    return wrap


def col(name, parser=None, nullable=False):
    metadata = {'column': name, 'nullable': nullable}
    if parser:
        metadata['parser'] = parser
    return field(metadata=metadata)


class ColumnMissing(Exception):
    pass

class ParsingFailed(Exception):
    pass


def parse_col(dclass, field, row):
    if field.metadata['column'] not in row:
        raise ColumnMissing(f'{dclass} field {field.name} expected a column named {field.metadata["column"]} in the row {row}')
    val = row[field.metadata['column']]
    parser = field.metadata.get('parser', field.type)
    if val is None:
        if not field.metadata['nullable']:
            raise ColumnMissing(f'{dclass} field {field.name} expected a column named {field.metadata["column"]} in the row but got NULL from the db')
        if parser == field.type:
            return None
    try:
        return parser(val)
    except ColumnMissing:
        raise
    except Exception as e:
        raise ParsingFailed(f'{dclass} field {field.name} parser {parser} blew up on "{val}"') from e


def create_from_db(dclass, row):
    return dclass(*[parse_col(dclass, f, row) for f in fields(dclass) if 'column' in f.metadata])


def load(conn, cls):
    columns = ', '.join([f.metadata['column'] for f in fields(cls) if 'column' in f.metadata])
    query = f'SELECT {columns} FROM {cls.table}'
    results = {}
    if cls.one_to_many:
        results = collections.defaultdict(list)
    with conn.cursor() as cursor:
        cursor.execute(query)
        for r in cursor.fetchall():
            instance = create_from_db(cls, r)
            key = cls.create_key(instance)
            if cls.one_to_many:
                results[key].append(instance)
            else:
                assert key not in results, f"Was expecting a single item for {key} but got {instance} and {results[key]}"
                results[key] = instance
        return results
