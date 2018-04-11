from collections import namedtuple
from urllib.parse import urljoin
from urllib.request import urlopen

from fuzzywuzzy import fuzz
from sphinx.util.inventory import InventoryFile

from util import DEFAULT_REPO, GITHUB_URL

DOCS_URL = "https://telethon.readthedocs.io/en/latest/"
API_URL = "https://lonamiwebs.github.io/Telethon/"
PROJECT_URL = urljoin(GITHUB_URL, DEFAULT_REPO + '/')

Doc = namedtuple('Doc', 'short_name, full_name, type, url')


class BestHandler:
    def __init__(self):
        self.items = []

    def add(self, score, item):
        self.items.append((score, item))

    def to_list(self, amount, threshold):
        items = sorted(self.items, key=lambda x: x[0])
        items = [item for score, item in reversed(items[-amount:]) if score > threshold]
        return items if len(items) > 0 else None


class Search:
    def __init__(self):
        self._docs = {}
        self.parse_docs()

    def parse_docs(self):
        docs_data = urlopen(urljoin(DOCS_URL, "objects.inv"))
        self._docs = InventoryFile.load(docs_data, DOCS_URL, urljoin)

    def docs(self, query, amount=3, threshold=80):
        query = list(reversed(query.split('.')))
        besth = BestHandler()
        best = (0, None)

        for typ, items in self._docs.items():
            if typ not in ['py:staticmethod', 'py:exception', 'py:method', 'py:module', 'py:class', 'py:attribute',
                           'py:data', 'py:function']:
                continue
            for name, item in items.items():
                name_bits = name.split('.')
                dot_split = zip(query, reversed(name_bits))
                score = 0
                for s, n in dot_split:
                    score += fuzz.ratio(s, n)
                score += fuzz.ratio(query, name)

                # These values are basically random :/
                if typ == 'py:module':
                    score *= 0.75
                if typ == 'py:class':
                    score *= 1.10
                if typ == 'py:attribute':
                    score *= 0.85

                if score > best[0]:
                    short_name = name_bits[1:]

                    try:
                        if name_bits[1].lower() == name_bits[2].lower():
                            short_name = name_bits[2:]
                    except IndexError:
                        pass
                    best = (score, Doc('.'.join(short_name), name, typ[3:], item[2]))
                    besth.add(score, Doc('.'.join(short_name), name, typ[3:], item[2]))

        return besth.to_list(amount, threshold)

    def api_docs(self, query, all_list):
        result_list = []

        for key, value in all_list.items():
            res = self.get_search_array(value[0], value[1], query)[:10]
            for i, des in enumerate(res[0]):
                result_list.append(Doc(des, des, key, f"{API_URL}{res[1][i]}"))

        return result_list

    def get_search_array(self, origins, originus, query):
        destination = []
        destinationu = []

        for i, origin in enumerate(origins):
            if self.find(origin.lower(), query):
                destination.append(origin)
                destinationu.append(originus[i])

        return [destination, destinationu]

    @staticmethod
    def find(haystack, needle):
        if len(needle) == 0:
            return True
        hi = 0
        ni = 0
        while True:
            while ord(needle[ni]) < ord('a') or ord(needle[ni]) > ord('z'):
                ni += 1
                if ni == len(needle):
                    return True
            while haystack[hi] != needle[ni]:
                hi += 1
                if hi == len(haystack):
                    return False
            hi += 1
            ni += 1
            if ni == len(needle):
                return True
            if hi == len(haystack):
                return False


search = Search()
