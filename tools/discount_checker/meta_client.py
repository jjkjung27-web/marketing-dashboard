from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.api import FacebookAdsApi

from tools.discount_checker.cache import Cache


def _extract_image_url(creative_data: dict) -> str | None:
    return creative_data.get("image_url") or creative_data.get("thumbnail_url")


class MetaClient:
    def __init__(self, access_token: str, ad_account_id: str, cache: Cache):
        FacebookAdsApi.init(access_token=access_token)
        self._account = AdAccount(ad_account_id)
        self._cache = cache

    def get_creative(self, ad_name: str) -> tuple[str, str] | None:
        """Returns (creative_id, image_url) or None if not found."""
        ads = self._account.get_ads(
            fields=["name", "creative"],
            params={
                "filtering": [{"field": "name", "operator": "EQUAL", "value": ad_name}]
            },
        )
        if not ads:
            return None

        creative_id = ads[0]["creative"]["id"]
        creative_data = AdCreative(creative_id).api_get(
            fields=["image_url", "thumbnail_url"]
        )
        image_url = _extract_image_url(creative_data)
        if not image_url:
            return None

        return creative_id, image_url
