import decimal
import requests

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

CHALLONGE_API_URL = "api.challonge.com/v1"
# A global dict for maintaining credentials
_credentials = {
    "user": None,
    "api_key": None,
}

def set_credentials(username, api_key):
    """Set the challonge.com api credentials to use."""
    _credentials["user"] = username
    _credentials["api_key"] = api_key

def get_credentials():
    """Retrieve the challonge.com credentials set with set_credentials()."""
    return _credentials["user"], _credentials["api_key"]

def fetch(method, uri, params_prefix=None, **params):

    params = _prepare_params(params, params_prefix)

    s = requests.Session()    

    # Using basic authentication (the default)
    
    s.auth = (get_credentials())

    # uri's need to be formulated by the individual APIs
    # matches, tournaments and participants.
    
    url = "https://%s/%s.xml" % (CHALLONGE_API_URL, uri)

    response = s.request(method, url, params)

    if not response.ok:
        raise response.raise_for_status()

    # call replace to remove non-breaking spaces, otherwise ElementTree.fromstring will fail.
    return response.text.replace(u'\xa0', u' ')

def fetch_and_parse(method, uri, params_prefix=None, **params):
    """Fetch the given uri and return the root Element of the response."""
    doc = ElementTree.fromstring(fetch(method, uri, params_prefix, **params))
    return _parse(doc)


def _parse(root):
    """Recursively convert an Element into python data types"""
    import dateutil.parser
    if root.tag == "nil-classes":
        return []
    elif root.get("type") == "array":
        return [_parse(child) for child in root]

    d = {}
    for child in root:
        type = child.get("type") or "string"

        if child.get("nil"):
            value = None
        elif type == "boolean":
            value = True if child.text.lower() == "true" else False
        elif type == "datetime":
            value = dateutil.parser.parse(child.text)
        elif type == "decimal":
            value = decimal.Decimal(child.text)
        elif type == "integer":
            value = int(child.text)
        else:
            value = child.text

        d[child.tag] = value
    return d


def _prepare_params(dirty_params, prefix=None):
    """Prepares parameters to be sent to challonge.com.

    The `prefix` can be used to convert parameters with keys that
    look like ("name", "url", "tournament_type") into something like
    ("tournament[name]", "tournament[url]", "tournament[tournament_type]"),
    which is how challonge.com expects parameters describing specific
    objects.

    """
    params = {}
    for k, v in dirty_params.items():
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        elif isinstance(v, bool):
            # challonge.com only accepts lowercase true/false
            v = str(v).lower()

        if prefix:
            params["%s[%s]" % (prefix, k)] = v
        else:
            params[k] = v

    return params
