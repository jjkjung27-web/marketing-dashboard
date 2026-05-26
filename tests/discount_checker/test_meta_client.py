from unittest.mock import patch, MagicMock
from tools.discount_checker.meta_client import MetaClient, _extract_image_url


def test_returns_none_when_no_ads_found():
    with patch("tools.discount_checker.meta_client.FacebookAdsApi"), \
         patch("tools.discount_checker.meta_client.AdAccount") as mock_account_cls:
        mock_account = MagicMock()
        mock_account_cls.return_value = mock_account
        mock_account.get_ads.return_value = []
        client = MetaClient("token", "act_123")
        result = client.get_creative("ad_name_not_found")
    assert result is None


def test_returns_creative_id_and_image_url():
    with patch("tools.discount_checker.meta_client.FacebookAdsApi"), \
         patch("tools.discount_checker.meta_client.AdAccount") as mock_account_cls, \
         patch("tools.discount_checker.meta_client.AdCreative") as mock_creative_cls:

        mock_account = MagicMock()
        mock_account_cls.return_value = mock_account

        mock_ad = {"name": "test_ad", "creative": {"id": "cid_001"}}
        mock_account.get_ads.return_value = [mock_ad]

        mock_creative_cls.return_value.api_get.return_value = {
            "image_url": "http://example.com/img.jpg"
        }

        client = MetaClient("token", "act_123")
        result = client.get_creative("test_ad")

    assert result == ("cid_001", "http://example.com/img.jpg")


def test_extract_image_url_prefers_image_url():
    creative_data = {"image_url": "http://img.jpg", "thumbnail_url": "http://thumb.jpg"}
    assert _extract_image_url(creative_data) == "http://img.jpg"


def test_extract_image_url_falls_back_to_thumbnail():
    creative_data = {"thumbnail_url": "http://thumb.jpg"}
    assert _extract_image_url(creative_data) == "http://thumb.jpg"


def test_extract_image_url_returns_none_when_missing():
    assert _extract_image_url({}) is None
