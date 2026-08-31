from typing import Any, Dict
class CompatibilityEngine:
    def check(self,product_a:Dict[str,Any],product_b:Dict[str,Any])->Dict[str,Any]:
        a_attrs=product_a.get('attributes',{}) or {}
        b_attrs=product_b.get('attributes',{}) or {}
        a_id,b_id=str(product_a.get('id')),str(product_b.get('id'))
        RULES = (
            ("incompatible_with", "incompatible", "An explicit incompatibility relationship exists."),
            ("compatible_with", "compatible", "An explicit compatibility relationship exists."),
        )
        for attr_key,status,evidence_text in RULES:
           if self._has_bidirectional_link(a_attrs,b_attrs,a_id,b_id,attr_key):
               return {
                   'status':status,
                   'confidence':0.98,
                   'evidence':[evidence_text]
               }
        return {
            'status':'unknown',
            'confidence':0.25,
            'evidence':[],
            'reason':"The catalog does not contain enough compatibility evidence"
        }
    def _has_bidirectional_link(self, attrs_a: dict, attrs_b: dict, id_a: str, id_b: str, attr_key: str)->bool:
        return self._contains(attrs_a.get(attr_key),id_b) or self._contains(attrs_b.get(attr_key),id_a)
    @staticmethod
    def _contains(value:Any,target:str)->bool:
        if isinstance(value,list):
            return target in {str(item)for item in value}
        if isinstance(value,dict):
            return target in {str(key) for key in value.keys()}
        return str(value)==target if value is not None else None