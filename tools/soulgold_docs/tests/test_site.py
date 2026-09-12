from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.soulgold_docs import site


class StaticSiteRefreshTests(unittest.TestCase):
    def test_refresh_preserves_data_sprites_and_detail_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            (source / "index.html").write_text('<head><base href="./">\n  </head><span class="header-version">{{LATEST_VERSION}}</span><script src="assets/app.js?v=test-build"></script>')
            (source / "version.json").write_text('{"latestVersion":"v1.1.3"}')
            header = root / "version.h"
            header.write_text('#define DISPLAY_VERSION "v1.2.0"\n')
            (source / "guides").mkdir()
            (source / "guides" / "example.md").write_text("Authoring source")
            preserved = ["data/common.json", "sprites/pokemon/bulbasaur.png", "guides/image.png"]
            for relative in preserved:
                path = output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"existing data")
            detail = output / "pokedex" / "bulbasaur" / "index.html"
            detail.parent.mkdir(parents=True)
            detail.write_text("old UI")
            guide_detail = output / "guides" / "example" / "index.html"
            guide_detail.parent.mkdir(parents=True)
            guide_detail.write_text("old UI")

            with patch.object(site, "SRC_DIR", source), patch.object(site, "OUT_DIR", output), patch.object(site, "VERSION_H", header):
                site.refresh_static_site()

            for relative in preserved:
                self.assertEqual((output / relative).read_bytes(), b"existing data")
            self.assertIn('<base href="../../">', detail.read_text())
            self.assertIn("assets/app.js?v=test-build", detail.read_text())
            self.assertIn('<span class="header-version">v1.2.0</span>', detail.read_text())
            self.assertIn('href="data/species-details/bulbasaur.json?v=test-build"', detail.read_text())
            self.assertIn('href="data/species-meta.json?v=test-build"', detail.read_text())
            self.assertIn('href="data/guides.json?v=test-build"', guide_detail.read_text())
            self.assertNotIn('href="data/species.json', guide_detail.read_text())
            for route in site.SECTION_ROUTES:
                section_html = (output / route / "index.html").read_text()
                self.assertIn('<base href="../">', section_html)
                self.assertIn('<span class="header-version">v1.2.0</span>', section_html)
                for filename in site.SECTION_PRELOADS[route]:
                    self.assertIn(f'href="data/{filename}?v=test-build"', section_html)
            self.assertEqual((output / "version.json").read_text(), (source / "version.json").read_text())
            self.assertEqual(json.loads((output / "version.json").read_text()), {"latestVersion": "v1.2.0"})
            self.assertFalse((output / "guides" / "example.md").exists())

            # Full builds use the same header source, including subsequent bumps.
            header.write_text('#define DISPLAY_VERSION "v1.2.1" // Release version\n')
            with patch.object(site, "SRC_DIR", source), patch.object(site, "OUT_DIR", output), patch.object(site, "VERSION_H", header):
                site.prepare_output_tree()
            self.assertEqual(json.loads((output / "version.json").read_text()), {"latestVersion": "v1.2.1"})
            self.assertEqual((output / "version.json").read_text(), (source / "version.json").read_text())
            self.assertIn('<span class="header-version">v1.2.1</span>', (output / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
