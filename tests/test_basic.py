from mo_testing.fuzzytestcase import FuzzyTestCase, add_error_reporting

from mo_files import URL
from mo_http import http


host = URL("http://localhost:5000")


@add_error_reporting
class TestBasic(FuzzyTestCase):
    def test_version(self):
        response = http.get_json(host / "__version__")
        self.assertTrue(response.source.startswith("https://github.com/klahnakoski/spread-server/tree"))
