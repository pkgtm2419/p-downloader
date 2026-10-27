import unittest
from core.spider import WebSpider

class TestWebSpider(unittest.TestCase):
    def test_spider_initialization_and_extensions(self):
        spider = WebSpider(
            start_url="https://example.com/gallery",
            max_depth=2,
            target_categories=["video", "archives"],
            custom_extensions={".iso", ".custom"}
        )
        self.assertEqual(spider.max_depth, 2)
        self.assertEqual(spider.start_domain, "example.com")
        self.assertIn(".mp4", spider.target_extensions)
        self.assertIn(".zip", spider.target_extensions)
        self.assertIn(".iso", spider.target_extensions)
        self.assertIn(".custom", spider.target_extensions)

    def test_depth_clamping(self):
        s1 = WebSpider("https://example.com", max_depth=0)
        self.assertEqual(s1.max_depth, 1)

        s2 = WebSpider("https://example.com", max_depth=10)
        self.assertEqual(s2.max_depth, 5)

if __name__ == "__main__":
    unittest.main()
