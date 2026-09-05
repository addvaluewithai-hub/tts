import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "image-gen" / "client.py"
spec = importlib.util.spec_from_file_location("image_gen_client", MODULE_PATH)
image_gen_client = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = image_gen_client
assert spec.loader is not None
spec.loader.exec_module(image_gen_client)


class ImageGenClientTests(unittest.TestCase):
    def test_default_base_url(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                image_gen_client.base_url(),
                "https://agent.wpaikits.site/v1/workflow/jobs-images",
            )

    def test_env_base_url_override(self):
        with patch.dict(os.environ, {"IMAGE_API_BASE_URL": "https://example.test/root/"}, clear=True):
            self.assertEqual(image_gen_client.base_url(), "https://example.test/root")

    def test_root_relative_status_url_resolves_from_origin(self):
        self.assertEqual(
            image_gen_client.resolve_url(
                "/v1/workflow/jobs-images/jobs/abc",
                base="https://agent.wpaikits.site/v1/workflow/jobs-images",
            ),
            "https://agent.wpaikits.site/v1/workflow/jobs-images/jobs/abc",
        )

    def test_relative_status_url_resolves_under_base(self):
        self.assertEqual(
            image_gen_client.resolve_url(
                "jobs/abc",
                base="https://agent.wpaikits.site/v1/workflow/jobs-images",
            ),
            "https://agent.wpaikits.site/v1/workflow/jobs-images/jobs/abc",
        )

    def test_encode_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.png"
            path.write_bytes(b"hello")
            encoded = image_gen_client.encode_reference(path)
            self.assertEqual(encoded["name"], "sample.png")
            self.assertEqual(encoded["mime"], "image/png")
            self.assertEqual(encoded["data_base64"], "aGVsbG8=")

    def test_batch_validation_and_string_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref = root / "ref.jpg"
            ref.write_bytes(b"jpg")
            request_file = root / "batch.json"
            request_file.write_text(
                json.dumps(
                    {
                        "requests": [
                            {
                                "prompt": "Airport gate",
                                "aspect_ratio": "16:9",
                                "references": [str(ref)],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            requests_data = image_gen_client.load_batch_requests(request_file)
            self.assertEqual(len(requests_data), 1)
            self.assertEqual(requests_data[0]["prompt"], "Airport gate")
            self.assertEqual(requests_data[0]["references"][0]["name"], "ref.jpg")

    def test_large_visual_plan_is_accepted_and_chunked(self):
        with tempfile.TemporaryDirectory() as tmp:
            request_file = Path(tmp) / "batch.json"
            request_file.write_text(
                json.dumps({"requests": [{"prompt": f"shot {i}"} for i in range(32)]}),
                encoding="utf-8",
            )
            requests_data = image_gen_client.load_batch_requests(request_file)
            chunks = image_gen_client.chunked(requests_data)
            self.assertEqual(len(requests_data), 32)
            self.assertEqual([len(chunk) for chunk in chunks], [20, 12])

    def test_chunk_size_cannot_exceed_service_limit(self):
        with self.assertRaises(ValueError):
            image_gen_client.chunked([{"prompt": "x"}], 21)

    def test_collect_child_downloads(self):
        data = {
            "jobs": [
                {"image": {"download_url": "https://example.test/1.png"}},
                {"download_url": "https://example.test/2.png"},
            ]
        }
        self.assertEqual(
            image_gen_client.collect_child_downloads(data),
            ["https://example.test/1.png", "https://example.test/2.png"],
        )


if __name__ == "__main__":
    unittest.main()
