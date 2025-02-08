@dataclass
class ProductMetadata(object):
    """
    Metadata for a Stripe product.
    """

    stripe_id: str
    name: str
    features: List[str]
    description: str = ""
    is_default: bool = False


PREMIUM = ProductMetadata(
    stripe_id="prod_GqvWupK96UxUaG",
    name="Premium",
    description="For small businesses and teams",
    is_default=False,
    features=[
        features.UNLIMITED_WIDGETS,
        features.LUDICROUS_MODE,
        features.PRIORITY_SUPPORT,
    ],
)


def ludicrous_mode_enabled(user):
    return features.LUDICROUS_MODE in user.product.metadata.features
