"""Key derivation, encryption and the in-memory unlocked-key vault.

Deliberate exception to the Dto/BO/Entity triptyque used elsewhere: this is
a technical service (KDF, Fernet encryption, holding the unlocked key in
process memory), not a business concept exposed as CRUD. It persists via a
dedicated ``VaultEntity`` for consistency with the rest of storage, but has
no BO and no generic Dto — only narrow action Dtos in
``controllers/auth.py`` (``SetupPasswordDtoIn``, ``UnlockDtoIn``,
``AuthStatusDtoOut``). The rest of the app (including ``agent/client.py``)
reads the decrypted token through ``security/vault.py``, never the raw
entity.
"""
