from dataclasses import asdict, replace
from core.config import get_config
from core.config.models.verificators import VProviderField, VProviderType, VerificationProvider
from core.config.store import ConfigLoader
from core.utils.json import dataclass_to_dict


def get_verificators():
    config = get_config()

    verificators = [dataclass_to_dict(v) for v in config.verificators.items]
    order = [t.value for t in config.verificators.order]

    order_index = {value: index for index, value in enumerate(order)}
    sorted_verificators = sorted(verificators, key=lambda x: order_index[x['type']])

    return sorted_verificators


def update_verificator(
        vid: str, 
        enabled: bool, 
        fields: dict,
        order: list,
    ):
    if vid not in VProviderType:
        return {'status': 'UNKNOWN_PROVIDER', 'error_message': 'Unknown provider type'}
    
    with ConfigLoader().update() as config:
        cfg = config.verificators.items
        
        config.verificators.order = [VProviderType(t) for t in order]

        for i in range(len(cfg)):
            v = cfg[i]
            if v.type == vid:
                new_fields = []

                if v.type == VProviderType.SMSRU:
                    new_fields.append(
                        VProviderField(value=fields.get('api_key'))
                    )
                if v.type == VProviderType.ASTERISK:
                    new_fields.append(
                        VProviderField(
                            name="call_phone",
                            label="Call phone",
                            type="text",
                            value=fields.get('call_phone'),
                        )
                    )
                if v.type in [VProviderType.MIKROTIK, VProviderType.HUAWEI]:
                    new_fields.append(
                        VProviderField(
                            name="url",
                            label="URL",
                            type="text",
                            value=fields.get('url'),
                        )
                    )

                cfg[i] = replace(v, 
                    enabled=enabled,
                    fields=new_fields,
                )
                return {'status': 'OK'}
