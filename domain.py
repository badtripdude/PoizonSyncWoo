class SKU:
    def __init__(self,
                 id_: int = None,
                 sku_code: str = None,
                 regular_price: int = None,
                 vars_: dict[str:str] = None):
        if not vars_:
            vars_ = {}
        self.vars = vars_
        self.regular_price = regular_price
        self.sku_code = sku_code
        self.id = id_


class SPU:
    def __init__(self, id_: int, title: str = None, desc: str = None,
                 article_code: str = None, min_price: int = None,
                 max_price: int = None, skus: list[SKU] = None,
                 images: list[str] = None, category_id: int = None,
                 source_url: str = None, brand_name: str = None,
                 specs:list=None):
        self.brand_name = brand_name
        self.source_url = source_url
        if skus is None:
            skus = []
        if specs is None:
            specs = []
        if images is None:
            images = []
        self.specs = specs
        self.images = images
        self.max_price = max_price
        self.min_price = min_price
        self.article_code = article_code
        self.desc = desc
        self.title = title
        self.id_ = id_
        self.skus: list = skus
        self.category_id = category_id

    def add_sku(self, sku: SKU):
        self.skus.append(sku)


class ScoringService:
    def __init__(self):
        self.config = {
            "bonus_keywords": ["爆款", "热卖", "经典"],
        }

    def score(self, spu: SPU) -> int:
        score = 0

        score += 2 * len(spu.skus)

        score += min(len(spu.images), 5)

        if spu.min_price and spu.min_price > 400:
            score += 1

        if any(word in spu.title for word in self.config["bonus_keywords"]):
            score += 1

        return score


class SPUCollector:
    def __init__(self, spus: list[SPU] = None):
        if not spus:
            spus = []
        self.spus = spus

    def add_spu(self, spu: SPU):
        self.spus.append(spu)

    def top_n(self, scoring_service: ScoringService, n: int = 50) -> list[SPU]:
        return sorted(self.spus, key=lambda spu: scoring_service.score(spu), reverse=True)[:n]


# @lru_cache(maxsize=256, )
async def calculate_price(sku_regular_price: int, *, mode: str, x: int, y: int, z: int) -> int:
    # TODO: вынести app layer
    price = sku_regular_price // 100
    if mode == 'thepoizon':
        price = round(price * 0.8)
    elif mode == 'dewu':
        price = (price - 2632) // 15.82

        price = \
            round(
                price +
                x +
                y +
                z
            )
    return price
