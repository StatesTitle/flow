import collections
import io
import pymssql
import sys

import paramiko
import sshtunnel
from dataclasses import dataclass, field, fields
from sshtunnel import SSHTunnelForwarder

from settings import (
    RESWARE_DATABASE_NAME, RESWARE_DATABASE_PASSWORD, RESWARE_DATABASE_PORT,
    RESWARE_DATABASE_SERVER, RESWARE_DATABASE_USER,
    SSH_TUNNEL_ENABLED, SSH_SERVER_HOST, SSH_SERVER_PORT, SSH_USERNAME, SSH_PRIVATE_KEY, SSH_REMOTE_BIND_ADDRESS,
    SSH_REMOTE_BIND_PORT)


class ResWareDatabaseConnection:
    def __enter__(self):
        # SSH tunnel is required to connect to a SQL server running behind a firewall
        self.tunnel = None
        if SSH_TUNNEL_ENABLED:
            # Paramiko expects the key to be enclosed in a tagged block, but that's obnoxious to encode in .env and
            # Heroku configs. If we don't have it in the config, wrap it here.
            key = SSH_PRIVATE_KEY
            if not key.startswith('-----'):
                key = f'-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----'''

            self.tunnel = SSHTunnelForwarder(
                (SSH_SERVER_HOST, SSH_SERVER_PORT),
                ssh_username=SSH_USERNAME,
                ssh_private_key=paramiko.RSAKey.from_private_key(io.StringIO(key)),
                remote_bind_address=(SSH_REMOTE_BIND_ADDRESS, SSH_REMOTE_BIND_PORT),
                # If the tunnel is failing, switch this to TRACE to figure out what it's trying. Checking the BitVise
                # logs on the server can be helpful, too
                logger=sshtunnel.create_logger(loglevel='WARNING')
            )
            self.tunnel.start()

            # if an ssh tunnel is used, bind to the tunnel's localhost port
            try:
                self._db_connect('127.0.0.1', self.tunnel.local_bind_port)
            except:
                # Always close the tunnel if it's open so we don't leave a thread dangling
                self._close_tunnel(True)
                raise
        else:
            self._db_connect(
                RESWARE_DATABASE_SERVER,
                RESWARE_DATABASE_PORT
            )

        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        connection_close_raised = True
        try:
            self.connection.close()
            connection_close_raised = False
        finally:
            self._close_tunnel(connection_close_raised)

    def _close_tunnel(self, already_handling_exception):
        # close ssh tunnel if it was created
        if not self.tunnel:
            return
        try:
            self.tunnel.close()
        except:
            if already_handling_exception:
                print("Hit an exception closing the ssh tunnel, but we were already handling an exception. Swallowing the tunnel closing exception", file=sys.stderr)
            else:
                raise

    def _db_connect(self, host, port):
        # due to a pymssql bug, the database name cannot be specified on init if an ssh tunnel is used
        # instead, it must be given to the connection's cursor object before a query
        # this could also be an issue with paramiko, which sshtunnel uses for implementation
        # for more details, see: https://github.com/pahaz/sshtunnel/issues/99
        self.connection = pymssql.connect(
            host=host,
            user=RESWARE_DATABASE_USER,
            password=RESWARE_DATABASE_PASSWORD,
            port=port,
            as_dict=True
        )
        with self.connection.cursor() as cursor:
            cursor.execute(f"USE {RESWARE_DATABASE_NAME}")


def tableclass(table, lookup=None, one_to_many=False, **kwargs):
    """Marks a dataclass as loadable from a specified SQL table"""
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
    """Marks a tableclass field as coming rom the named column on the table of the tableclass"""
    metadata = {'column': name, 'nullable': nullable}
    if parser:
        metadata['parser'] = parser
    return field(metadata=metadata)


class ColumnMissing(Exception):
    """Raised when the col for a field on a tableclass isn't in a fetched row"""
    pass


class ParsingFailed(Exception):
    """Raised when the parser on a col raises an exception on a value found in a row for the col name"""
    pass


def _parse_col(dclass, field, row):
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


def _create_from_db(dclass, row):
    return dclass(*[_parse_col(dclass, f, row) for f in fields(dclass) if 'column' in f.metadata])


def load(conn, tablecls):
    """Returns a dict of the lookup of tablecls to instances of it for all rows in its table

    If one_to_many is set on the tableclass, the returned dict will be from the key on the instance to a list of
    instances with that same key

    If lookup is specified, it's expected to be a fieldname or a tuple of fieldnames to create the keys for the returned
    dictionary

    If lookup isn't specified, it's assumed to be 'id'"""

    columns = ', '.join([f.metadata['column'] for f in fields(tablecls) if 'column' in f.metadata])
    query = f'SELECT {columns} FROM {tablecls.table}'
    results = {}
    if tablecls.one_to_many:
        results = collections.defaultdict(list)
    with conn.cursor() as cursor:
        cursor.execute(query)
        for r in cursor.fetchall():
            instance = _create_from_db(tablecls, r)
            key = tablecls.create_key(instance)
            if tablecls.one_to_many:
                results[key].append(instance)
            else:
                assert key not in results, f"Was expecting a single item for {key} but got {instance} and {results[key]}"
                results[key] = instance
        return results
