from enum import Enum
class QueryIntent(str, Enum):
    DETAIL = "detail"
    SIMILARITY = "similarity"
    FILTER = "filter"
    LIST = "list"
    DEFAULT = "default"