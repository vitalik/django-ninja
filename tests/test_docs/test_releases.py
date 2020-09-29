from os.path import join, dirname
import ninja


def test_releases_page():
    releses_file = join(dirname(__file__), "../../docs/docs/releases.md")
    with open(releses_file, "r") as f:
        page_contents = f.read()
    assert ninja.__version__ in page_contents
