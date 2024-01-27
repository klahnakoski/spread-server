from jx_sqlite.sqlite import Sqlite
from mo_testing.fuzzytestcase import FuzzyTestCase, add_error_reporting

from mo_files import URL, File
from mo_http import http

TEST_DATABASE = "tests/resources/chinook.sql"
host = URL("http://localhost:5000")


@add_error_reporting
class TestBasic(FuzzyTestCase):
    def __init__(self, *args, **kwargs):
        FuzzyTestCase.__init__(self, *args, **kwargs)
        self.db = None

    def setUp(self):
        self.db = Sqlite(debug=True)
        self.db.read_sql(TEST_DATABASE)

    def test_simple_query(self):
        response = http.post(host / "query", content="SELECT * FROM chinook.employees")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.headers["Location"].endswith(".sqlite"))
