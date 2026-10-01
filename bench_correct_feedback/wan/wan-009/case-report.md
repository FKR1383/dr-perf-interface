# wan-009 full-feedback result

Status: `success`; iterations: 2; fixed workload: `00e880d4388f88685d791b292ee8af2972bd74e76763acdabe15410a0c7c3290`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `cache_slots = self._cached_conv_counts['decoder'] + self._cached_conv_counts['encoder']`; `existing_cache_slots = len(self.__dict__.get('_feat_map', ())) + len(self.__dict__.get('_enc_feat_map', ()))` | - | invalid |
| 2 | `entry_cache_index = self._conv_idx[0]`; `existing_cache_slots = len(self.__dict__.get('_feat_map', ())) + len(self.__dict__.get('_enc_feat_map', ()))` | 0.130099% | success |
