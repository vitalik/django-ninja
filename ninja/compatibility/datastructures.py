from collections.abc import Mapping


def _destruct_iterable_mapping_values(data):
    for i, elem in enumerate(data):
        if len(elem) != 2:
            raise ValueError(
                "dictionary update sequence element #{} has "
                "length {}; 2 is required.".format(i, len(elem))
            )
        if not isinstance(elem[0], str):
            raise ValueError(
                "Element key %r invalid, only strings are allowed" % elem[0]
            )
        yield tuple(elem)


class CaseInsensitiveMapping(Mapping):
    """
    Mapping allowing case-insensitive key lookups. Original case of keys is
    preserved for iteration and string representation.
    Example::
        >>> ci_map = CaseInsensitiveMapping({'name': 'Jane'})
        >>> ci_map['Name']
        Jane
        >>> ci_map['NAME']
        Jane
        >>> ci_map['name']
        Jane
        >>> ci_map  # original case preserved
        {'name': 'Jane'}
    """

    def __init__(self, data):
        if not isinstance(data, Mapping):
            data = {k: v for k, v in _destruct_iterable_mapping_values(data)}
        self._store = {k.lower(): (k, v) for k, v in data.items()}

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __len__(self):
        return len(self._store)

    def __eq__(self, other):
        return isinstance(other, Mapping) and {
            k.lower(): v for k, v in self.items()
        } == {k.lower(): v for k, v in other.items()}

    def __iter__(self):
        return (original_key for original_key, value in self._store.values())

    def __repr__(self):
        return repr({key: value for key, value in self._store.values()})

    def copy(self):
        return self
