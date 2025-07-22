import utils
from application.services import BrandNormalizer
from domain import SPU, SKU


# from infrastracture.thepoizon_client import PoizonSPU


class SPUMapper:
    RU_ENG = {'размер': 'size', 'версия': 'version'}

    @staticmethod
    def from_domain_to_woocomerce(spu: SPU) -> tuple:
        spu_data = {
            "slug": utils.extract_slug(spu.source_url),
            "sku": spu.article_code,
            'spu_id': spu.id_,
            "name": spu.title,
            "description": spu.desc,
            "images": [{'src': url_image} for url_image in spu.images],
            "brand": BrandNormalizer.normalize_brand(raw_brand=spu.brand_name,
                                                     title=spu.title)
        }
        variations = []
        for sku in spu.skus:
            eu_size = sku.vars.get('eu_size', None)
            ru_size = sku.vars.get('ru_size', None)
            attrs = []
            if eu_size:
                attrs.append({
                    'name': 'pa_eu_size',
                    'option': eu_size,
                })
            # if ru_size:
            #     attrs.append({'name': 'ru_size',
            #                   'option': ru_size,
            #                   })
            variations.append({
                "regular_price": f'{sku.regular_price}',
                "sku": f"{spu.article_code}-{sku.sku_code}",
                "attributes": attrs
            })
        return spu_data, variations

    @staticmethod
    def from_poizon_to_domain(data: dict) -> SPU:
        article_number = [prop.get("value") for prop in data.get('baseProperties', []) if
                          prop.get('itemType') == 'ARTICLE_NUMBER']
        d_spu = SPU(title=data.get('shareInfo', {}).get('shareTitle'),
                    desc=None,
                    id_=data.get('buyDialogModel', {}).get('detail', {}).get('spuId'),
                    max_price=None,
                    min_price=data.get('price', {}).get('money', {}).get('minUnitVal'),
                    images=[image.get('url') for image in data.get('imageModels', []) if not image.get('modelWear', )],
                    article_code=article_number[0] if article_number else None,
                    category_id=data.get('buyDialogModel', {}).get('detail', {}).get('categoryId', None),
                    source_url=data.get('shareInfo', {}).get('shareUrl'),
                    brand_name=data.get('brandItemsModel', {}).get('brandName', ''),
                    )
        if d_spu.brand_name == '':
            d_spu.brand_name = None
        for pz_sku in data.get('buyDialogModel', {}).get('skus', []):
            vars_ = {}
            for prop in pz_sku.get('properties', []):
                level = prop.get('level')
                prop_val_id = prop.get('propertyValueId')
                for sale_prop in data.get('buyDialogModel', {}).get('saleProperties', []):
                    for prop_ in sale_prop.get('propertyList', []):
                        for prop_item_model in prop_.get('propertyItemModels', {}):
                            if level == sale_prop.get('level') and prop_item_model.get(
                                    'propertyValueId') == prop_val_id:
                                name = prop_item_model['name'].lower()
                                name = SPUMapper.RU_ENG.get(name, name)
                                vars_.update(
                                    {f'{prop_['propertyKey'].lower()}_{name}': prop_item_model['value'], })
            regular_price = pz_sku.get('skuSpeedInfo', [{}])[0].get('speedPrice', {}).get('money', {}).get('minUnitVal')

            if regular_price and 'eu_size' in vars_:
                d_spu.add_sku(SKU(
                    regular_price=regular_price,
                    id_=pz_sku.get('skuId'),
                    vars_=vars_,
                    sku_code=pz_sku.get('skuId'),
                ))
        return d_spu

    # @staticmethod
    # def from_dewu_to_domain(pz_spu: PoizonSPU) -> SPU:
    #     d_spu = SPU(title=utils.remove_chinese_characters(
    #         pz_spu.core.title).strip() if not pz_spu.core.original_title else utils.remove_chinese_characters(
    #         pz_spu.core.original_title).strip(),
    #                 desc=pz_spu.core.description,
    #                 id_=pz_spu.core.spu_id,
    #                 max_price=pz_spu.stock.max_price,
    #                 min_price=pz_spu.stock.min_price,
    #                 images=pz_spu.images.all_images,
    #                 article_code=str(pz_spu.core.article_number),
    #                 )
    #     for pz_sku_id in pz_spu.stock.sku_ids:
    #         d_spu.add_sku(SKU(
    #             regular_price=pz_spu.stock.recommended_prices[pz_sku_id],
    #             id_=pz_sku_id,
    #             vars_=[utils.normalize_variants(pz_spu.stock.sku_to_variant.get(pz_sku_id, []))],
    #             sku_code=pz_sku_id
    #
    #         ))
    #     return d_spu
