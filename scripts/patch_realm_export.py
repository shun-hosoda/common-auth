"""Add userProfileConfig to realm-export.json."""
import json

user_profile_config = {
    "attributes": [
        {
            "name": "username",
            "displayName": "${username}",
            "validations": {
                "length": {"min": 3, "max": 255},
                "username-prohibited-characters": {},
                "up-username-not-idn-homograph": {},
            },
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "email",
            "displayName": "${email}",
            "validations": {"email": {}, "length": {"max": 255}},
            "required": {"roles": ["user"]},
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "firstName",
            "displayName": "${firstName}",
            "validations": {
                "length": {"max": 255},
                "person-name-prohibited-characters": {},
            },
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "lastName",
            "displayName": "${lastName}",
            "validations": {
                "length": {"max": 255},
                "person-name-prohibited-characters": {},
            },
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "tenant_id",
            "permissions": {"view": ["admin"], "edit": ["admin"]},
            "multivalued": False,
        },
        {
            "name": "mfa_enabled",
            "permissions": {"view": ["admin"], "edit": ["admin"]},
            "multivalued": False,
        },
        {
            "name": "mfa_method",
            "permissions": {"view": ["admin"], "edit": ["admin"]},
            "multivalued": False,
        },
    ],
    "groups": [
        {
            "name": "user-metadata",
            "displayHeader": "User metadata",
            "displayDescription": "Attributes, which refer to user metadata",
        }
    ],
}

with open("auth-stack/keycloak/realm-export.json") as f:
    realm = json.load(f)

# userProfileConfig is stored as a JSON string inside the realm JSON
realm["userProfileConfig"] = json.dumps(user_profile_config)

with open("auth-stack/keycloak/realm-export.json", "w") as f:
    json.dump(realm, f, indent=2, ensure_ascii=False)

print("✅ realm-export.json updated with userProfileConfig")
