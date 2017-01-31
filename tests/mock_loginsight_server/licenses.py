# -*- coding: utf-8 -*-

import requests_mock
from collections import Counter
import json
import logging

from .utils import RandomDict, requiresauthentication, trailing_guid_pattern, license_url_matcher


# VMware vRealize Log Insight Exporter
# Copyright © 2017 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an “AS IS” BASIS, without warranties or
# conditions of any kind, EITHER EXPRESS OR IMPLIED. See the License for the
# specific language governing permissions and limitations under the License.


mockserverlogger = logging.getLogger("LogInsightMockAdapter")


class MockedLicensesMixin(requests_mock.Adapter):

    def __init__(self, **kwargs):
        super(MockedLicensesMixin, self).__init__(**kwargs)

        self.licenses_known = RandomDict({'12345678-90ab-cdef-1234-567890abcdef': {'typeEnum': 'OSI', 'id': '12345678-90ab-cdef-1234-567890abcdef', 'error': '', 'status': 'Active', 'configuration': '1 Operating System Instance (OSI)', 'licenseKey': '4J2TK-XXXXX-XXXXX-XXXXX-XXXXX', 'infinite': True, 'count': 0, 'expiration': 0}})

        # License Keys
        self.register_uri('GET', '/api/v1/licenses', status_code=200, text=self.callback_list_license)
        self.register_uri('POST', '/api/v1/licenses', status_code=201, text=self.callback_add_license)
        self.register_uri('DELETE', license_url_matcher, status_code=200, text=self.callback_remove_license)

        self.register_uri('GET', '/api/v1/version', text='{"releaseName": "GA","version": "1.2.3-4567890"}', status_code=200)

    @requiresauthentication
    def callback_list_license(self, request, context, session_id, user_id):
        return json.dumps(self.get_license_summary_object())

    @requiresauthentication
    def callback_add_license(self, request, context, session_id, user_id):
        body = request.json()
        newitem = {'typeEnum': 'OSI', 'id': 'TBD', 'error': '', 'status': 'Active',
                   'configuration': '1 Operating System Instance (OSI)',
                   'licenseKey': body['key'], 'infinite': True, 'count': 0, 'expiration': 0}
        newitem['id'] = self.licenses_known.append(newitem)
        return json.dumps(newitem)

    @requiresauthentication
    def callback_remove_license(self, request, context, session_id, user_id):
        delete_guid = trailing_guid_pattern.match(request._url_parts.path).group(1)
        try:
            del self.licenses_known[delete_guid]
            mockserverlogger.info("Deleted license {0}".format(delete_guid))
        except KeyError:
            mockserverlogger.info("Attempted to delete nonexistant license {0}".format(delete_guid))
            context.status_code = 404
        return

    def get_license_summary_object(self):
        counts = Counter(OSI=0, CPU=0)
        for key, license in self.licenses_known.items():
            if not license['error']:
                counts[license['typeEnum']] += license["count"]

        return {"hasOsi": counts['OSI'] > 0,
                "hasCpu": counts['CPU'] > 0,
                "maxOsis": counts['OSI'],
                "maxCpus": counts['CPU'],
                "limitedLicenseCapabilities": ["QUERY", "RBAC", "UPGRADE", "ACTIVE_DIRECTORY", "CONTENT_PACK"],
                "standardLicenseCapabilities": ["FORWARDING", "RBAC", "UPGRADE", "CUSTOM_SSL", "ACTIVE_DIRECTORY", "CONTENT_PACK", "VSPHERE_FULL_SUPPORT", "CLUSTER", "IMPORT_CONTENT_PACKS", "QUERY", "ARCHIVE", "THIRD_PARTY_CONTENT_PACKS"],
                "uninitializedLicenseCapabilities": ["RBAC", "ACTIVE_DIRECTORY", "CONTENT_PACK"],
                "licenseState": "ACTIVE" if (counts['OSI'] + counts['CPU'] > 0) else "INACTIVE",
                "licenses": self.licenses_known,
                "hasTap": False}

    def prep(self):
        pass